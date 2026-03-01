from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union

class QueryOptimization(BaseModel):
    """Schema for query optimization and intent classification."""
    optimized_query: str = Field(description="The technical English version of the user's query.")
    intent: str = Field(description="The classified intent of the query (e.g., TOOL_USE, MARKET_ANALYSIS, etc.)")

class PlanDecomposition(BaseModel):
    """Schema for breaking down complex requests into steps."""
    plan_steps: List[str] = Field(description="A list of 3-5 logical reasoning steps.")

class SystemToolCall(BaseModel):
    """Schema for an individual tool call."""
    tool_name: str = Field(description="The name of the tool to execute.")
    tool_input: Union[dict, str, list] = Field(description="The parameters or input for the tool.")
    reasoning: str = Field(description="Brief explanation of why this tool is needed.")

class SystemToolSelection(BaseModel):
    """Schema for selecting multiple tools or providing a direct answer."""
    tool_calls: List[SystemToolCall] = Field(default_factory=list, description="List of tools to execute.")
    direct_answer: Optional[str] = Field(None, description="A direct response if no tools are needed.")

class SentimentResult(BaseModel):
    """Schema for market sentiment analysis."""
    score: float = Field(description="Sentiment score from -1.0 (Bearish) to 1.0 (Bullish).")
    reason: str = Field(description="A concise 1-sentence explanation for the score.")
    key_drivers: List[str] = Field(default_factory=list, description="Top 3-5 keywords or entities driving this sentiment (e.g. ['Trump', 'Iran', 'Tariff']).")

class EvaluationResult(BaseModel):
    """Schema for evaluating AI responses (Agentic RAG)."""
    is_satisfactory: bool = Field(description="Whether the response meets the user's requirements.")
    feedback: Optional[str] = Field(None, description="Feedback for refinement if unsatisfactory.")
