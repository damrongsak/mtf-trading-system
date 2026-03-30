"""
Document Structural Analyzer for Project Olympus.
Analyzes document layout and key themes before detailed extraction.
"""

import logging
from typing import List
from pydantic import BaseModel, Field
from app.core.llm_utils import LLMUtils

logger = logging.getLogger("DocumentAnalyzer")


class DocStructure(BaseModel):
    """Schema for document structural analysis"""

    title: str = Field(..., description="The definitive title of the document")
    main_themes: List[str] = Field(..., description="Top 3-5 primary themes or topics")
    key_entities: List[str] = Field(
        ..., description="Most prominent organizations, assets, or people mentioned"
    )
    structure_map: List[str] = Field(
        ..., description="Mental map of the document (sections and their purpose)"
    )
    suggested_ontology_labels: List[str] = Field(
        ..., description="Which Olympus labels are most relevant for this doc"
    )


class DocumentAnalyzer:
    """Analyzes documents to provide global context for extraction tiers"""

    ANALYSIS_PROMPT = """You are THE LEAD ANALYST for Project Olympus.
Before we extract detailed data, analyze this document's structure and themes.

Your goals:
1. Identify the true title and main themes.
2. List the most important entities that will serve as 'Anchor Nodes'.
3. Create a brief map of the document's flow.

Input: First few pages/sections of the document.
Output: Valid DocStructure JSON."""

    @staticmethod
    async def analyze(content_preview: str) -> DocStructure:
        """Perform structural analysis on a preview of the content"""
        logger.info("🔍 Analyzing document structure...")

        try:
            # Use the first 8000 chars for analysis
            preview = content_preview[:8000]

            analysis = await LLMUtils.call_llm_structured(
                system_prompt=DocumentAnalyzer.ANALYSIS_PROMPT,
                user_prompt=f"Document Preview:\n{preview}",
                response_model=DocStructure,
                tier="doc_analysis",
            )

            logger.info(f"✅ Analysis Complete: {analysis.title}")
            return analysis
        except Exception as e:
            logger.error(f"Document analysis failed: {e}")
            # Return a basic structure as fallback
            return DocStructure(
                title="Unknown Document",
                main_themes=["General Intelligence"],
                key_entities=[],
                structure_map=["Unstructured Content"],
                suggested_ontology_labels=["Paper"],
            )
