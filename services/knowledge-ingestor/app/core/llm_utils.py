"""
LLM Utilities — Institutional 3-Tier Cascading Fallback Strategy
=================================================================
Tier 1 (Primary):     OpenRouter → stepfun/step-3.5-flash:free  [SSE Streaming]
Tier 2 (Secondary):   OpenRouter → deepseek/deepseek-v3.2       [SSE Streaming]
Tier 3 (Last Resort): Google Gemini Direct (google-genai SDK)   [Streaming]

Connection Management (Professional Grade):
- httpx.AsyncClient singleton with connection pooling (no TCP overhead per call)
- Split timeout: connect=5s, read=120s (handles slow LLM without blocking forever)
- OpenRouter SSE: "stream": true — tokens arrive incrementally
- Explicit error classification: 402/429 vs network errors vs unexpected
- Gemini: native async aio.models + generate_content_stream

The deprecated `google-generativeai` package has been removed.
Provider switching is automatic. On total failure, a CRITICAL alert is emitted.
"""

import json
import logging
import re
import asyncio
import httpx
import instructor
from google import genai
from google.genai import types as genai_types
from openai import OpenAI
from typing import Dict, Any, Type, TypeVar, AsyncGenerator, cast
from app.core.app_config import config

T = TypeVar("T")
logger = logging.getLogger("OlympusLLMUtils")


# ─────────────────────────── Singleton HTTP Client ───────────────────────────

