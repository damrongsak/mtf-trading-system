import logging
from decimal import Decimal
import uuid
import json
from app.core.globals import services
from app.core.config import settings
from app.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from app.services.telegram import send_telegram_message
from app.core.risk_alert_templates import (
    moderate_drift_alert,
    crisis_auto_applied_alert
)

logger = logging.getLogger("ai-analyst.tasks")

async def update_gold_sentiment():
    """
    Scheduled task to refresh XAUUSD sentiment score.
    Uses smarter caching and robust fallbacks.
    """
    logger.info("🔄 Running Scheduled Sentiment Update for XAUUSD...")
    
    sentiment_service = services.get("sentiment")
    if not sentiment_service:
        logger.error("❌ Sentiment Service not available in globals. Check lifespan startup.")
        return

    try:
        # Defaults to XAUUSD
        # The service now uses gemini-2.5-flash and headline hashing
        result = await sentiment_service.get_sentiment(symbol="XAUUSD")
        
        score = result.get('score', 0.0)
        reason = result.get('reason', 'No reason provided')
        
        if score == 0.0 and "Error" in reason:
            logger.warning(f"⚠️ Sentiment update returned fallback value: {reason}")
        else:
            logger.info(f"✅ Sentiment Update Success: {score} | {reason}")
            
    except Exception as e:
        logger.error(f"❌ Critical Failure in update_gold_sentiment task: {e}")

async def run_daily_post_mortem():
    """
    Scheduled task to analyze closed trades from the last 24 hours.
    Extracts lessons learned and stores them in Qdrant.
    """
    logger.info("🔄 Running Daily Post-Mortem Analysis...")
    
    agent = services.get("post_mortem")
    if not agent:
        logger.error("❌ PostMortemAgent not available in globals.")
        return

    db = SessionLocal()
    try:
        # Fetch closed trades from last 24h
        # Since we don't have the full models here, we use raw SQL or a minimal Reflected model
        # Using raw SQL is safer to avoid importing models from other services
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        
        query = text("""
            SELECT trade_id as id, symbol, entry_price, exit_price, pnl_usd as result_pnl, 
                   status, direction, strategy_name, exit_timestamp
            FROM trades
            WHERE status = 'CLOSED' AND exit_timestamp >= :yesterday
        """)
        
        result = db.execute(query, {"yesterday": yesterday}).mappings().all()
        # Convert SQLAlchemy RowMappings to standard dicts
        # The PostMortemAgent.safe_json_dumps handles UUID, Decimal, and datetime
        trades = [dict(r) for r in result]
        
        if not trades:
            logger.info("ℹ️ No closed trades found in the last 24 hours. Skipping analysis.")
            return

        logger.info(f"📊 Analyzing {len(trades)} trades for post-mortem...")
        
        # We assume a default user for daily cron or iterate over users
        # For now, using 'trader1' as default if not specified
        user_id = "trader1" 
        
        results = await agent.run_batch_analysis(trades, user_id)
        logger.info(f"✅ Daily Post-Mortem complete. {len(results)} lessons processed.")
            
    except Exception as e:
        logger.error(f"❌ Critical Failure in run_daily_post_mortem task: {e}")
    finally:
        db.close()

