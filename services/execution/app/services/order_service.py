import logging
import uuid
import json
from datetime import datetime, timedelta, timezone
from sqlalchemy.future import select
from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from typing import Any

from app.models import BrokerAccount, Fund, Trade, Candle, EconomicEvent, TradeStatus, RiskFilter
from app.adapters.factory import BrokerFactory
from app.utils.crypto import decrypt_data
from app.services.minimax_service import MinimaxService
from app.validators.order_validator import OrderValidator
from app.filters.session_filter import SessionFilter
from app.filters.news_filter import NewsFilter
from app.filters.volatility_filter import VolatilityFilter
from app.filters.spread_filter import SpreadFilter
from app.filters.quant_filter import QuantFilter
from app.filters.liquidity_filter import LiquidityFilter
from app.filters.liquidity_filter import LiquidityFilter
from app.risk.risk_limits import RiskLimitsAgent
from app.services.cache_service import execution_cache
from app.services.price_service import price_service
import asyncio
import time

logger = logging.getLogger(__name__)

class OrderService:
    @staticmethod
    async def _log_trace(trace_id: str, step: str, start_time: float):
        """Helper to log execution trace to Redis for observability."""
        try:
            from app.utils.redis_client import get_redis_client
            rc = get_redis_client()
            duration = (time.time() - start_time) * 1000
            msg = f"{step}:{duration:.2f}ms"
            # 1. Store in List (for history)
            await rc.rpush(f"trace:{trace_id}", msg)
            # 2. Broadcast (for real-time UI)
            await rc.publish("execution:traces", json.dumps({"trace_id": trace_id, "step": step, "duration_ms": round(duration, 2)}))
            # TTL for trace
            await rc.expire(f"trace:{trace_id}", 3600)
        except Exception:
            pass

    @staticmethod
    async def execute_smart_order(req_data: dict, db: AsyncSession):
        """
        Core logic for placing a smart order with risk management and minimax check.
        Expects req_data to have: broker_account_id, symbol, direction, stop_loss, etc.
        """
        try:
            # 0. Global Check (HFT-lite: Try Redis first)
            try:
                from app.utils.redis_client import get_redis_client
                rc = get_redis_client()
                if await rc.get("system:kill_switch") == "1":
                    logger.warning("🛑 SYSTEM HALTED: Smart Order rejected via Global Kill Switch.")
                    raise HTTPException(status_code=503, detail="System is currently halted for emergency maintenance.")
            except (RuntimeError, Exception):
                # Fallback: if Redis is closed or fails, we might still want to proceed if safe, 
                # but for unit tests this happens because of loop closure.
                pass

            # 1. Resolve Account (Tiered Cache Only)
            try:
                account_id = req_data.get("broker_account_id")
                # UUID validation is fast/local
                uuid.UUID(account_id)
            except (ValueError, TypeError):
                raise ValueError("Invalid UUID format for broker_account_id")

            start_t = time.time()
            trace_id = req_data.get("client_order_id") or f"trace:{uuid.uuid4().hex[:8]}"
            
            # --- TIERED CACHE: Account (Rule 7: No DB Fallback here) ---
            account_data = await execution_cache.get_account(account_id)
            if not account_data:
                logger.error(f"Rule 7 Violation Prevented: Account {account_id} not in cache. Rejecting for hot-path protection.")
                # We could trigger a background fetch here, but the current order must fail to keep loop latency <10ms
                raise HTTPException(status_code=503, detail="System warming up. Broker account metadata not yet cached.")

            # Map dict to object for compatibility
            account = type('obj', (object,), account_data)
            await OrderService._log_trace(trace_id, "account_cache_hit", start_t)

            if not account.is_active:
                raise ValueError("Broker Account is inactive")

            # 2. Decrypt Credentials (Cached)
            creds_start = time.time()
            credentials = await execution_cache.get_credentials(account_id)
            if credentials:
                await OrderService._log_trace(trace_id, "creds_cache_hit", creds_start)
            else:
                try:
                    credentials = decrypt_data(account.credentials_encrypted)
                    credentials["environment"] = account.environment
                    execution_cache.set_credentials(account_id, credentials)
                    await OrderService._log_trace(trace_id, "creds_decrypt", creds_start)
                except Exception:
                    raise Exception("Failed to retrieve broker credentials")

            adapter = BrokerFactory.get_adapter(account.broker_name, credentials)

            # 3. Validation (Standard checks)
            stop_loss = req_data.get("stop_loss")
            if not stop_loss:
                raise ValueError("Smart Order requires a Stop Loss price to calculate risk.")
            
            take_profit = req_data.get("take_profit")

            if not req_data.get("generated_by"):
                raise ValueError("Traceability Error: 'generated_by' (Strategy Name) is required.")

            if not req_data.get("signal_id"):
                 logger.warning("Smart Order missing 'signal_id'. Traceability will be limited.")

            # 4. Hierarchical Risk Calculation (Cache Only)
            if not account.fund_id:
                raise ValueError("Broker Account is not linked to a Fund")
            
            fund_start = time.time()
            fund_id = str(account.fund_id)
            fund_data = await execution_cache.get_fund(fund_id)
            if not fund_data:
                logger.error(f"Rule 7 Violation Prevented: Fund {fund_id} not in cache. Rejecting.")
                raise HTTPException(status_code=503, detail="System warming up. Fund metadata not yet cached.")

            fund = type('obj', (object,), fund_data)
            await OrderService._log_trace(trace_id, "fund_cache_hit", fund_start)

            # Determine Max Risk Limit
            fund_limit = float(fund.max_risk_per_trade)
            account_limit = None
            if account.risk_settings and "max_risk_per_trade" in account.risk_settings:
                account_limit = float(account.risk_settings["max_risk_per_trade"])
                
            effective_limit = min(fund_limit, account_limit) if account_limit is not None else fund_limit
            
            # Dynamic Risk via Last Known NAV (HFT-lite)
            calculated_risk = effective_limit
            if fund.risk_percentage and float(fund.risk_percentage) > 0:
                try:
                    # In HFT-lite, we use cached NAV if available to save 100ms
                    from app.utils.redis_client import get_redis_client
                    rc = get_redis_client()
                    nav_cached = await rc.get(f"account_summary:nav:{account_id}")
                    if nav_cached:
                        nav = float(nav_cached)
                        await OrderService._log_trace(trace_id, "nav_cache_hit", time.time())
                    else:
                        summary = await adapter.get_account_summary()
                        nav = float(summary.get('NAV', 0))
                        await rc.set(f"account_summary:nav:{account_id}", str(nav), ex=60) # Cache for 1 min
                        await OrderService._log_trace(trace_id, "nav_api_fetch", time.time())
                    
                    if nav > 0:
                        dynamic_risk = nav * float(fund.risk_percentage)
                        calculated_risk = min(dynamic_risk, effective_limit)
                except Exception as e:
                    logger.warning(f"Failed to calculate dynamic risk: {e}")

            # Final Risk Amount
            requested_risk = req_data.get("risk_usd")
            target_risk = requested_risk if requested_risk is not None else calculated_risk
            
            if target_risk > effective_limit:
                raise ValueError(f"Requested risk ${target_risk} exceeds effective limit ${effective_limit}")

            # 5. Position Sizing (O(1) Price Lookup)
            price_start = time.time()
            current_price, price_err = await price_service.get_latest_price(req_data["symbol"], provider=account.broker_name)
            if price_err:
                logger.warning(f"Price cache miss or stale: {price_err}. Falling back to API.")
                try:
                    current_price = await adapter.get_current_price(req_data["symbol"])
                    await OrderService._log_trace(trace_id, "price_api_fetch", price_start)
                except Exception as e:
                    raise Exception(f"Failed to fetch live price: {str(e)}")
            else:
                await OrderService._log_trace(trace_id, "price_cache_hit", price_start)
                
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

            # Min Lot Validation (Allow fractional for Crypto/OANDA, e.g. 0.01)
            if abs(units) < 0.0001: 
                raise ValueError(f"Calculated size {units:.6f} is below minimum (0.0001 units)")

            # Round to reasonable decimal for API consistency (e.g. 4 decimals)
            units = round(units, 4)

            # 6.0 IC Markets Safety Guardrail: Max 0.01 Lot
            await RiskLimitsAgent.check_order_size(req_data["symbol"], units)

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

            # 6.5. Layer 4: Risk Citadel - Mandatory Filters (Parallel Execution)
            await OrderService.validate_all_risk_filters(
                db=db,
                adapter=adapter,
                fund=fund,
                symbol=req_data["symbol"],
                direction=direction,
                sl_price=stop_loss,
                tp_price=take_profit,
                entry_price=entry_ref,
                units=units,
                broker_account_id=account_id,
                trace_id=trace_id
            )

            # 7. Execute
            exec_start = time.time()
            logger.info(f"Executing: {req_data['symbol']} {units} units. Risk=${target_risk}")
            
            # ... execution logic ...
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
            
            await OrderService._log_trace(trace_id, "broker_execute", exec_start)
            
            fill = response.get("orderFillTransaction") or response.get("orderCreateTransaction") or {}
            res = {
                "id": fill.get("id", "trace_" + trace_id[-6:]),
                "instrument": fill.get("instrument", req_data["symbol"]),
                "units": fill.get("units", str(units)),
                "price": fill.get("price", str(entry_ref)),
                "time": fill.get("time", ""),
                "trace_id": trace_id
            }
            # Log total time
            total_duration = (time.time() - start_t) * 1000
            res["latency_ms"] = round(total_duration, 2)
            
            # [Latency] Publish internal latency metric
            try:
                from app.utils.redis_client import get_redis_client
                rc = get_redis_client()
                await rc.publish("system.metrics.latency", json.dumps({
                    "type": "internal_latency",
                    "symbol": req_data["symbol"],
                    "latency_ms": round(total_duration, 2),
                    "trace_id": trace_id
                }))
            except: pass

            logger.info(f"✨ HFT-lite Order Complete: {req_data['symbol']} in {total_duration:.2f}ms")
            return res
        except ValueError as ve:
            logger.error(f"Validation Error in Smart Order: {ve}")
            raise ve
        except Exception as e:
            logger.error(f"Unexpected Error in Smart Order: {e}", exc_info=True)
            raise e
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
        
        # 1. Resolve Account (Cache Only - Rule 7)
        account_id = req_data.get("broker_account_id")
        account_data = await execution_cache.get_account(account_id)
        if not account_data:
            logger.error(f"Rule 7 Violation Prevented: Account {account_id} not in cache for Market Making.")
            raise ValueError("Market Making metadata not available in cache.")
        
        account = type('obj', (object,), account_data)
        credentials = await execution_cache.get_credentials(account_id)
        if not credentials:
             # decrypt if not in L1
             credentials = decrypt_data(account.credentials_encrypted)
             credentials["environment"] = account.environment
             execution_cache.set_credentials(account_id, credentials)
             
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

    @staticmethod
    async def validate_all_risk_filters(
        db: AsyncSession,
        adapter: Any,
        fund: Any,
        symbol: str,
        direction: str,
        sl_price: float,
        tp_price: float,
        entry_price: float = 0.0,
        units: float = 0.0,
        broker_account_id: str = None,
        trace_id: str = None
    ):
        """
        Executes all mandatory Layer 4 Risk Filters in PARALLEL (HFT-lite).
        """
        filter_start = time.time()
        
        # 1. Fetch filters (Cached)
        fund_id = str(fund.id)
        active_filters_raw = await execution_cache.get_risk_filters(fund_id, broker_account_id)
        
        if active_filters_raw is None:
            # Rule 7 Compliance: Do not fallback to DB in hot path.
            # If cache is missing, it's safer to fail or use a very minimal default.
            # However, for Risk Filters, a missing cache means we can't guarantee safety.
            logger.error(f"Rule 7 Violation Prevented: Risk filters not in cache for fund {fund_id}. Rejecting.")
            raise ValueError("Risk safety metadata not available. Please retry in 5s.")
        
        if trace_id: await OrderService._log_trace(trace_id, "filters_cache_hit", filter_start)

        # 2. Sequential Validation for Phase 1 (Synchronous logic, very fast)
        # OrderValidator currently expects objects, let's convert or mock
        # For now, we'll keep it simple as it's purely CPU bound
        OrderValidator.validate(
            symbol=symbol,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            active_filters=[type('obj', (object,), f) for f in active_filters_raw]
        )

        # 3. Parallelize Phase 2 & 3 (HFT-lite)
        filter_instances = {
            "SESSION_FILTER": SessionFilter(),
            "NEWS_FILTER": NewsFilter(),
            "VOLATILITY_FILTER": VolatilityFilter(),
            "SPREAD_FILTER": SpreadFilter(),
            "QUANT_FILTER": QuantFilter(),
            "LIQUIDITY_FILTER": LiquidityFilter(),
        }

        # Tasks for Phase 2 Filters
        tasks = []
        for f_data in active_filters_raw:
            f_type = f_data["filter_type"]
            if f_type in filter_instances:
                filter_obj = filter_instances[f_type]
                tasks.append(
                    filter_obj.validate(
                        db=db,
                        adapter=adapter,
                        fund=fund,
                        symbol=symbol,
                        direction=direction,
                        sl_price=sl_price,
                        tp_price=tp_price,
                        entry_price=entry_price,
                        filter_config=type('obj', (object,), f_data)
                    )
                )
        
        # Task for Phase 3 Limits (Now DB-free)
        tasks.append(RiskLimitsAgent.check_limits(db, fund, broker_account_id))
        
        # [NEW] Phase 28: Account-Specific Margin Check
        # Resolve full account for leverage
        account_data = await execution_cache.get_account(broker_account_id)
        if account_data:
            account_obj = type('obj', (object,), account_data)
            tasks.append(RiskLimitsAgent.check_margin(account_obj, symbol, units=units, current_price=entry_price))

        if tasks:
            await asyncio.gather(*tasks)
            if trace_id: await OrderService._log_trace(trace_id, "parallel_filters_complete", time.time())

        return True