_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    """
    Return a module-level singleton httpx.AsyncClient with:
    - Connection pooling (reuses TCP — no handshake per call)
    - Split timeout: connect=5s prevents hanging on bad hosts,
      read=120s handles large LLM responses without premature cutoff
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=5.0,  # TCP handshake max 5s
                read=120.0,  # SSE/response read max 120s
                write=30.0,  # Request write max 30s
                pool=5.0,  # Pool acquire wait max 5s
            ),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
            ),
        )
    return _http_client


# ─────────────────────────── Internal Helpers ────────────────────────────────


def _is_retryable_error(e: Exception) -> bool:
    msg = str(e)
    return any(
        x in msg
        for x in [
            "402",
            "429",
            "Insufficient credits",
            "rate-limited",
            "Payment Required",
        ]
    )


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

    Non-streaming path (call_llm / call_llm_structured):
      Uses httpx.AsyncClient singleton — native async, connection pooled.

    Streaming path (stream_openrouter / call_llm_streaming):
      Uses "stream": true with SSE delta parsing.
      Yields typed event dicts for direct consumption by EventSourceResponse.
    """

    # ── Structured Extraction (instructor) ───────────────────────────────────

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

        # ── Tier 1 ────────────────────────────────────────────────────────────
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
                    cast(Any, client.chat.completions.create),
                    model=config.tier1_model,
                    response_model=response_model,
                    messages=messages,
                    max_retries=max_retries,
                    temperature=0.1,
                    extra_headers=_openrouter_headers(f"{tier}-T1-s"),
                )
                logger.info(f"✅ [Tier 1] {config.tier1_model}: OK")
                return cast(T, result)
            except Exception as e:
                last_error = e
                level = "warning" if _is_retryable_error(e) else "error"
                getattr(logger, level)(
                    f"⚠️ [Tier 1] {config.tier1_model} failed: {e} → Tier 2"
                )

        # ── Tier 2 ────────────────────────────────────────────────────────────
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
                    cast(Any, client.chat.completions.create),
                    model=config.tier2_model,
                    response_model=response_model,
                    messages=messages,
                    max_retries=max_retries,
                    temperature=0.1,
                    extra_headers=_openrouter_headers(f"{tier}-T2-s"),
                )
                logger.info(f"✅ [Tier 2] {config.tier2_model}: OK")
                return cast(T, result)
            except Exception as e:
                last_error = e
                logger.warning(
                    f"⚠️ [Tier 2] {config.tier2_model} failed: {e} → Tier 3 (Gemini Direct)"
                )

        # ── Tier 3: Google Gemini Direct ──────────────────────────────────────
        if config.google_api_key:
            try:
                google_model = config.tier3_model.split("/")[-1]
                logger.debug(f"[Tier 3] Structured → Gemini Direct: {google_model}")
                patched = instructor.from_provider(
                    f"google/{google_model}", api_key=config.google_api_key
                )
                result = await asyncio.to_thread(
                    cast(Any, patched.create),
                    response_model=response_model,
                    messages=messages,
                    max_retries=max_retries,
                )
                logger.info(f"✅ [Tier 3] Gemini Direct ({google_model}): OK")
                return cast(T, result)
            except Exception as e:
                last_error = e
                logger.error(f"❌ [Tier 3] Gemini Direct failed: {e}")

        logger.critical(
            f"🚨 ALL 3 LLM TIERS FAILED (structured). Last error: {last_error}"
        )
        raise RuntimeError(f"All 3 LLM tiers exhausted. Last error: {last_error}")

    # ── Raw Text / JSON — Non-Streaming ──────────────────────────────────────

    @staticmethod
    async def call_llm(
        system_prompt: str,
        user_prompt: str,
        tier: str = "default",
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """Call LLM with 3-tier fallback. Returns parsed JSON dict."""
        last_error: str | None = None

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

        if config.google_api_key:
            result, last_error = await LLMUtils._try_gemini_direct(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            if result is not None:
                return result

        logger.critical(f"🚨 ALL 3 LLM TIERS FAILED. Last error: {last_error}")
        return {"error": f"All 3 LLM tiers exhausted. Last error: {last_error}"}

    # ── SSE Streaming: Single OpenRouter Tier ────────────────────────────────

    @staticmethod
    async def stream_openrouter(
        model: str,
        system_prompt: str,
        user_prompt: str,
        tier_label: str,
        max_tokens: int = 4000,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream tokens from OpenRouter via SSE ("stream": true).

        Yields typed event dicts:
          {"event": "tier_start",  "data": {"tier_label": ..., "model": ...}}
          {"event": "delta",       "data": {"text": "partial token..."}}
          {"event": "tier_done",   "data": {"tokens": N, "full_text": "..."}}
          {"event": "error",       "data": {"code": 402, "reason": "..."}}
        """
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "stream": True,
        }
        yield {
            "event": "tier_start",
            "data": {"tier_label": tier_label, "model": model},
        }

        client = _get_http_client()
        full_text = ""
        token_count = 0

        try:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers=_openrouter_headers(tier_label),
            ) as response:
                if response.status_code == 402:
                    yield {
                        "event": "error",
                        "data": {
                            "code": 402,
                            "reason": "Insufficient credits",
                            "model": model,
                        },
                    }
                    return
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "unknown")
                    yield {
                        "event": "error",
                        "data": {
                            "code": 429,
                            "reason": f"Rate limited (retry-after:{retry_after}s)",
                            "model": model,
                        },
                    }
                    return
                if response.status_code != 200:
                    err_body = await response.aread()
                    yield {
                        "event": "error",
                        "data": {
                            "code": response.status_code,
                            "reason": err_body.decode("utf-8", errors="replace")[:300],
                            "model": model,
                        },
                    }
                    return

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk = line[6:].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        data = json.loads(chunk)
                        delta = data["choices"][0]["delta"].get("content", "")
                        if delta:
                            full_text += delta
                            token_count += 1
                            yield {"event": "delta", "data": {"text": delta}}
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        except httpx.ConnectTimeout:
            yield {
                "event": "error",
                "data": {"reason": f"Connect timeout (5s) for {model}", "model": model},
            }
            return
        except httpx.ReadTimeout:
            yield {
                "event": "error",
                "data": {"reason": f"Read timeout (120s) for {model}", "model": model},
            }
            return
        except httpx.NetworkError as e:
            yield {
                "event": "error",
                "data": {"reason": f"Network error: {e}", "model": model},
            }
            return
        except Exception as e:
            logger.error(f"❌ [{tier_label}] Unexpected: {e}")
            yield {"event": "error", "data": {"reason": str(e), "model": model}}
            return

        logger.info(f"✅ [{tier_label}] {model}: streamed {token_count} tokens")
        yield {
            "event": "tier_done",
            "data": {
                "tier_label": tier_label,
                "model": model,
                "tokens": token_count,
                "full_text": full_text,
            },
        }

    # ── SSE Streaming: Cascading 3-Tier ──────────────────────────────────────

    @staticmethod
    async def call_llm_streaming(
        system_prompt: str,
        user_prompt: str,
        tier: str = "direct",
        max_tokens: int = 4000,
    ) -> AsyncGenerator[dict, None]:
        """
        Stream LLM response with 3-tier cascading fallback.
        Yields typed event dicts consumable by EventSourceResponse.

        Event flow (happy path):
          tier_start → delta × N → tier_done → done

        On tier failure:
          tier_start → error → fallback → [next tier] → ...
        """
        # ── Tier 1 ────────────────────────────────────────────────────────────
        if config.openrouter_api_key:
            full_text, had_error = "", False
            async for event in LLMUtils.stream_openrouter(
                model=config.tier1_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tier_label=f"{tier}-T1",
                max_tokens=max_tokens,
            ):
                if event["event"] == "error":
                    had_error = True
                    yield {
                        "event": "fallback",
                        "data": {
                            **event["data"],
                            "from_tier": 1,
                            "model": config.tier1_model,
                        },
                    }
                    break
                if event["event"] == "delta":
                    full_text += event["data"]["text"]
                yield event

            if not had_error and full_text:
                yield {
                    "event": "done",
                    "data": {"full_text": full_text, "tier_used": 1},
                }
                return

        # ── Tier 2 ────────────────────────────────────────────────────────────
        if config.openrouter_api_key:
            full_text, had_error = "", False
            async for event in LLMUtils.stream_openrouter(
                model=config.tier2_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tier_label=f"{tier}-T2",
                max_tokens=max_tokens,
            ):
                if event["event"] == "error":
                    had_error = True
                    yield {
                        "event": "fallback",
                        "data": {
                            **event["data"],
                            "from_tier": 2,
                            "model": config.tier2_model,
                        },
                    }
                    break
                if event["event"] == "delta":
                    full_text += event["data"]["text"]
                yield event

            if not had_error and full_text:
                yield {
                    "event": "done",
                    "data": {"full_text": full_text, "tier_used": 2},
                }
                return

        # ── Tier 3: Google Gemini Streaming ───────────────────────────────────
        if config.google_api_key:
            google_model = config.tier3_model.split("/")[-1]
            yield {
                "event": "tier_start",
                "data": {"tier_label": f"{tier}-T3", "model": config.tier3_model},
            }
            try:
                gemini_client = _get_gemini_client()
                full_text, token_count = "", 0
                full_prompt = f"SYSTEM: {system_prompt}\n\nUSER: {user_prompt}"
                async for (
                    chunk
                ) in await gemini_client.aio.models.generate_content_stream(
                    model=google_model,
                    contents=full_prompt,
                    config=genai_types.GenerateContentConfig(temperature=0.1),
                ):
                    if chunk.text:
                        full_text += chunk.text
                        token_count += 1
                        yield {"event": "delta", "data": {"text": chunk.text}}

                logger.info(
                    f"✅ [Tier 3] Gemini ({google_model}): streamed {token_count} tokens"
                )
                yield {
                    "event": "tier_done",
                    "data": {
                        "tier_label": f"{tier}-T3",
                        "model": config.tier3_model,
                        "tokens": token_count,
                        "full_text": full_text,
                    },
                }
                yield {
                    "event": "done",
                    "data": {"full_text": full_text, "tier_used": 3},
                }
                return
            except Exception as e:
                logger.error(f"❌ [Tier 3] Gemini streaming failed: {e}")
                yield {
                    "event": "fallback",
                    "data": {
                        "from_tier": 3,
                        "model": config.tier3_model,
                        "reason": str(e),
                    },
                }

        logger.critical("🚨 ALL 3 LLM TIERS FAILED (streaming).")
        yield {"event": "error", "data": {"message": "All 3 LLM tiers exhausted"}}

    # ── Private Provider Helpers (non-streaming) ──────────────────────────────

    @staticmethod
    async def _try_openrouter(
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        tier_label: str,
    ) -> tuple[Dict[str, Any] | None, str | None]:
        """Non-streaming OpenRouter call via async httpx. Returns (result, error_str)."""
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
            client = _get_http_client()
            response = await client.post(
                url, json=payload, headers=_openrouter_headers(tier_label)
            )
            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                logger.info(f"✅ [{tier_label}] {model}: OK")
                return LLMUtils.parse_json_response(content), None
            elif response.status_code in [402, 429]:
                type_err = (
                    "Insufficient credits"
                    if response.status_code == 402
                    else "Rate limited"
                )
                err = f"{response.status_code} {type_err} for {model}"
                logger.warning(f"⚠️ [{tier_label}] {err}")
                return None, err
            else:
                err = f"HTTP {response.status_code} for {model}: {response.text[:200]}"
                logger.warning(f"⚠️ [{tier_label}] {err}")
                return None, err
        except httpx.ConnectTimeout:
            err = f"Connect timeout for {model}"
            logger.warning(f"⚠️ [{tier_label}] {err}")
            return None, err
        except httpx.ReadTimeout:
            err = f"Read timeout for {model}"
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
        """Non-streaming Gemini call using native async."""
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
        if response is None:
            return {"error": "LLM returned None"}

        clean = re.sub(r"```json\s*", "", response)
        clean = re.sub(r"```\s*$", "", clean, flags=re.MULTILINE).strip()

        try:
            return cast(Dict[str, Any], json.loads(clean))
        except json.JSONDecodeError:
            pass

        brace_start = clean.find("{")
        brace_end = clean.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            try:
                return cast(Dict[str, Any], json.loads(clean[brace_start : brace_end + 1]))
            except json.JSONDecodeError:
                pass

        try:
            fixed = re.sub(r'(?<=[:",])\s*\n\s*(?=[^\]\}])', " ", clean)
            if "\n" in clean:
                fixed = clean.replace("\n", "\\n")
            fixed = re.sub(r"(\w+):", r'"\1":', fixed)
            return cast(Dict[str, Any], json.loads(fixed))
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
