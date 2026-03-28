"""
LLM Utilities — Institutional 3-Tier Cascading Fallback Strategy
=================================================================
Tier 1 (Primary):     OpenRouter → stepfun/step-3.5-flash:free
Tier 2 (Secondary):   OpenRouter → deepseek/deepseek-v3.2
Tier 3 (Last Resort): Google Gemini Direct (google-genai SDK)

Uses the NEW `google.genai` SDK (google-genai>=1.0.0).
The deprecated `google-generativeai` package has been removed.

Provider switching is automatic. On total failure, a CRITICAL alert is emitted.
"""

import json
import logging
import re
import asyncio
import requests
import instructor
from google import genai
from google.genai import types as genai_types
from openai import OpenAI
from typing import Dict, Any, Type, TypeVar
from app.core.app_config import config

T = TypeVar("T")
logger = logging.getLogger("OlympusLLMUtils")


# ─────────────────────────── Internal Helpers ────────────────────────────────

def _is_credit_error(e: Exception) -> bool:
    msg = str(e)
    return "402" in msg or "Insufficient credits" in msg or "Payment Required" in msg


def _openrouter_headers(tier_label: str) -> dict:
    return {
        "Authorization": f"Bearer {config.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://openclaw.local",
        "X-Title": f"OlympusIngestor-{tier_label}",
    }


def _get_gemini_client() -> genai.Client:
    """Return a configured google.genai client."""
    return genai.Client(api_key=config.google_api_key)


# ─────────────────────────── LLMUtils ────────────────────────────────────────