async def check_sentiment_risk_drift():
    """
    Autonomous Pipeline: Sentiment-to-Risk (Phase 58).
    Monitors sentiment drift for gold and triggers RiskRebalancerAgent with tiered responses:
    - Drift < 0.4: Log only (normal market conditions)
    - Drift 0.4-0.6: Notify + suggest (moderate shift)
    - Drift > 0.6: Auto-apply risk adjustment (CRISIS mode)
    """
    logger.info("🚨 Running Autonomous Sentiment-to-Risk Drift Check...")
    
    sentiment_service = services.get("sentiment")
    if not sentiment_service:
        return

    try:
        # 1. Get Current Sentiment
        current_data = await sentiment_service.get_sentiment(symbol="XAUUSD")
        current_score = current_data.get("score", 0.0)
        
        # 2. Get Previous Score from Redis (using SentimentService's redis client)
        prev_key = "sentiment:previous_score:XAUUSD"
        prev_score_raw = await sentiment_service.redis.get(prev_key)
        prev_score = float(prev_score_raw) if prev_score_raw else 0.0
        
        # 3. Calculate Drift
        drift = abs(current_score - prev_score)
        THRESHOLD_NOTIFY = 0.4   # Moderate shift — notify + suggest
        THRESHOLD_CRISIS = 0.6   # Crisis — auto-apply
        
        logger.info(f"📊 Sentiment Analysis: Current={current_score:.2f}, Prev={prev_score:.2f}, Drift={drift:.2f}")

        # Log to Orchestration Audit Stream
        redis = services.get("redis")
        if redis:
            audit_entry = {
                "type": "pipeline_execution",
                "pipeline": "Sentiment-to-Risk",
                "symbol": "XAUUSD",
                "current_score": str(current_score),
                "prev_score": str(prev_score),
                "drift": str(drift),
                "triggered": "TRUE" if drift >= THRESHOLD_NOTIFY else "FALSE",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            await redis.xadd("orchestration.audit.stream", audit_entry, maxlen=1000, approximate=True)

        if drift >= THRESHOLD_NOTIFY:
            logger.warning(f"💥 SENTIMENT DRIFT DETECTED ({drift:.2f} >= {THRESHOLD_NOTIFY}). Invoking RiskRebalancerAgent...")
            
            # 4. Directly invoke RiskRebalancerAgent instead of consult_specialist
            risk_rebalancer = services.get("risk_rebalancer")
            if not risk_rebalancer:
                logger.error("❌ RiskRebalancerAgent not available in globals.")
                # Update previous score anyway
                await sentiment_service.redis.set(prev_key, str(current_score))
                return
            
            # 5. Get all active funds to analyze
            db = SessionLocal()
            try:
                funds_result = db.execute(text("SELECT id FROM funds WHERE is_active = true")).mappings().all()
                fund_ids = [str(r["id"]) for r in funds_result]
            finally:
                db.close()
            
            if not fund_ids:
                logger.warning("⚠️ No active funds found for risk rebalancing.")
                await sentiment_service.redis.set(prev_key, str(current_score))
                return
            
            for fund_id in fund_ids:
                try:
                    # 5b. Throttle Check: Avoid spamming if alert was sent 15m ago
                    throttle_key = f"alert_throttle:sentiment_drift:{fund_id}"
                    if await sentiment_service.redis.get(throttle_key):
                        logger.info(f"⏭️ Throttling sentiment alert for fund {fund_id} (Cooldown active).")
                        continue

                    # Build a minimal AgentState for the rebalancer
                    from langchain_core.messages import HumanMessage
                    state = {
                        "messages": [HumanMessage(content=(
                            f"AUTONOMOUS SENTIMENT DRIFT ALERT: Gold sentiment shifted from {prev_score:.2f} to {current_score:.2f} "
                            f"(drift={drift:.2f}). Reason: {current_data.get('reason', 'N/A')}. "
                            f"Evaluate risk parameters for fund {fund_id}."
                        ))],
                        "scratchpad": [],
                        "active_fund_id": fund_id
                    }
                    
                    result_state = await risk_rebalancer.analyze_risk(state)
                    
                    # 6. Parse recommendation from scratchpad
                    recommendation = None
                    for note in result_state.get("scratchpad", []):
                        if "suggests rebalance" in note:
                            # Extract JSON from scratchpad note
                            json_start = note.find("{")
                            if json_start >= 0:
                                recommendation = json.loads(note[json_start:])
                                break
                    
                    if recommendation:
                        logger.info(f"📋 Fund {fund_id}: RiskRebalancer recommends: {json.dumps(recommendation)}")
                        
                        if drift >= THRESHOLD_CRISIS:
                            # CRISIS MODE: Auto-apply
                            logger.warning(f"🚨 CRISIS MODE (drift={drift:.2f}): Auto-applying risk rebalance for fund {fund_id}")
                            await _auto_apply_rebalance(fund_id, recommendation, drift, current_data.get("reason", ""))
                        else:
                            # MODERATE: Notify only (log for dashboard pickup)
                            logger.info(f"📢 MODERATE DRIFT: Suggestion stored for fund {fund_id}. Manual apply recommended.")
                            await _store_suggestion(fund_id, recommendation, drift, current_data.get("reason", ""), current_score, prev_score)
                    else:
                        logger.info(f"✅ Fund {fund_id}: No rebalancing needed for current conditions.")
                        
                except Exception as fund_err:
                    logger.error(f"❌ Error analyzing fund {fund_id}: {fund_err}")

        # 7. Update Previous Score
        await sentiment_service.redis.set(prev_key, str(current_score))
        
    except Exception as e:
        logger.error(f"❌ Error in check_sentiment_risk_drift: {e}")


async def _auto_apply_rebalance(fund_id: str, recommendation: dict, drift: float, reason: str):
    """
    Auto-applies a risk rebalance recommendation by:
    1. Updating fund config in DB
    2. Publishing RISK_REBALANCE_APPLIED event to Redis
    3. Recording in rebalance_history
    """
    db = SessionLocal()
    try:
        # Get current config for audit snapshot
        fund_row = db.execute(
            text("SELECT risk_percentage, max_drawdown_threshold FROM funds WHERE id = :fid"),
            {"fid": fund_id}
        ).mappings().first()
        
        if not fund_row:
            logger.error(f"Fund {fund_id} not found for auto-apply.")
            return
        
        previous_config = {
            "risk_percentage": float(fund_row["risk_percentage"]) if fund_row["risk_percentage"] else 0,
            "max_drawdown_threshold": float(fund_row["max_drawdown_threshold"]) if fund_row["max_drawdown_threshold"] else 0
        }
        
        applied_config = {
            "risk_percentage": recommendation.get("risk_percentage", previous_config["risk_percentage"]),
            "max_drawdown_threshold": recommendation.get("max_drawdown_threshold", previous_config["max_drawdown_threshold"])
        }
        
        # Update fund config
        db.execute(
            text("""
                UPDATE funds 
                SET risk_percentage = :rp, max_drawdown_threshold = :mdt 
                WHERE id = :fid
            """),
            {
                "rp": applied_config["risk_percentage"],
                "mdt": applied_config["max_drawdown_threshold"],
                "fid": fund_id
            }
        )
        
        # Record in rebalance_history
        db.execute(
            text("""
                INSERT INTO rebalance_history (id, fund_id, trigger_type, drift_score, previous_config, applied_config, reasoning, applied_by)
                VALUES (:id, :fid, 'SENTIMENT_DRIFT', :drift, :prev, :applied, :reasoning, 'SYSTEM')
            """),
            {
                "id": str(uuid.uuid4()),
                "fid": fund_id,
                "drift": drift,
                "prev": json.dumps(previous_config),
                "applied": json.dumps(applied_config),
                "reasoning": f"Autonomous sentiment drift ({drift:.2f}): {reason}"
            }
        )
        
        db.commit()
        logger.info(f"✅ Auto-applied risk rebalance for fund {fund_id}: {json.dumps(applied_config)}")
        
        # Publish to Redis for Execution Service
        redis = services.get("redis")
        if redis:
            await redis.publish("system:events", json.dumps({
                "event": "RISK_REBALANCE_APPLIED",
                "fund_id": fund_id,
                "applied_by": "SYSTEM",
                "trigger": "SENTIMENT_DRIFT",
                "drift_score": drift
            }))
            logger.info(f"📡 Published RISK_REBALANCE_APPLIED for fund {fund_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Failed to auto-apply rebalance for fund {fund_id}: {e}")
    finally:
        db.close()
    
    # Send Telegram notification to fund owners (outside DB session)
    await _notify_fund_owners(
        fund_id,
        crisis_auto_applied_alert(
            fund_id=fund_id,
            drift=drift,
            previous_config=previous_config,
            applied_config=applied_config,
            reason=reason
        )
    )


async def _store_suggestion(fund_id: str, recommendation: dict, drift: float, reason: str, current_score: float = 0.0, prev_score: float = 0.0):
    """
    Stores a pending risk rebalance suggestion for dashboard pickup.
    Uses Redis with TTL so stale suggestions expire naturally.
    """
    redis = services.get("redis")
    if not redis:
        return
    
    suggestion = {
        "fund_id": fund_id,
        "recommendation": recommendation,
        "drift_score": drift,
        "reasoning": f"Sentiment drift ({drift:.2f}): {reason}",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    # Store in Redis with 4-hour TTL for dashboard pickup
    key = f"risk:pending_suggestion:{fund_id}"
    await redis.set(key, json.dumps(suggestion), ex=14400)
    logger.info(f"📦 Stored pending risk suggestion for fund {fund_id} (TTL: 4h)")
    
    # Send Telegram notification to fund owners
    await _notify_fund_owners(
        fund_id,
        moderate_drift_alert(
            fund_id=fund_id,
            current_score=current_score,
            prev_score=prev_score,
            drift=drift,
            recommendation=recommendation,
            reason=reason
        )
    )


async def _notify_fund_owners(fund_id: str, message: str):
    """
    Look up all owners/managers of a fund via user_funds → telegram_chat_mappings
    and send a Telegram notification to each linked user.
    Falls back to the system's default TELEGRAM_CHAT_ID from .env if no users found.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram notifications skipped: TELEGRAM_BOT_TOKEN not configured in .env")
        return
    
    db = SessionLocal()
    try:
        # Find all owner/manager chat_ids for this fund
        result = db.execute(
            text("""
                SELECT DISTINCT tcm.chat_id 
                FROM user_funds uf
                JOIN telegram_chat_mappings tcm ON tcm.user_id = uf.user_id AND tcm.is_active = true
                WHERE uf.fund_id = :fid AND uf.role IN ('OWNER', 'MANAGER')
            """),
            {"fid": fund_id}
        ).mappings().all()
        
        chat_ids = [int(r["chat_id"]) for r in result]
        
        if not chat_ids:
            # Fallback to system default chat_id from .env
            if settings.TELEGRAM_CHAT_ID:
                chat_ids = [settings.TELEGRAM_CHAT_ID]
                logger.info(f"Using default TELEGRAM_CHAT_ID from .env: {settings.TELEGRAM_CHAT_ID}")
            else:
                logger.warning(f"No Telegram recipients found for fund {fund_id} and no default TELEGRAM_CHAT_ID in .env")
                return
        
        for chat_id in chat_ids:
            try:
                await send_telegram_message(chat_id, message)
                logger.info(f"📱 Telegram alert sent to chat_id={chat_id} for fund {fund_id}")
                
                # Set Throttle Key (15 mins TTL)
                redis = services.get("redis")
                if redis:
                    throttle_key = f"alert_throttle:sentiment_drift:{fund_id}"
                    await redis.setex(throttle_key, 900, "1")
            except Exception as e:
                logger.error(f"Failed to send Telegram to {chat_id}: {e}")
    finally:
        db.close()
