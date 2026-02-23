import asyncio
import os
import sys
import json
from typing import Dict, Any

# Add the current directory to sys.path to allow importing app
sys.path.append(os.getcwd())

from app.services.gemini import GeminiClient, GeminiSchemaMapper
from app.core.config import settings
from app.core.schemas import (
    QueryOptimization,
    PlanDecomposition,
    ToolSelection,
    SentimentResult,
    EvaluationResult
)

def test_schema_mapper():
    print("--- Testing GeminiSchemaMapper ---")
    schemas = [
        QueryOptimization,
        PlanDecomposition,
        ToolSelection,
        SentimentResult,
        EvaluationResult
    ]
    
    for schema_cls in schemas:
        try:
            gemini_schema = GeminiSchemaMapper.to_gemini_schema(schema_cls)
            print(f"✅ Schema {schema_cls.__name__} mapped successfully.")
            
            # Verify no forbidden fields
            forbidden = ["additionalProperties", "$defs", "definitions", "title"]
            schema_str = json.dumps(gemini_schema)
            for f in forbidden:
                if f'"{f}"' in schema_str:
                    print(f"  ❌ Warning: Found forbidden field '{f}' in {schema_cls.__name__}")
        except Exception as e:
            print(f"  ❌ Error mapping {schema_cls.__name__}: {e}")

async def test_live_api():
    print("\n--- Testing Live Gemini API (Safety + Models) ---")
    client = GeminiClient()
    
    # Test models
    models_to_test = [
        settings.gemini.flash_lite_model_id,
        settings.gemini.flash_model_id,
        settings.gemini.model_id
    ]
    
    test_query = "Give me a high-leverage XAUUSD trading plan for the Asia session. Discuss risk management."

    for model in models_to_test:
        print(f"Testing model: {model}...")
        try:
            # We use a simple prompt to check connectivity and safety
            response = await client.generate_content(
                model=model,
                contents=[test_query]
            )
            text = response.get("text", "")
            if text:
                print(f"  ✅ Received response ({len(text)} chars).")
            else:
                print(f"  ⚠️ Received EMPTY response. Check logs for finish_reason.")
        except Exception as e:
            print(f"  ❌ Error with {model}: {e}")

if __name__ == "__main__":
    test_schema_mapper()
    asyncio.run(test_live_api())
