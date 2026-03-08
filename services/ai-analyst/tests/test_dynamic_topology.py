import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.strategy_advisor import StrategyAdvisorAgent
from app.agents.sentinel.economic_sanity_gate import EconomicSanityGate

@pytest.fixture
def mock_services():
    mock_rag = AsyncMock()
    mock_gemini = AsyncMock()
    # Note: StrategyAdvisorAgent uses self.gemini.generate_content (wrapper)
    # and self.gemini.client.aio (direct SDK)
    mock_gemini.generate_content = AsyncMock()
    mock_gemini.client = MagicMock()
    mock_gemini.client.aio = AsyncMock()
    
    # Mock search_lessons for retrieval test
    mock_rag.search_lessons = AsyncMock(return_value=["Lesson 1"])
    mock_rag.search_documentation = AsyncMock(return_value=[])
    mock_rag.search_similar_strategies = AsyncMock(return_value=[])
    mock_rag.search_library = AsyncMock(return_value=[])
    
    return mock_rag, mock_gemini

@pytest.mark.asyncio
async def test_node_severity_classifier(mock_services):
    mock_rag, mock_gemini = mock_services
    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    # Mock Gemini response for severity
    # The code uses SeverityClassification.model_validate_json(text)
    mock_gemini.generate_content.return_value = {
        "text": json.dumps({"severity": "CRISIS", "rationale": "Market crash detected"})
    }
    
    state = {"input_text": "Market is crashing!", "optimized_query": "market crash"}
    result = await advisor.node_severity_classifier(state)
    
    assert result["severity"] == "CRISIS"
    mock_gemini.generate_content.assert_called_once()

@pytest.mark.asyncio
async def test_economic_sanity_gate_logic():
    from app.agents.sentinel.economic_sanity_gate import AccountState, TradeProposal, EconomicSanityGate
    from decimal import Decimal
    
    account = AccountState(
        balance=Decimal("10000.0"),
        equity=Decimal("10000.0"),
        margin_used=Decimal("1000.0"),
        open_positions=0
    )
    gate = EconomicSanityGate(account=account)
    
    # 1. Valid Trade
    proposal = TradeProposal(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=Decimal("2000.0"),
        stop_loss=Decimal("1990.0"),
        take_profit=Decimal("2020.0"),
        lot_size=Decimal("0.1")
    )
    
    is_safe, violations = gate.validate_proposal(proposal)
    assert is_safe is True
    
    # 2. Invalid Stop Loss (Buy trade with SL above Entry)
    invalid_proposal = TradeProposal(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=Decimal("2000.0"),
        stop_loss=Decimal("2010.0"), # Invalid for BUY
        take_profit=Decimal("2020.0"),
        lot_size=Decimal("0.1")
    )
    is_safe, violations = gate.validate_proposal(invalid_proposal)
    assert is_safe is False
    assert any("LONG_SL_ABOVE_ENTRY" in v for v in violations)

    # 3. Lot Size Limit
    huge_proposal = TradeProposal(
        symbol="XAUUSD",
        direction="BUY",
        entry_price=Decimal("2000.0"),
        stop_loss=Decimal("1990.0"),
        take_profit=Decimal("2020.0"),
        lot_size=Decimal("5.0") # Max is 0.1 in the gate code
    )
    is_safe, violations = gate.validate_proposal(huge_proposal)
    assert is_safe is False
    assert any("LOT_EXCEEDED" in v for v in violations)

@pytest.mark.asyncio
async def test_node_sentinel_crisis(mock_services):
    mock_rag, mock_gemini = mock_services
    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    # Mock Gemini for adversarial review
    mock_gemini.generate_content.return_value = {
        "text": json.dumps({"approved": True, "reason": "Logic holds up"})
    }
    
    state = {
        "severity": "CRISIS",
        "proposed_trade": {
            "symbol": "XAUUSD",
            "direction": "BUY",
            "entry_price": 2000.0,
            "stop_loss": 1980.0,
            "take_profit": 2050.0,
            "lot_size": 0.05
        },
        "reasoning_trace": ["I think gold will go up because of inflation."]
    }
    
    # We need to mock the account data fetch if it were real, but it's currently hardcoded in sentinel node
    result = await advisor.node_sentinel(state)
    
    assert result["sentinel_result"]["approved"] is True
    assert "Logic holds up" in result["sentinel_result"]["reason"]

@pytest.mark.asyncio
async def test_node_consensus_layer_fallback(mock_services):
    mock_rag, mock_gemini = mock_services
    advisor = StrategyAdvisorAgent(mock_rag, mock_gemini)
    
    # Force OpenRouter failure
    advisor.openrouter.generate_completion = AsyncMock(side_effect=Exception("API Key missing"))
    
    # Mock Gemini fallback
    mock_gemini.generate_content.return_value = {
        "text": json.dumps({"approved": True, "reason": "Fallback approved", "consensus_score": 85})
    }
    
    state = {
        "proposed_trade": {"symbol": "XAUUSD", "direction": "BUY"},
        "reasoning_trace": ["Logic"],
        "scratchpad": ["Market is volatile"]
    }
    
    result = await advisor.node_consensus_layer(state)
    
    assert result["consensus_result"]["approved"] is True
    assert result["consensus_result"]["fallback_used"] is True
    assert "Gemini Fallback" in result["consensus_result"]["warning"]
