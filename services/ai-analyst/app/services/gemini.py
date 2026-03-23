from typing import Union, List, Optional, Dict, Any
from google import genai
from google.genai import types
import json
import re

class GeminiSchemaMapper:
    """
    Utility to transform Pydantic/JSON schemas into strict Gemini-compatible formats.
    Gemini API is picky about 'additionalProperties', '$defs', and certain naming conventions.
    This version recursively resolves $refs to support nested models.
    """
    @staticmethod
    def to_gemini_schema(schema: Any) -> Dict[str, Any]:
        if hasattr(schema, "model_json_schema"):
            schema_dict = schema.model_json_schema()
        elif isinstance(schema, dict):
            schema_dict = schema
        else:
            return schema

        # 1. Extract definitions if any
        definitions = schema_dict.get("$defs", schema_dict.get("definitions", {}))
        
        # 2. Recursively resolve refs and cleanup
        return GeminiSchemaMapper._process_node(schema_dict, definitions)

    @staticmethod
    def _process_node(node: Any, definitions: Dict[str, Any]) -> Any:
        if isinstance(node, list):
            return [GeminiSchemaMapper._process_node(item, definitions) for item in node]
        
        if not isinstance(node, dict):
            return node

        # Handle References
        if "$ref" in node:
            ref_path = node["$ref"]
            ref_key = ref_path.split("/")[-1]
            if ref_key in definitions:
                 # Resolve the reference and process the resolved node
                 return GeminiSchemaMapper._process_node(definitions[ref_key], definitions)
            else:
                 logger.warning(f"Schema Mapper: Could not resolve reference {ref_path}")
                 return node

        # Remove unsupported Gemini fields
        unsupported = ["additionalProperties", "additional_properties", "title", "description", "$defs", "definitions"]
        
        cleaned = {}
        for k, v in node.items():
            if k in unsupported:
                continue
            
            # Special case for "anyOf" or "oneOf" (Gemini is picky, usually prefers just one type or simpler union)
            # For now, we'll keep them and hope Gemini handles the standard ones
            
            cleaned[k] = GeminiSchemaMapper._process_node(v, definitions)

        return cleaned

from app.core.config import settings
import time
import asyncio
import logging

logger = logging.getLogger("ai-analyst")

