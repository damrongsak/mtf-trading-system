import logging
import uuid
import json
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.models import BrokerAccount, Fund
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.services.minimax_service import MinimaxService

logger = logging.getLogger(__name__)

class OrderService:
    @staticmethod
    async def execute_smart_order(req_data: dict, db: AsyncSession):
        """
        Core logic for placing a smart order with risk management and minimax check.
        Expects req_data to have: broker_account_id, symbol, direction, stop_loss, etc.
        """
        # 1. Resolve Account
        try:
            account_id = req_data.get("broker_account_id")
            account_uuid = uuid.UUID(account_id)
        except (ValueError, TypeError):
            raise ValueError("Invalid UUID format for broker_account_id")

        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == account_uuid))
        account = result.scalars().first()
        if not account:
            raise ValueError("Broker Account not found")
        if not account.is_active:
            raise ValueError("Broker Account is inactive")

        # 2. Decrypt Credentials
        try:
            credentials = decrypt_data(account.credentials_encrypted)
            credentials["environment"] = account.environment
        except Exception:
            raise Exception("Failed to retrieve broker credentials")

        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)

        # 3. Validation
        stop_loss = req_data.get("stop_loss")
        if not stop_loss:
            raise ValueError("Smart Order requires a Stop Loss price to calculate risk.")

        if not req_data.get("generated_by"):
            raise ValueError("Traceability Error: 'generated_by' (Strategy Name) is required.")

        if not req_data.get("signal_id"):
             # We can warn or auto-generate, but strict mode prefers explicit ID
             logger.warning("Smart Order missing 'signal_id'. Traceability will be limited.")

        # 4. Hierarchical Risk Calculation
        if not account.fund_id:
            raise ValueError("Broker Account is not linked to a Fund")
            
        result_fund = await db.execute(select(Fund).where(Fund.id == account.fund_id))
        fund = result_fund.scalars().first()
        if not fund:
            raise ValueError("Fund not found")

        # Determine Max Risk Limit
        fund_limit = float(fund.max_risk_per_trade)
        account_limit = None
        if account.risk_settings and "max_risk_per_trade" in account.risk_settings:
            account_limit = float(account.risk_settings["max_risk_per_trade"])
            
        effective_limit = min(fund_limit, account_limit) if account_limit is not None else fund_limit
        
        # Dynamic Risk via NAV
        calculated_risk = effective_limit
        if fund.risk_percentage and float(fund.risk_percentage) > 0:
            try:
                summary = await adapter.get_account_summary()
                nav_str = summary.get('NAV')
                if nav_str:
                    nav = float(nav_str)
                    dynamic_risk = nav * float(fund.risk_percentage)
                    calculated_risk = min(dynamic_risk, effective_limit)
            except Exception as e:
                logger.warning(f"Failed to calculate dynamic risk: {e}")

        # Final Risk Amount
        requested_risk = req_data.get("risk_usd")
        target_risk = requested_risk if requested_risk is not None else calculated_risk
        
        if target_risk > effective_limit:
            raise ValueError(f"Requested risk ${target_risk} exceeds effective limit ${effective_limit}")

        # 5. Position Sizing
        try:
            current_price = await adapter.get_current_price(req_data["symbol"])
        except Exception as e:
            raise Exception(f"Failed to fetch live price: {str(e)}")
            
        entry_ref = req_data.get("entry_price") or current_price
        dist = abs(entry_ref - stop_loss)
        
        if dist <= 0:
            raise ValueError("Stop Loss cannot be equal to Entry/Current Price")
            
        raw_units = target_risk / dist
        direction = req_data.get("direction")
        
        if direction == "BULLISH":
            units = raw_units
            if stop_loss >= entry_ref:
                raise ValueError("Long SL must be below Entry Price")
        elif direction == "BEARISH":
            units = -raw_units
            if stop_loss <= entry_ref:
                raise ValueError("Short SL must be above Entry Price")
        else:
            raise ValueError("Invalid direction")

        # Min Lot Validation
        if abs(units) < 1.0: 
            raise ValueError(f"Calculated size {units:.4f} is below minimum (1 unit)")

        units = int(units)

        # 6. Minimax Check
        reward_usd = 0.0
        take_profit = req_data.get("take_profit")
        if take_profit:
            reward_dist = abs(take_profit - entry_ref)
            reward_usd = reward_dist * abs(units)
        else:
            reward_usd = target_risk * 2.0
        
        is_safe, regret, reason = MinimaxService.calculate_regret(
            risk_usd=target_risk,
            reward_usd=reward_usd,
            confidence=req_data.get("confidence", 0.8),
            pain_threshold=req_data.get("pain_threshold", 50.0),
            volatility_multiplier=req_data.get("atr_multiplier", 1.0)
        )
        
        if not is_safe:
            raise ValueError(f"Risk Citadel Validation Failed: {reason}")

        # 7. Execute
        logger.info(f"Executing: {req_data['symbol']} {units} units. Risk=${target_risk}")
        
        if req_data.get("entry_price"):
            response = await adapter.place_limit_order(
                symbol=req_data["symbol"],
                units=units,
                entry_price=req_data["entry_price"],
                sl_price=stop_loss,
                tp_price=take_profit,
                time_in_force=req_data.get("time_in_force", "GTC"),
                trade_id=None,
                comment=f"{req_data.get('generated_by', 'Manual')}-{req_data.get('signal_id', '0')}"
            )
        else:
            response = await adapter.place_market_order(
                symbol=req_data["symbol"],
                units=units,
                sl_price=stop_loss,
                tp_price=take_profit,
                trade_id=None,
                comment=f"{req_data.get('generated_by', 'Manual')}-{req_data.get('signal_id', '0')}"
            )
        
        fill = response.get("orderFillTransaction") or response.get("orderCreateTransaction") or {}
        return {
            "id": fill.get("id", "0"),
            "instrument": fill.get("instrument", req_data["symbol"]),
            "units": fill.get("units", str(units)),
            "price": fill.get("price", str(entry_ref)),
            "time": fill.get("time", "")
        }
    @staticmethod
    async def update_market_quotes(req_data: dict, db: AsyncSession):
        """
        Market Making: Update both Bid and Ask quotes for a symbol.
        Optimized to replace existing quotes.
        """
        symbol = req_data.get("symbol")
        bid = req_data.get("bid")
        ask = req_data.get("ask")
        bid_vol = req_data.get("bid_volume", 1000)
        ask_vol = req_data.get("ask_volume", 1000)
        
        # 1. Resolve Account (Same as execute_smart_order)
        account_id = req_data.get("broker_account_id")
        result = await db.execute(select(BrokerAccount).where(BrokerAccount.id == uuid.UUID(account_id)))
        account = result.scalars().first()
        
        credentials = decrypt_data(account.credentials_encrypted)
        credentials["environment"] = account.environment
        adapter = BrokerFactory.get_adapter(account.broker_name, credentials)
        
        # 2. Update Quotes (Broker Specific)
        # For cTrader, this usually means cancelling pending orders of same type/label and placing new ones.
        # Or using the specialized Mass Order API if implemented.
        
        # Simplified: Call adapter's update_quotes
        logger.info(f"Updating Quotes for {symbol}: Bid={bid}, Ask={ask}")
        return await adapter.update_quotes(
            symbol=symbol,
            bid_price=bid,
            ask_price=ask,
            bid_units=bid_vol,
            ask_units=ask_vol,
            comment=f"MM-{req_data.get('generated_by')}"
        )
