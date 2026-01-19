
import asyncio
import logging
import sys
import os
from sqlalchemy.future import select

# Add parent directory to path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import get_db, AsyncSessionLocal
from app.models import BrokerAccount, MarketSymbol, DataSource
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from ctrader_open_api.messages.OpenApiMessages_pb2 import *
from ctrader_open_api.messages.OpenApiModelMessages_pb2 import *

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SymbolSync")

async def sync_symbols():
    async with AsyncSessionLocal() as db:
        # 1. Find a valid cTrader account to use for fetching symbols
        logger.info("Locating cTrader account...")
        result = await db.execute(select(BrokerAccount).where(BrokerAccount.broker_name == "CTRADER", BrokerAccount.is_active == True))
        account = result.scalars().first()
        
        if not account:
            logger.error("No active cTrader account found. Cannot fetch symbols.")
            return

        logger.info(f"Using cTrader account: {account.account_name} ({account.account_number})")

        # 2. Initialize Adapter
        try:
            credentials = decrypt_data(account.credentials_encrypted)
            credentials["environment"] = account.environment
            adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        except Exception as e:
            logger.error(f"Failed to initialize adapter: {e}")
            return

        client = adapter.client
        
        try:
            # 3. Connect and Auth
            await client.connect()
            await client.authorize_app(adapter.client_id, adapter.client_secret)
            await client.authorize_account(adapter.account_id, adapter.token)
            
            # 4. Fetch Symbols
            logger.info("Fetching symbols from cTrader...")
            symbols_list = await client.get_symbols_list(adapter.account_id)
            logger.info(f"Received {len(symbols_list)} symbols from cTrader.")
            
            # 5. Fetch Local Market Symbols
            # Find Active cTrader Data Source
            ds_result = await db.execute(select(DataSource).where(DataSource.provider == 'CTRADER', DataSource.is_active == True))
            descriptions = ds_result.scalars().all()
            
            if not descriptions:
                logger.error("No ACTIVE Data Source found for provider 'CTRADER'.")
                return

            # Create map once
            ctrader_map = {s.symbolName: s for s in symbols_list}
            updates_count = 0

            for ds in descriptions:
                logger.info(f"Processing Data Source: {ds.name} ({ds.id})")
                
                ms_result = await db.execute(select(MarketSymbol).where(MarketSymbol.data_source_id == ds.id))
                local_symbols = ms_result.scalars().all()
            
                logger.info(f"Found {len(local_symbols)} local symbols for {ds.name}")
                
                # Collect matched IDs to fetch FULL details
                to_enrich = []
                local_sym_map = {} # id -> local_sym obj

                for local_sym in local_symbols:
                    target_name = local_sym.symbol
                    match = ctrader_map.get(target_name)
                    if not match:
                        alt_name = target_name.replace("_", "").replace("/", "")
                        match = ctrader_map.get(alt_name)
                    
                    if match:
                        # Append to list for batch fetching
                        to_enrich.append(match.symbolId)
                        local_sym_map[match.symbolId] = local_sym
                    else:
                        logger.warning(f"Could not find match for local symbol: {local_sym.symbol} in {ds.name}")
                
                # Batch fetch full details
                if to_enrich:
                    logger.info(f"Fetching full details for {len(to_enrich)} symbols...")
                    full_symbols = await client.get_symbols_full(adapter.account_id, to_enrich)
                    
                    for full_sym in full_symbols:
                         ls = local_sym_map.get(full_sym.symbolId)
                         if ls:
                             # Convert full proto object to dict
                             # Manual pick is safer/cleaner than trying to dump proto.
                             
                             new_details = dict(ls.details) if ls.details else {}
                             new_details.update({
                                 "symbolId": full_sym.symbolId,
                                 "digits": full_sym.digits,
                                 "pipPosition": full_sym.pipPosition,
                                 # "scheduleId": full_sym.scheduleId, # Attribute Error
                                 "commission": full_sym.commission,
                                 "minVolume": full_sym.minVolume,
                                 "maxVolume": full_sym.maxVolume,
                                 "stepVolume": full_sym.stepVolume,
                                 "lotSize": full_sym.lotSize,
                                 # "baseAssetId": full_sym.baseAssetId, # Available in LightSymbol
                                 # "quoteAssetId": full_sym.quoteAssetId, 
                             })
                             ls.details = new_details
                             updates_count += 1
                             logger.info(f"Updated {ls.symbol} -> ID {full_sym.symbolId} (Full Details)")

            await db.commit()
            logger.info(f"Sync Complete. Updated {updates_count} symbols.")

        except Exception as e:
            logger.error(f"Sync failed: {e}", exc_info=True)
        finally:
            await client.disconnect()

if __name__ == "__main__":
    asyncio.run(sync_symbols())
