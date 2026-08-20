"""
LLM provider abstraction.

Supports:
  - xAI Grok chat completions
  - Hugging Face Inference API chat completions
  - RapidAPI OPEN AI chat completions
  - Demo mode: deterministic, rule-based text generation, no API key required

WHY A JSON-PROMPT TOOL-CALLING LOOP (viva note):
Most Hugging Face Inference API chat models do not expose native
function/tool-calling the way the Anthropic or OpenAI APIs do. To still
get genuine agentic tool use, we tell the model exactly which tools exist
(name + JSON schema of arguments) in the system prompt and require it to
reply with ONE JSON object per turn:

    {"action": "call_tool", "tool": "<name>", "arguments": {...}}
    or
    {"action": "final_answer", "content": "..."}

The agent loop (see base_agent.py) parses that JSON, executes the tool in
Python, feeds the JSON result back to the model as the next message, and
repeats until the model emits "final_answer" or a max-step limit is hit.
This is a standard, robust pattern for building tool-using agents on top
of models without native function calling, and it keeps ALL numeric
computation in Python (Section 5 of the assignment).
"""
from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    text: str
    is_demo: bool = False


class LLMProvider:
    """Abstract base."""

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        raise NotImplementedError


class GrokProvider(LLMProvider):
    """Small dependency-free client for xAI's OpenAI-compatible API."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model_name = model_name or os.environ.get("XAI_MODEL", "grok-4-latest")
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        self.base_url = (base_url or os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1/chat/completions")).rstrip("/")
        if not self.api_key:
            raise RuntimeError("XAI_API_KEY is not set. Add it to .env, or run with DEMO_MODE=true.")

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        payload = json.dumps({
            "model": self.model_name,
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "max_tokens": 900,
            "temperature": 0.2,
            "stream": False,
        }).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(self.base_url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            return LLMResponse(text=result["choices"][0]["message"]["content"], is_demo=False)
        except urllib.error.HTTPError as exc:
            try:
                error_body = exc.read().decode("utf-8", errors="replace")[:1000]
                error_data = json.loads(error_body)
                detail = error_data.get("error", error_data)
                if isinstance(detail, dict):
                    detail = detail.get("message") or detail.get("code") or str(detail)
            except Exception:  # noqa: BLE001 - retain the original HTTP failure
                detail = exc.reason
            logger.error("Grok API call failed (%s): %s", exc.code, detail)
            raise RuntimeError(f"Grok API call failed (HTTP {exc.code}): {detail}") from exc
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            logger.error("Grok API call failed: %s", exc)
            raise RuntimeError(f"Grok API call failed: {exc}") from exc


class HuggingFaceProvider(LLMProvider):
    """Wraps huggingface_hub.InferenceClient for chat-completion style calls."""

    def __init__(self, model_name: Optional[str] = None, api_token: Optional[str] = None):
        from huggingface_hub import InferenceClient  # imported lazily

        self.model_name = model_name or os.environ.get("HF_MODEL") or os.environ.get(
            "MODEL_NAME", "meta-llama/Llama-3.1-8B-Instruct"
        )
        token = api_token or os.environ.get("HF_TOKEN") or os.environ.get("HF_API_TOKEN")
        if not token:
            raise RuntimeError(
                "HF_TOKEN is not set. Add it to your .env file, or run with DEMO_MODE=true."
            )
        self.client = InferenceClient(model=self.model_name, token=token)

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        chat_messages = [{"role": "system", "content": system_prompt}] + messages
        try:
            result = self.client.chat_completion(
                messages=chat_messages,
                max_tokens=900,
                temperature=0.2,
            )
            text = result.choices[0].message.content
            return LLMResponse(text=text, is_demo=False)
        except Exception as exc:  # noqa: BLE001
            logger.error("Hugging Face inference call failed: %s", exc)
            raise


def _rapidapi_key() -> Optional[str]:
    """Read the normal env var or the legacy RapidAPI Python snippet in .env."""
    configured = os.environ.get("RAPIDAPI_KEY") or os.environ.get("RAPID_API_KEY")
    if configured:
        return configured.strip().strip('"\'')
    env_path = Path(__file__).resolve().parent.parent / ".env"
    try:
        content = env_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = re.search(
        r"(?i)[\"']x-rapidapi-key[\"']\s*:\s*[\"']([^\"']+)[\"']",
        content,
    )
    return match.group(1).strip() if match else None


class RapidAPIProvider(LLMProvider):
    """Client for the OPEN AI API published through RapidAPI."""

    def __init__(self, api_key: Optional[str] = None, host: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or _rapidapi_key()
        self.host = host or os.environ.get("RAPIDAPI_HOST", "open-ai21.p.rapidapi.com")
        self.base_url = base_url or os.environ.get(
            "RAPIDAPI_URL", f"https://{self.host}/conversationgpt35"
        )
        self.model_name = os.environ.get("RAPIDAPI_MODEL", "GPT-3.5 via RapidAPI")
        if not self.api_key:
            raise RuntimeError("RAPIDAPI_KEY is not set in .env.")

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        payload = json.dumps({
            "messages": [{"role": "system", "content": system_prompt}] + messages,
            "web_access": False,
            "system_prompt": system_prompt,
            "temperature": 0.2,
            "top_k": 5,
            "top_p": 0.9,
            "max_tokens": 900,
        }).encode("utf-8")
        request = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": self.host,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                result = json.loads(response.read().decode("utf-8"))
            text = result.get("result") or result.get("text")
            if not text:
                raise ValueError(f"RapidAPI response contained no answer: {str(result)[:300]}")
            return LLMResponse(text=str(text), is_demo=False)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"RapidAPI call failed (HTTP {exc.code}): {detail}") from exc
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            raise RuntimeError(f"RapidAPI call failed: {exc}") from exc


class DemoProvider(LLMProvider):
    """
    Deterministic, rule-based stand-in for an LLM. Used when DEMO_MODE=true
    or no API token is configured. It does NOT invent dataset numbers --
    it only ever echoes tool results that Python already computed, and its
    control flow (which tool to call next) is a fixed, documented plan
    per agent role, applied to the REAL data at run time.
    """

    def complete(self, system_prompt: str, messages: list[dict]) -> LLMResponse:
        # The DemoProvider is not used directly by agents; agents check
        # is_demo mode and run their deterministic plan instead of calling
        # this. Kept here to satisfy the LLMProvider interface uniformly.
        return LLMResponse(text=json.dumps({"action": "final_answer", "content": "(demo mode)"}), is_demo=True)


def get_provider() -> tuple[LLMProvider, bool]:
    """
    Returns (provider, is_demo_mode).
    Reads DEMO_MODE and provider settings from the environment (loaded via dotenv
    in app.py / conftest). Falls back to demo mode automatically -- and
    loudly logs why -- if no token is present, so the app never crashes
    just because a key wasn't configured.
    """
    demo_flag = os.environ.get("DEMO_MODE", "").strip().lower() in {"1", "true", "yes"}
    if demo_flag:
        logger.info("DEMO_MODE=true -> using DemoProvider (no LLM calls).")
        return DemoProvider(), True

    try:
        configured_provider = os.environ.get("LLM_PROVIDER", "").strip().lower()
        if configured_provider:
            provider_name = configured_provider
        elif _rapidapi_key():
            provider_name = "rapidapi"
        elif os.environ.get("HF_TOKEN") or os.environ.get("HF_API_TOKEN"):
            provider_name = "huggingface"
        else:
            provider_name = "grok"

        if provider_name in {"huggingface", "hugging_face", "hf"}:
            return HuggingFaceProvider(), False
        if provider_name in {"rapidapi", "rapid_api", "rapid"}:
            return RapidAPIProvider(), False
        if provider_name in {"grok", "xai"}:
            return GrokProvider(), False
        raise RuntimeError(
            f"Unsupported LLM_PROVIDER={provider_name!r}; use 'rapidapi', 'huggingface', 'grok', or 'xai'."
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialize LLM provider (%s) -> falling back to Demo Mode.", exc)
        return DemoProvider(), True


def extract_json_object(text: str) -> Optional[dict]:
    """
    Best-effort extraction of a single JSON object from an LLM response,
    tolerating markdown code fences or leading/trailing prose that some
    open models add despite instructions.
    """
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    else:
        first = text.find("{")
        last = text.rfind("}")
        if first != -1 and last != -1 and last > first:
            text = text[first:last + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Could not parse JSON from LLM response: %r", text[:300])
        return None
