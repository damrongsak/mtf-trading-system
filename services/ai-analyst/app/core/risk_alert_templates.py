"""
Phase 60: Telegram Alert Templates for Risk Events.
All templates use HTML formatting compatible with ai-analyst's send_telegram_message.
"""


def moderate_drift_alert(
    fund_id: str,
    current_score: float,
    prev_score: float,
    drift: float,
    recommendation: dict,
    reason: str
) -> str:
    """Template for MODERATE sentiment drift (0.4–0.6)."""
    risk_pct = recommendation.get("risk_percentage", 0)
    max_dd = recommendation.get("max_drawdown_threshold", 0)
    
    return (
        "⚠️ **Sentiment Drift Detected**\n\n"
        f"**Fund:** `{fund_id[:8]}...`\n"
        f"**Drift:** {drift:.2f} (Prev: {prev_score:.2f} → Now: {current_score:.2f})\n"
        f"**Trigger:** {reason[:120]}\n\n"
        "📋 **AI Recommendation:**\n"
        f"• Risk %: {risk_pct * 100:.2f}%\n"
        f"• Max DD: {max_dd:.1f}%\n\n"
        "👉 Review and apply via Dashboard → Risk Controls"
    )


def crisis_auto_applied_alert(
    fund_id: str,
    drift: float,
    previous_config: dict,
    applied_config: dict,
    reason: str
) -> str:
    """Template for CRISIS auto-apply (drift > 0.6)."""
    prev_risk = previous_config.get("risk_percentage", 0)
    new_risk = applied_config.get("risk_percentage", 0)
    prev_dd = previous_config.get("max_drawdown_threshold", 0)
    new_dd = applied_config.get("max_drawdown_threshold", 0)
    
    return (
        "🚨 **CRISIS: Risk Auto-Adjusted**\n\n"
        f"**Fund:** `{fund_id[:8]}...`\n"
        f"**Drift Magnitude:** {drift:.2f} (CRISIS threshold: 0.6)\n\n"
        "**Changes Applied:**\n"
        f"• Risk: {prev_risk * 100:.2f}% → **{new_risk * 100:.2f}%**\n"
        f"• Max DD: {prev_dd:.1f}% → **{new_dd:.1f}%**\n\n"
        f"**Reason:** {reason[:200]}\n\n"
        "⚡ Applied by: Autonomous AI System\n"
        "Review: Dashboard → Risk Controls → Rebalance History"
    )


def rebalance_suggestion_alert(
    fund_id: str,
    recommendation: dict,
    reasoning: str
) -> str:
    """Template for manual rebalance suggestion (from AI review)."""
    risk_pct = recommendation.get("risk_percentage", 0)
    max_dd = recommendation.get("max_drawdown_threshold", 0)
    
    return (
        "📋 **AI Risk Rebalance Suggestion**\n\n"
        f"**Fund:** `{fund_id[:8]}...`\n\n"
        "**Recommended Parameters:**\n"
        f"• Risk %: {risk_pct * 100:.2f}%\n"
        f"• Max DD: {max_dd:.1f}%\n\n"
        f"**Reasoning:** {reasoning[:250]}\n\n"
        "👉 Apply via Dashboard → Risk Controls → AI Risk Analysis"
    )