class LLMUtils:
    """
    Professional 3-tier cascading LLM utility.

    Tier 1 & 2 route through OpenRouter.
    Tier 3 falls back to direct Google Gemini (new google-genai SDK).
    All tiers are tried before raising CRITICAL.
    """

    # ── Structured Extraction ─────────────────────────────────────────────────

    @staticmethod
    async def call_llm_structured(
        system_prompt: str,
        user_prompt: str,
        response_model: Type[T],
        tier: str = "default",
        max_retries: int = 2,
    ) -> T:
        """Call LLM and return a validated Pydantic model using instructor."""
        last_error: Exception | None = None
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # ── Tier 1: OpenRouter – stepfun/step-3.5-flash:free ─────────────────
        if config.openrouter_api_key:
            try:
                logger.debug(f"[Tier 1] Structured → {config.tier1_model}")
                client = instructor.from_openai(
                    OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=config.openrouter_api_key,
                    ),
                    mode=instructor.Mode.JSON,
                )
                result = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=config.tier1_model,
                    response_model=response_model,
                    messages=messages,
                    max_retries=max_retries,
                    temperature=0.1,
                    extra_headers=_openrouter_headers(f"{tier}-T1-s"),
                )
                logger.info(f"✅ [Tier 1] {config.tier1_model}: OK")
                return result
            except Exception as e:
                last_error = e
                level = "warning" if _is_credit_error(e) else "warning"
                getattr(logger, level)(
                    f"⚠️ [Tier 1] {config.tier1_model} failed: {e} → Tier 2"
                )

        # ── Tier 2: OpenRouter – deepseek/deepseek-v3.2 ──────────────────────
        if config.openrouter_api_key:
            try:
                logger.debug(f"[Tier 2] Structured → {config.tier2_model}")
                client = instructor.from_openai(
                    OpenAI(
                        base_url="https://openrouter.ai/api/v1",
                        api_key=config.openrouter_api_key,
                    ),
                    mode=instructor.Mode.JSON,
                )
                result = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=config.tier2_model,
                    response_model=response_model,
                    messages=messages,
                    max_retries=max_retries,
                    temperature=0.1,
                    extra_headers=_openrouter_headers(f"{tier}-T2-s"),
                )
                logger.info(f"✅ [Tier 2] {config.tier2_model}: OK")
                return result
            except Exception as e:
                last_error = e
                logger.warning(
                    f"⚠️ [Tier 2] {config.tier2_model} failed: {e} → Tier 3 (Gemini Direct)"
                )

        # ── Tier 3: Google Gemini Direct (new google-genai SDK) ───────────────
        if config.google_api_key:
            try:
                google_model = config.tier3_model.split("/")[-1]
                logger.debug(f"[Tier 3] Structured → Gemini Direct: {google_model}")
                gemini_client = _get_gemini_client()
                # Use instructor.from_provider for the new google-genai SDK
                patched = instructor.from_provider(
                    f"google/{google_model}",
                    api_key=config.google_api_key,
                )
                result = await asyncio.to_thread(
                    patched.create,
                    response_model=response_model,
                    messages=messages,
                    max_retries=max_retries,
                )
                logger.info(f"✅ [Tier 3] Gemini Direct ({google_model}): OK")
                return result
            except Exception as e:
                last_error = e
                logger.error(f"❌ [Tier 3] Gemini Direct failed: {e}")

        # ── TOTAL FAILURE ─────────────────────────────────────────────────────
        logger.critical(
            "🚨 ALL 3 LLM TIERS FAILED (structured). "
            f"T1={config.tier1_model} T2={config.tier2_model} "
            f"T3={config.tier3_model}. Last error: {last_error}"
        )
        raise RuntimeError(f"All 3 LLM tiers exhausted. Last error: {last_error}")

    # ── Raw Text / JSON Extraction ────────────────────────────────────────────

    @staticmethod
    async def call_llm(
        system_prompt: str,
        user_prompt: str,
        tier: str = "default",
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """Call LLM with 3-tier fallback. Returns parsed JSON dict."""
        last_error: str | None = None

        # ── Tier 1 ────────────────────────────────────────────────────────────
        if config.openrouter_api_key:
            result, last_error = await LLMUtils._try_openrouter(
                model=config.tier1_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                tier_label=f"{tier}-T1",
            )
            if result is not None:
                return result

        # ── Tier 2 ────────────────────────────────────────────────────────────
        if config.openrouter_api_key:
            result, last_error = await LLMUtils._try_openrouter(
                model=config.tier2_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                tier_label=f"{tier}-T2",
            )
            if result is not None:
                return result

        # ── Tier 3: Gemini Direct (new google-genai SDK) ──────────────────────
        if config.google_api_key:
            result, last_error = await LLMUtils._try_gemini_direct(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            if result is not None:
                return result

        # ── TOTAL FAILURE ─────────────────────────────────────────────────────
        logger.critical(
            "🚨 ALL 3 LLM TIERS FAILED. "
            f"T1={config.tier1_model} T2={config.tier2_model} "
            f"T3={config.tier3_model}. Last error: {last_error}"
        )
        return {"error": f"All 3 LLM tiers exhausted. Last error: {last_error}"}

    # ── Private Provider Helpers ──────────────────────────────────────────────

    @staticmethod
    async def _try_openrouter(
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        tier_label: str,
    ) -> tuple[Dict[str, Any] | None, str | None]:
        """Try a single OpenRouter model. Returns (result, error_str)."""
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }
        try:
            logger.debug(f"[{tier_label}] OpenRouter/{model}…")
            response = await asyncio.to_thread(
                requests.post,
                url,
                json=payload,
                headers=_openrouter_headers(tier_label),
                timeout=180,
            )
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                logger.info(f"✅ [{tier_label}] {model}: OK")
                return LLMUtils.parse_json_response(content), None
            elif response.status_code == 402:
                err = f"402 Insufficient credits for {model}"
                logger.warning(f"⚠️ [{tier_label}] {err}")
                return None, err
            else:
                err = f"HTTP {response.status_code} for {model}: {response.text[:200]}"
                logger.warning(f"⚠️ [{tier_label}] {err}")
                return None, err
        except Exception as e:
            err = f"Exception for {model}: {e}"
            logger.warning(f"⚠️ [{tier_label}] {err}")
            return None, err

    @staticmethod
    async def _try_gemini_direct(
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[Dict[str, Any] | None, str | None]:
        """
        Try Google Gemini using the new google-genai SDK (async).
        Uses client.aio.models.generate_content for non-blocking IO.
        """
        google_model = config.tier3_model.split("/")[-1]
        try:
            logger.debug(f"[Tier 3] Gemini Direct (async): {google_model}…")
            gemini_client = _get_gemini_client()
            full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"
            response = await gemini_client.aio.models.generate_content(
                model=google_model,
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(temperature=0.1),
            )
            if response and response.text:
                logger.info(f"✅ [Tier 3] Gemini Direct ({google_model}): OK")
                return LLMUtils.parse_json_response(response.text), None
            else:
                err = "Gemini Direct returned empty response"
                logger.error(f"❌ [Tier 3] {err}")
                return None, err
        except Exception as e:
            err = f"Gemini Direct error: {e}"
            logger.error(f"❌ [Tier 3] {err}")
            return None, err

    # ── JSON Parsing Utility ──────────────────────────────────────────────────

    @staticmethod
    def parse_json_response(response: str) -> Dict[str, Any]:
        """Extract and parse JSON from LLM response reliably."""
        clean = re.sub(r"```json\s*", "", response)
        clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE).strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError:
            pass

        brace_start = clean.find("{")
        brace_end = clean.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return json.loads(clean[brace_start : brace_end + 1])
            except json.JSONDecodeError:
                pass

        try:
            fixed = re.sub(r'(?<=[:",])\s*\n\s*(?=[^\]\}])', " ", clean)
            if "\n" in clean:
                fixed = clean.replace("\n", "\\n")
            fixed = re.sub(r"(\w+):", r'"\1":', fixed)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        cypher_match = re.search(r'"cypher_queries"\s*:\s*\[(.*?)\]', clean, re.DOTALL)
        if cypher_match:
            queries_str = cypher_match.group(1)
            query_matches = re.findall(r'"((?:[^"\\]|\\.)*)"', queries_str, re.DOTALL)
            queries = [
                q.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
                for q in query_matches
                if q.strip()
            ]
            if queries:
                return {"cypher_queries": queries}

        return {"error": "Failed to parse JSON", "raw": response[:500]}