class GeminiClient:
    def __init__(self, client_factory=None):
        if not settings.gemini.api_key:
            raise ValueError("GOOGLE_API_KEY is not set")
        
        # Dependency Injection for testing
        self.client_factory = client_factory or genai.Client
        
        # Initialize the client with the API key
        self.client = self.client_factory(api_key=settings.gemini.api_key)
        # Using configured model
        self.model_id = settings.gemini.model_id
        
        # Circuit Breaker state: model_name -> expiration_timestamp (float)
        self._rate_limit_lockouts = {}
        
        # Phase 1: FMEA Guardrails
        from app.services.monitoring import monitor
        self.drift_monitor = monitor

    async def _inject_safe_mode_instruction(self, contents: list) -> list:
        """
        Injects a Safe Mode warning if market drift is detected.
        """
        # This is a simplified check. In production, we'd pass the current OHLC to the monitor.
        # For now, we assume the monitor is updated out-of-band by a background job.
        # If we can't find a recent drift check, we default to False.
        is_drifted = getattr(self.drift_monitor, "last_drift_status", False)
        
        if is_drifted:
            safe_mode_msg = (
                "\n\n[SAFE MODE ACTIVE: HIGH MARKET DRIFT DETECTED]\n"
                "The current market environment significantly deviates from historical patterns. "
                "Prioritize 'Wait' or 'Base SMC' recommendations. Be extremely conservative. "
                "Avoid complex probabilistic predictions."
            )
            # Find the last text part and append
            for content in reversed(contents):
                if isinstance(content, str):
                    # Replace the entire string with the appended version
                    idx = contents.index(content)
                    contents[idx] = content + safe_mode_msg
                    break
        return contents

    async def generate_content(self, model: Union[str, list], contents: list, config: dict = None, thinking_config: dict = None, api_key: str = None, response_schema: type = None, safety_settings: Optional[List[types.SafetySetting]] = None) -> dict:
        """
        Generic generation with support for Thinking models, Structured Output, and Active Fallback.
        Implements a Circuit Breaker and Safe Mode Guardrail.
        """
        if not contents or (isinstance(contents, list) and len(contents) == 0):
             logger.error("Gemini generate_content called with empty contents.")
             raise ValueError("Empty contents provided for generation")

        # Phase 1: Guardrail Injection
        contents = await self._inject_safe_mode_instruction(contents)
        
        models = [model] if isinstance(model, str) else model
        last_error = None
        
        current_time = time.time()
        
        for i, current_model in enumerate(models):
            # 1. Circuit Breaker Check
            lockout_expiry = self._rate_limit_lockouts.get(current_model, 0)
            if current_time < lockout_expiry:
                remaining_lockout = int(lockout_expiry - current_time)
                logger.warning(f"Circuit Breaker: Skipping {current_model} (Locked out for {remaining_lockout}s)")
                continue # Instantly try the next fallback

            try:
                # Merge config
                current_config = dict(config) if config else {}
                if thinking_config:
                    current_config['thinking_config'] = thinking_config
                
                # Configure Structured Output
                if response_schema:
                    current_config['response_mime_type'] = "application/json"
                    gemini_schema = GeminiSchemaMapper.to_gemini_schema(response_schema)
                    logger.debug(f"DEBUG: Generated Gemini Schema for {response_schema.__name__}: {json.dumps(gemini_schema)}")
                    current_config['response_schema'] = gemini_schema

                # Configure Safety Settings (Prevent blocking legitimate institutional analysis)
                # CRITICAL: Even if BLOCK_NONE is set, Gemini may block if the prompt is flagged by internal filters.
                # However, providing NONE explicitly is the best we can do.
                if safety_settings:
                    current_config['safety_settings'] = safety_settings
                else:
                    # Default permissive safety settings for trading analysis
                    current_config['safety_settings'] = [
                        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
                        types.SafetySetting(category="HARM_CATEGORY_CIVIC_INTEGRITY", threshold="BLOCK_NONE")
                    ]

                # Transient client for BYOK if key provided
                active_client = self.client
                if api_key and api_key != settings.gemini.api_key:
                    active_client = self.client_factory(api_key=api_key)

                import traceback
                logger.debug(f"DEBUG: Calling generate_content on {current_model}...")
                
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Resolve config into the right type
                        # FORCE: tool_config to NONE to prevent UNEXPECTED_TOOL_CALL errors
                        if 'tool_config' not in current_config:
                             current_config['tool_config'] = types.ToolConfig(
                                 function_calling_config=types.FunctionCallingConfig(mode='NONE')
                             )
                        
                        gen_config = types.GenerateContentConfig(**current_config)
                        
                        response = await active_client.aio.models.generate_content(
                            model=current_model,
                            contents=contents,
                            config=gen_config
                        )
                        break # Success! Break retry loop
                    except Exception as e:
                        error_str = str(e).upper()
                        is_unavailable_error = "503" in error_str or "UNAVAILABLE" in error_str
                        
                        if is_unavailable_error and attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 2
                            logger.warning(f"Model {current_model} hit 503 (High Demand). Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})...")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        # If not a retryable 503 or we exhausted retries, log and raise for fallback logic
                        logger.error(f"DEBUG: CRASH in google-genai SDK call on {current_model}: {e}\n{traceback.format_exc()}")
                        raise e

                # Check for safety blocks
                if response.candidates and response.candidates[0].finish_reason:
                    reason = response.candidates[0].finish_reason
                    if reason != "STOP":
                        # If blocked by safety, we TRY to extract any text if it exists (partial blocking)
                        logger.warning(f"Gemini response finished with reason: {reason}. Text may be truncated or blocked.")
                        if i < len(models) - 1:
                            logger.info(f"Retrying with fallback model due to {reason} block...")
                            continue 
                
                # Safe response extraction
                text_content = ""
                thoughts = []
                tool_calls_found = []

                if response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text_content += part.text
                            if hasattr(part, 'thought') and part.thought:
                                thoughts.append(str(part.thought))
                            # Check for tool_call in part (SDK specific)
                            if hasattr(part, 'tool_call') and part.tool_call:
                                tool_calls_found.append(part.tool_call)

                # Fallback to .text if my manual extraction is empty but .text works
                if not text_content:
                    try:
                        text_content = response.text or ""
                    except Exception:
                        pass

                if not text_content and not tool_calls_found:
                    logger.debug(f"DEBUG: Gemini response is empty of both text and tools. Finish Reason: {getattr(response.candidates[0], 'finish_reason', 'UNKNOWN') if response.candidates else 'NO_CANDIDATE'}")

                return {
                    "text": text_content,
                    "thoughts": "\n".join(thoughts) if thoughts else None,
                    "tool_calls": tool_calls_found, # Optional: if we ever want to use SDK-native tools
                    "usage": getattr(response, 'usage_metadata', None),
                    "finish_reason": getattr(response.candidates[0], 'finish_reason', 'STOP') if response.candidates else 'NO_CANDIDATE'
                }
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                last_error = e
                error_str = str(e).upper()
                
                # Detect recoverable infrastructural errors
                is_quota_error = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "QUOTA" in error_str
                is_unavailable_error = "404" in error_str or "NOT_FOUND" in error_str or "503" in error_str
                
                if is_quota_error or is_unavailable_error:
                    # Apply Circuit Breaker lock out
                    # Quota (429) -> 60s, Unavailable (503) -> 15s (shorter as it might be transient)
                    lockout_duration = 60 if is_quota_error else 15
                    self._rate_limit_lockouts[current_model] = time.time() + lockout_duration
                    
                    if i < len(models) - 1:
                        reason = "Rate Limit (429)" if is_quota_error else "Unavailable (404/503)"
                        logger.warning(f"Model {current_model} hit {reason}. Locked out for {lockout_duration}s. Falling back to {models[i+1]}...")
                        await asyncio.sleep(0.5) # Brief pause before next attempt
                        continue
                
                logger.error(f"Gemini Generation Error on {current_model}: {e}\n{error_trace}")
                if i == len(models) - 1:
                    # If we exhausted all fallback models, raise the last encountered error
                    raise e
                    
        # If all models were skipped via Circuit Breaker and no API call was even attempted
        if last_error:
            raise last_error
        else:
            raise RuntimeError(f"All requested models ({models}) are currently locked out by the Circuit Breaker due to Rate Limits.")

    async def generate_market_outlook(self, context: dict, api_key: str = None, model_id: str = None, thinking_config: dict = None) -> str:
        """
        Generates a market outlook based on technical indicators and SMC context.
        Supports multimodal input (images).
        Values in `context` can optionally override `api_key` and `model_id`.
        """
        
        # Determine strict client config
        active_key = api_key or settings.gemini.api_key
        active_model = model_id or self.model_id
        
        # Instantiate transient client if key differs, else use default
        client = self.client
        if api_key and api_key != settings.gemini.api_key:
            client = genai.Client(api_key=active_key)

        prompt = f"""
        You are an elite institutional trader analyzing the financial markets. 
        Analyze the following market context and provide a concise, narrative-based outlook.
        
        Context:
        - Trend (4H): {context.get('trend_4h', 'Unknown')}
        - Price: {context.get('current_price', 'Unknown')}
        - Key Levels: {context.get('key_levels', [])}
        - Recent Signals: {context.get('recent_signals', [])}
        
        Format your response in Markdown with these sections:
        ## 📊 Market Context
        ## 🗝️ Key Levels to Watch
        ## 🧠 Strategy Bias (Bullish/Bearish/Neutral)
        """
        
        contents = [prompt]
        if "image_b64" in context and context["image_b64"]:
            print("INFO: Processing multimodal request with image")
            try:
                import base64
                from io import BytesIO
                from PIL import Image
                
                # Convert base64 to Image object usually required by some SDKs or just pass as blob
                # Google GenAI SDK supports dictionary for parts: {'mime_type': 'image/jpeg', 'data': bytes}
                
                img_data = base64.b64decode(context["image_b64"])
                image_part = {"mime_type": "image/jpeg", "data": img_data}
                contents.append(image_part)
            except Exception as e:
                return f"Error processing image: {str(e)}"

        try:
            # Use Tier 3 fallback for Market Outlook (Pro/Logic heavy)
            response = await self.generate_content(
                model=[active_model, "gemini-2.5-pro", "gemini-2.0-pro"],
                contents=contents
            )
            return response.get("text", "")
        except Exception as e:
            logger.error(f"Gemini Error in generate_market_outlook: {e}")
            return f"Error generating outlook: {str(e)}"

    async def analyze_journal_entry(self, entry_content: str, similar_entries: list = None, user_id: str = None) -> str:
        """
        Analyzes a journal entry and compares it with similar past entries to identify patterns.
        If similar_entries is None, it attempts to fetch them via RAG (requires user_id).
        """
        if similar_entries is None:
            if not user_id:
                raise ValueError("user_id is required for RAG search")
                
            from app.services.rag import RAGService
            rag = RAGService(self)
            try:
                similar_entries = await rag.search_similar_entries(entry_content, user_id=user_id)
            except Exception as e:
                # Fallback if RAG fails (e.g., connection issue)
                similar_entries = []
                print(f"RAG fetch failed: {e}")

        context_str = "\n".join([f"- {e}" for e in similar_entries])
        prompt = f"""
        Analyze this trading journal entry for psychological patterns and mistakes.
        Compare it with these similar past entries:
        {context_str}
        
        Current Entry:
        "{entry_content}"
        
        Provide a bulleted list of:
        - Detected Emotion
        - Recurring Mistake (if any)
        - Actionable Advice
        """
        
        try:
            # Tier 3 fallback for Journal Analysis
            response = await self.generate_content(
                model=[self.model_id, "gemini-2.5-pro", "gemini-2.0-pro"],
                contents=[prompt]
            )
            return response.get("text", "")
        except Exception as e:
            logger.error(f"Error analyzing journal: {e}")
            return f"Error analyzing journal: {str(e)}"

    async def generate_smc_analysis(self, smc_data: dict, api_key: str = None, model_id: str = None) -> str:
        """
        Specialized analysis for Smart Money Concepts
        """
        prompt = f"""
        Analyze this SMC Data and find the best trade setup.
        Data: {smc_data}
        
        Focus on:
        1. Liquidity Sweeps
        2. Order Blocks
        3. Fair Value Gaps
        """
        
        try:
            # Tier 2 fallback for SMC Analysis
            # Remove thinking_config from here if not supported by Flash 1.5/2.5
            response = await self.generate_content(
                model=[model_id or self.model_id, "gemini-2.5-flash", "gemini-2.0-flash"],
                contents=[prompt],
                api_key=api_key
            )
            return response.get("text", "")
        except Exception as e:
            logger.error(f"Error generating SMC analysis: {e}")
            return f"Error generating SMC analysis: {str(e)}"

    async def generate_smc_narrative(self, smc_data: dict, price_context: dict, api_key: str = None, model_id: str = None) -> str:
        """
        Generates a narrative based on SMC data (Order Blocks, FVGs, Structure).
        """
        active_key = api_key or settings.gemini.api_key
        active_model = model_id or self.model_id
        
        client = self.client
        if api_key and api_key != settings.gemini.api_key:
            client = genai.Client(api_key=active_key)

        prompt = f"""
        You are an expert Smart Money Concepts (SMC) trader.
        Analyze the current market structure and generate a professional trade narrative.
        
        Market Context:
        - Price: {price_context.get('price')}
        - Trend: {price_context.get('trend')}
        
        SMC Structure:
        - Structure: {smc_data.get('structure', {})}
        - Order Blocks: {smc_data.get('order_blocks', [])}
        - FVGs: {smc_data.get('fvgs', [])}
        - Liquidity Sweeps: {smc_data.get('liquidity_sweeps', [])}
        
        Explain the "Story of Price". specificially:
        1. liquidity objectives (where is the draw on liquidity?)
        2. structural bias (internal vs external structure)
        3. valid POIs (unmigitated OBs or FVGs)
        
        Keep it concise (under 200 words). Use bolding for key terms like **BOS**, **CHoCH**, **Order Block**.
        """
        
        try:
            # Tier 2 fallback for SMC Narrative
            response = await self.generate_content(
                model=[active_model, "gemini-2.5-flash", "gemini-2.0-flash"],
                contents=[prompt]
            )
            return response.get("text", "")
        except Exception as e:
            logger.error(f"Error generating narrative: {e}")
            return f"Error generating narrative: {str(e)}"

    async def generate_research_report(self, query: str, context: str, model_id: str = None) -> str:
        """
        Generates a deep research report based on retrieved context.
        """
        from app.core.prompts import DEEP_RESEARCH_PROMPT_TEMPLATE
        
        try:
            prompt = DEEP_RESEARCH_PROMPT_TEMPLATE.format(
                query=query,
                context=context
            )
            
            # Tier 3 fallback for Research Report
            response = await self.generate_content(
                model=[model_id or self.model_id, "gemini-2.5-pro", "gemini-2.0-pro"],
                contents=[prompt]
            )
            return response.get("text", "")
        except Exception as e:
            logger.error(f"Error generating research report: {e}")
            return f"Error generating research report: {str(e)}"