from app.services.minimax_service import MinimaxService

def test_minimax_safe_trade():
    """Test a safe trade that fits within pain threshold."""
    is_safe, regret, reason = MinimaxService.calculate_regret(
        risk_usd=20.0,
        reward_usd=40.0,
        confidence=0.8,
        pain_threshold=50.0
    )
    # Regret(Trade) = 20
    # Regret(NoTrade) = 40 * 0.8 = 32
    # Max Regret = 32
    # 32 <= 50 -> OK
    assert is_safe is True
    assert regret == 32.0
    assert reason == "OK"

def test_minimax_risk_rejection():
    """Test rejection due to high risk."""
    is_safe, regret, reason = MinimaxService.calculate_regret(
        risk_usd=60.0,
        reward_usd=100.0,
        confidence=0.5,
        pain_threshold=50.0
    )
    # Regret(Trade) = 60
    # Regret(NoTrade) = 100 * 0.5 = 50
    # Max Regret = 60
    # 60 > 50 -> Reject
    assert is_safe is False
    assert regret == 60.0
    assert "Regret 60.00" in reason

def test_minimax_opportunity_rejection():
    """Test rejection due to high missed opportunity (high confidence reward)."""
    # Wait, spec says: if Worst Case > Regret ... 
    # If I have a sure thing (Conf=1.0, Reward=1000) and Risk=10.
    # Regret(NoTrade) = 1000.
    # Worst Case = 1000.
    # If Pain Threshold = 50.
    # 1000 > 50 -> Reject.
    # This implies we shouldn't pass up opportunities that would cause massive regret if missed.
    # BUT, if the REASON is "User cannot handle regret > $50", then failing to take a sure thing IS causing potential regret.
    # So technically, we should ACCEPT the trade to AVOID the regret of missing it?
    # NO, the logic is: "Minimax strategy chooses the action that minimizes maximum regret."
    # Action A (Trade): Max Regret = Loss (if it fails).
    # Action B (No Trade): Max Regret = Missed Profit (if it wins).
    # We choose Action with Min(Max Regret).
    # Here, we are just VALIDATING the "Trade" action.
    # The spec is slightly ambiguous or I am interpreting "Pain Threshold" as "Max Allowed Loss".
    # But strictly following "Worst Case > Pain Threshold REJECT":
    
    is_safe, regret, reason = MinimaxService.calculate_regret(
        risk_usd=10.0,
        reward_usd=100.0,
        confidence=0.9,
        pain_threshold=50.0
    )
    # Regret(Trade) = 10
    # Regret(NoTrade) = 90
    # Max Regret = 90
    # 90 > 50 -> Reject?
    # If I reject, I am saying "I cannot emotionally handle missing this trade". 
    # WAIT. If I reject it, I AM missing it. So I am CAUSING the regret I can't handle.
    # This logic seems to be a "Pre-Trade Check" to see if the User is capable of handling the outcome deviations.
    # Let's assume the spec meant "Regret(Trade) > Pain Threshold".
    # But I implemented Max(Regret(Trade), Regret(NoTrade)).
    # If I return False (Reject), it actually forces "No Trade", which force-realizes the Regret(NoTrade).
    # So if Regret(NoTrade) is high, we should probably ACCEPT (or Require) the trade?
    # Spec: "If Worst Case > User_Pain_Threshold, REJECT trade."
    # This implies we should simply NOT PLAY if the stakes (either loss OR FOMO) are too high for our mental state.
    # i.e. "This opportunity is too volatile/stressful for you."
    
    assert is_safe is False
    assert regret == 90.0

def test_minimax_volatility_multiplier():
    """Test volatility multiplier effects."""
    is_safe, regret, reason = MinimaxService.calculate_regret(
        risk_usd=30.0,
        reward_usd=40.0,
        confidence=0.5,
        pain_threshold=50.0,
        volatility_multiplier=2.0
    )
    # Regret(Trade) = 30 * 2.0 = 60
    # Regret(NoTrade) = 20
    # Max = 60
    # 60 > 50 -> Reject
    assert is_safe is False
    assert regret == 60.0
