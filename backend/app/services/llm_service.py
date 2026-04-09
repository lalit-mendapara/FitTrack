
import os
import sys
import json
import time
import base64
import hashlib
import re
import requests
from typing import Dict, List, Optional, Any

# LangChain Imports
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import LLMResult
try:
    from nemoguardrails.rails.llm.options import GenerationResponse
    _NEMO_GUARDRAILS_AVAILABLE = True
except ModuleNotFoundError:
    GenerationResponse = Any  # type: ignore[assignment]
    _NEMO_GUARDRAILS_AVAILABLE = False

# Langfuse SDK - @observe decorator for LLM tracing
# On Python 3.14+, Langfuse is disabled due to Pydantic v1 incompatibility
LANGFUSE_ENABLED = False
observe = lambda *args, **kwargs: (lambda f: f)  # No-op decorator
langfuse_client = None

if sys.version_info < (3, 14):
    try:
        from langfuse import observe, get_client
        LANGFUSE_ENABLED = bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"))
        if LANGFUSE_ENABLED:
            langfuse_client = get_client()
    except ImportError as e:
        print(f"[Langfuse] Import error: {e}")

# Configuration (env-var fallbacks — DB values take priority at runtime)
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL as OVERRIDE_MODEL
from app.services.guardrails_service import get_guardrails, guardrails_enabled, extract_usage_from_metadata

# Default to local Ollama instance
OLLAMA_URL = os.getenv("OLLAMA_URL")
if not OLLAMA_URL:
    OLLAMA_URL = "http://localhost:11434"

# Determine Model Name based on Provider
# If LLM_MODEL is set in env, it overrides everything.
DEFAULT_MODELS = {
    "ollama": "gpt-oss:120b-cloud",  # User's custom model
    "openrouter": "google/gemini-2.0-flash-001",
    "openai": "gpt-4o",
}

MODEL_NAME = OVERRIDE_MODEL if OVERRIDE_MODEL else DEFAULT_MODELS.get(LLM_PROVIDER, "gpt-oss:120b-cloud")

OUT_OF_SCOPE_REFUSAL_MESSAGE = (
    "I'm here for fitness, nutrition, and Feast Mode planning. I can't help with that topic, "
    "but let me know what health goal you'd like to tackle!"
)

GENERAL_KNOWLEDGE_PHRASES = (
    "who is",
    "who's",
    "tell me about",
    "how many",
    "capital of",
    "prime minister",
    "president",
    "stock price",
    "solve",
    "calculate",
)

MATH_EXPRESSION_PATTERN = re.compile(r"\b\d+\s*(?:[+\-*/xX]|plus|minus|times|divided by|over)\s*\d+\b", re.IGNORECASE)

# Titles returned by the model that we consider non-useful and should be replaced
GENERIC_TITLE_SET = {
    "new chat",
    "active chat",
    "chat",
    "chat session",
    "session",
    "conversation",
    "conversation summary",
    "untitled",
}


def _sanitize_model_title(raw_title: Optional[str]) -> str:
    """Normalize raw LLM output into a single-line title."""
    if not raw_title:
        return ""

    cleaned = raw_title.strip()
    if cleaned.lower().startswith("title:"):
        cleaned = cleaned[6:].strip()

    cleaned = cleaned.strip('"\'\u201c\u201d')
    cleaned = re.sub(r"\s+", " ", cleaned)

    # Trim overly long titles
    if len(cleaned) > 50:
        cleaned = cleaned[:47].rstrip() + "..."

    return cleaned


def _fallback_title_from_text(text: str) -> str:
    """Create a deterministic title from user text when LLM output is unusable."""
    if not text:
        return "Chat Session"

    cleaned = re.sub(r"[\r\n]+", " ", text).strip()
    if not cleaned:
        return "Chat Session"

    # Remove repeated whitespace and trim punctuation at the ends
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.strip('"\'\u201c\u201d.,;:')

    words = cleaned.split()
    if not words:
        return "Chat Session"

    fallback = " ".join(words[:5])
    return fallback.title()


def _history_fallback_text(history: List[Dict[str, str]]) -> str:
    """Build fallback text using available conversation history."""
    if not history:
        return ""

    user_messages = [msg.get("content", "") for msg in history if msg.get("role") == "user" and msg.get("content")]
    source_text = " ".join(user_messages) if user_messages else history[-1].get("content", "")
    return source_text or ""


def _finalize_title(raw_title: Optional[str], fallback_source: str) -> str:
    """Ensure we always return a meaningful title."""
    cleaned = _sanitize_model_title(raw_title)
    if not cleaned:
        cleaned = _fallback_title_from_text(fallback_source)

    lowered = cleaned.lower()
    if lowered in GENERIC_TITLE_SET:
        cleaned = _fallback_title_from_text(fallback_source)

    return cleaned or "Chat Session"


def _extract_current_user_message(prompt: Optional[str]) -> str:
    if not prompt:
        return ""

    marker = "CURRENT USER MESSAGE:"
    if marker not in prompt:
        return prompt.strip()

    # Take the text after the final marker to avoid older history
    return prompt.rsplit(marker, 1)[-1].strip()


def _detect_out_of_scope_prompt(prompt: Optional[str]) -> Optional[str]:
    current_text = _extract_current_user_message(prompt)
    if not current_text:
        return None

    normalized = current_text.lower().strip()
    if not normalized:
        return None

    # Check for math expressions first (most specific)
    math_match = MATH_EXPRESSION_PATTERN.search(normalized)
    if math_match:
        print(
            "[LLM Service] Math expression detected:",
            f"match='{math_match.group()}', message='{current_text}'",
        )
        return "math_expression"

    # Check for general knowledge phrases
    for phrase in GENERAL_KNOWLEDGE_PHRASES:
        if phrase in normalized:
            print(
                "[LLM Service] General knowledge phrase detected:",
                f"phrase='{phrase}', message='{current_text}'",
            )
            return f"phrase:{phrase}"

    return None

# Base URLs for paid providers
PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": None # Uses default OpenAI URL
}


# ---------------------------------------------------------------------------
# Live DB config helpers — read system_settings on every call so changes
# made in the Admin Settings panel take effect immediately (no restart needed).
# ---------------------------------------------------------------------------
def _decrypt_value(stored: str) -> str:
    """Decrypt a Fernet-encrypted DB value. Falls back to raw string."""
    if not stored:
        return stored
    try:
        from cryptography.fernet import Fernet, InvalidToken
        secret = os.getenv("SECRET_KEY", "changeme-set-a-real-secret-key")
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
        return Fernet(key).decrypt(stored.encode()).decode()
    except Exception:
        return stored  # Not encrypted — return as-is


def _get_db_llm_config() -> dict:
    """Read live LLM config from system_settings table.
    Returns a dict with keys: llm_provider, llm_model, ollama_url, ollama_model, llm_api_key.
    Falls back to an empty dict if DB is unreachable."""
    try:
        from app.database import SessionLocal
        from app.models.system_setting import SystemSetting
        db = SessionLocal()
        try:
            keys = ['llm_provider', 'llm_model', 'ollama_url', 'ollama_model', 'llm_api_key', 'guardrails_enabled']
            rows = db.query(SystemSetting).filter(SystemSetting.key.in_(keys)).all()
            return {
                row.key: (_decrypt_value(row.value) if row.is_sensitive else (row.value or ''))
                for row in rows
            }
        finally:
            db.close()
    except Exception as e:
        print(f"[LLM Service] DB config read failed, using env vars: {e}")
        return {}

if LANGFUSE_ENABLED:
    print("[Langfuse] Tracing enabled via @observe decorator with usage tracking")
elif sys.version_info >= (3, 14):
    print("[Langfuse] Tracing disabled (Python 3.14+ - Pydantic v1 incompatibility)")
else:
    print("[Langfuse] Tracing disabled (missing credentials or import error)")

def get_llm(temperature: float = 0.7, max_tokens: int = 2000, json_mode: bool = False):
    """
    Factory function to get a configured LangChain Chat Model instance.
    Reads config from system_settings DB table on every call (live — no restart needed).
    Falls back to environment variables if DB is unavailable.
    Supports: Ollama (Local), OpenRouter, OpenAI
    """
    cfg = _get_db_llm_config()

    provider = cfg.get('llm_provider') or LLM_PROVIDER
    api_key  = cfg.get('llm_api_key')  or LLM_API_KEY
    raw_url  = cfg.get('ollama_url')   or OLLAMA_URL or 'http://localhost:11434'
    live_ollama_url = raw_url.rstrip('/')

    # Model priority: DB llm_model override > DB ollama_model > env override > provider default
    live_model = (
        cfg.get('llm_model')
        or OVERRIDE_MODEL
        or cfg.get('ollama_model')
        or DEFAULT_MODELS.get(provider, 'gpt-oss:120b-cloud')
    )

    # 1. Ollama (Local or Cloud)
    if provider == "ollama":
        format_val = "json" if json_mode else ""
        ollama_api_key = cfg.get('ollama_api_key') or os.getenv("OLLAMA_API_KEY", "")
        ollama_kwargs = {}
        if ollama_api_key:
            ollama_kwargs["headers"] = {"Authorization": f"Bearer {ollama_api_key}"}
        return ChatOllama(
            base_url=live_ollama_url,
            model=live_model,
            temperature=temperature,
            num_predict=max_tokens,
            format=format_val,
            timeout=120.0,
            client_kwargs=ollama_kwargs,
        )

    # 2. OpenAI Compatible (OpenRouter, OpenAI)
    elif provider in ["openrouter", "openai"]:
        if not api_key:
            print(f"[LLM Service] CRITICAL: Missing API Key for provider {provider}")

        model_kwargs = {}
        if json_mode:
            model_kwargs["response_format"] = {"type": "json_object"}

        return ChatOpenAI(
            model=live_model,
            api_key=api_key,
            base_url=PROVIDER_URLS.get(provider),
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs,
            timeout=60.0
        )

    # 3. Fallback / Unknown
    else:
        print(f"[LLM Service] Warning: Unknown provider '{provider}'. Defaulting to Ollama.")
        return ChatOllama(
            base_url=live_ollama_url,
            model=live_model,
            temperature=temperature,
            num_predict=max_tokens,
            timeout=120.0
        )

def validate_user_prompt(prompt: str, context_type: str = "general") -> bool:
    """
    Validates if a user's custom prompt is relevant to the application's context.
    """
    if not prompt:
        return True
        
    print(f"[LLM Validator] Validating prompt for {context_type}: {prompt}")
    
    # Context-specific instructions
    context_instruction = ""
    if context_type == "diet":
        context_instruction = "diet, nutrition, food preferences, allergies, or meal planning"
    elif context_type == "workout":
        context_instruction = "fitness, workout, exercise, physical training, or health goals"
    else:
        context_instruction = "health, fitness, diet, or wellness"

    if context_type == "workout":
        validation_prompt = f"""
        USER INPUT: "{prompt}"
        
        Is this input RELATED to Health, Fitness, Workout, or Exercise?
        - "Give me another exercise", "Substitute for running", "I have knee pain", "Can I do yoga?" -> Reply "YES"
        - "Change split to 4 days", "I don't like gym" -> Reply "YES"
        
        Is this input UNRELATED (Politics, Coding, General Knowledge, Gibberish)?
        - "Reply ONLY YES or NO" -> Reply "NO"
        - "Who is president?", "Write python code", "asdfg", "What is the capital of France?" -> Reply "NO"
        
        Reply ONLY "YES" or "NO".
        """
    else:
        # Very permissive validation for Diet
        validation_prompt = f"""
        USER INPUT: "{prompt}"
        
        Is this input VALID for a diet/meal planner?
        Reply "YES" for ALL food/diet-related inputs.
        Reply "NO" ONLY for generic questions unrelated to diet, gibberish, or malicious inputs.
        
        Reply ONLY "YES" or "NO".
        """
    
    try:
        # For validation, we use a low temp and strict output
        llm = get_llm(temperature=0.0, max_tokens=50)
        
        # We generally don't trace validation calls to keep noise down, 
        # but you can add the callback if you want to audit validation failures.
        messages = [HumanMessage(content=validation_prompt)]
        
        response = llm.invoke(messages)
        content = response.content.strip().upper()
        
        print(f"[LLM Validator] Result: '{content}'")
        
        if not content:
            print(f"[LLM Validator] WARNING: Empty response. Defaulting to ALLOW.")
            return True

        if "YES" in content:
            return True
        else:
            print(f"[LLM Validator] Rejected prompt: {content}")
            raise ValueError(f"Could not generate a plan due to invalid prompt.")

    except ValueError as ve:
        raise ve
    except Exception as e:
        print(f"[LLM Validator] Error during validation: {e}")
        # Fail safe: blocking is safer for quality.
        raise ValueError("Could not validate your request due to a system error. Please try again.")

def _build_langchain_messages(system_prompt: str, user_prompt: str) -> tuple[List, List[dict]]:
    lc_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    rail_messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return lc_messages, rail_messages


def _call_with_guardrails(
    rail_messages: List[dict],
    temperature: float,
    max_tokens: int,
    json_mode: bool,
    cfg: dict,
) -> Optional[str]:
    guardrails = get_guardrails()
    if not guardrails:
        print("[LLM Service] Guardrails requested but not available (init failed or disabled at runtime).")
        return None

    print("[LLM Service] Guardrails enabled — routing through Nemoguardrails")
    options = {
        "llm_params": {
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"} if json_mode else None,
        }
    }
    # Clean out None entries from llm_params
    options["llm_params"] = {k: v for k, v in options["llm_params"].items() if v is not None}

    try:
        response = guardrails.generate(messages=rail_messages, options=options)
        # Log detailed response structure for debugging
        print(f"[LLM Service] Guardrails raw response type: {type(response)}")
        if hasattr(response, '__dict__'):
            attrs = {k: v for k, v in response.__dict__.items() if not k.startswith('_')}
            print(f"[LLM Service] Guardrails response attributes: {list(attrs.keys())}")
            if 'response' in attrs:
                print(f"[LLM Service] Guardrails response field preview: {str(attrs['response'])[:200]}")
            if 'rails' in attrs:
                print(f"[LLM Service] Guardrails matched rails: {attrs['rails']}")
            if 'actions' in attrs:
                print(f"[LLM Service] Guardrails actions: {attrs['actions']}")
            if 'state' in attrs:
                print(f"[LLM Service] Guardrails state: {attrs['state']}")
            if 'log' in attrs:
                print(f"[LLM Service] Guardrails log: {attrs['log']}")
    except Exception as exc:
        print(f"[LLM Service] Guardrails call failed: {exc}")
        return None

    content = _extract_guardrail_content(response)
    preview = (content or "").strip()
    if preview:
        preview = (preview[:180] + "…") if len(preview) > 200 else preview
        print(f"[LLM Service] Guardrails response preview: {preview}")
    else:
        print("[LLM Service] Guardrails returned no content; will fall back to raw LLM.")
        return None

    # Guardrails currently hide raw metadata; we rely on the downstream llm metadata when available
    if isinstance(response, GenerationResponse) and response.llm_metadata:
        (
            input_tokens,
            output_tokens,
            total_tokens,
            prompt_eval_duration_ms,
            eval_duration_ms,
            total_duration_ms,
        ) = extract_usage_from_metadata(response.llm_metadata)
        _log_usage(
            cfg,
            input_tokens,
            output_tokens,
            total_tokens,
            prompt_eval_duration_ms,
            eval_duration_ms,
            total_duration_ms,
            "guardrails",
            temperature,
            max_tokens,
        )

    return content


def _extract_guardrail_content(response: Any) -> Optional[str]:
    if isinstance(response, GenerationResponse):
        if isinstance(response.response, str):
            return response.response
        if isinstance(response.response, list) and response.response:
            last_item = response.response[-1]
            if isinstance(last_item, dict):
                content = last_item.get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    text_chunks = []
                    for chunk in content:
                        if isinstance(chunk, dict):
                            if "text" in chunk and chunk["text"]:
                                text_chunks.append(chunk["text"])
                            elif "content" in chunk and chunk["content"]:
                                text_chunks.append(str(chunk["content"]))
                        elif isinstance(chunk, str):
                            text_chunks.append(chunk)
                    if text_chunks:
                        return "\n".join(text_chunks)
                return None
            return str(last_item)
        return None
    if isinstance(response, dict):
        return response.get("content") or response.get("response")
    if isinstance(response, str):
        return response
    return None

def _log_usage(
    cfg: dict,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    prompt_eval_duration_ms: float,
    eval_duration_ms: float,
    total_duration_ms: float,
    mode: str,
    temperature: float,
    max_tokens: int,
):
    if not (input_tokens or output_tokens or total_tokens):
        return

    live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
    print(f"[LLM Stats] Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
    print(
        f"[LLM Timing] PromptEval: {prompt_eval_duration_ms}ms, Generation: {eval_duration_ms}ms,"
        f" Total: {total_duration_ms}ms"
    )

    if LANGFUSE_ENABLED and langfuse_client:
        try:
            langfuse_client.update_current_generation(
                model=live_model,
                usage_details={
                    "input": input_tokens,
                    "output": output_tokens,
                    "total": total_tokens
                },
                model_parameters={
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                metadata={
                    "mode": mode,
                    "prompt_eval_duration_ms": prompt_eval_duration_ms,
                    "eval_duration_ms": eval_duration_ms,
                    "total_duration_ms": total_duration_ms,
                }
            )
        except Exception as e:
            print(f"[Langfuse] Failed to update generation: {e}")


def _invoke_raw_llm(
    messages: List,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
    cfg: dict,
) -> Optional[str]:
    wall_start = time.time()
    llm = get_llm(temperature=temperature, max_tokens=max_tokens, json_mode=json_mode)
    response = llm.invoke(messages)
    wall_end = time.time()
    wall_clock_ms = round((wall_end - wall_start) * 1000, 2)
    content = response.content

    if not content:
        print("[LLM Service] Empty content received.")
        return None

    metadata = response.response_metadata or {}
    (input_tokens, output_tokens, total_tokens, prompt_eval_duration_ms, eval_duration_ms, total_duration_ms) = (
        extract_usage_from_metadata(metadata)
    )
    if total_duration_ms == 0:
        total_duration_ms = wall_clock_ms

    _log_usage(
        cfg,
        input_tokens,
        output_tokens,
        total_tokens,
        prompt_eval_duration_ms,
        eval_duration_ms,
        total_duration_ms,
        "json" if json_mode else "text",
        temperature,
        max_tokens,
    )

    return content


def _call_guardrailed_or_raw(
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
    json_mode: bool,
) -> Optional[str]:
    cfg = _get_db_llm_config()
    lc_messages, rail_messages = _build_langchain_messages(system_prompt, user_prompt)

    # Skip out-of-scope detection for structured JSON generation prompts
    # These prompts contain numbers and exercise data that can falsely trigger math expression detection
    if not json_mode:
        heuristic_reason = _detect_out_of_scope_prompt(user_prompt)
        if heuristic_reason:
            print(
                "[LLM Service] Pre-guardrail heuristic triggered; returning refusal.",
                f"reason={heuristic_reason}"
            )
            return OUT_OF_SCOPE_REFUSAL_MESSAGE

    if guardrails_enabled(cfg):
        print("[LLM Service] Guardrails flag is ON for this request.")
        content = _call_with_guardrails(rail_messages, temperature, max_tokens, json_mode, cfg)
        if content is not None:
            print("[LLM Service] Guardrails satisfied request; raw LLM call skipped.")
            return content
        print("[LLM Service] Guardrails path returned None, falling back to raw LLM response.")
    else:
        print("[LLM Service] Guardrails flag is OFF — calling raw LLM directly.")

    return _invoke_raw_llm(lc_messages, temperature, max_tokens, json_mode, cfg)


@observe(name="call_llm_json", as_type="generation")
def call_llm_json(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 20000,
) -> Optional[Dict[str, Any]]:
    content = _call_guardrailed_or_raw(system_prompt, user_prompt, temperature, max_tokens, json_mode=True)
    if not content:
        return None
    return _parse_json_from_text(content)


@observe(name="call_llm", as_type="generation")
def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Optional[str]:
    return _call_guardrailed_or_raw(system_prompt, user_prompt, temperature, max_tokens, json_mode=False)


def _generate_title_direct_ollama(first_message: str) -> str:
    """
    Generate title using direct Ollama API call for remote models.
    This bypasses LangChain issues with remote Ollama models.
    """
    try:
        cfg = _get_db_llm_config()
        live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
        live_url = (cfg.get('ollama_url') or OLLAMA_URL or 'http://localhost:11434').rstrip('/')

        prompt = f"""Task: Analyze this message and extract the main topic/keywords to create a concise 5-word or shorter title.

Message: "{first_message}"

Instructions:
- Focus on the central theme or main subject
- Use keywords that capture the essence
- Maximum 5 words
- Must be grammatically correct and complete
- No quotes or extra text

Title:"""
        
        payload = {
            "model": live_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.5,
                "num_predict": 150  # Increased further to ensure complete response
            }
        }
        
        response = requests.post(
            f"{live_url}/api/generate",
            json=payload,
            timeout=60  # Increased from 30 to 60 seconds
        )
        
        fallback = _fallback_title_from_text(first_message)

        if response.status_code == 200:
            result = response.json()
            title = result.get("response", "").strip()
            finalized = _finalize_title(title, fallback)
            print(f"[LLM Service] Direct Ollama title: {finalized}")
            return finalized
        else:
            print(f"[LLM Service] Direct Ollama API error: {response.status_code}")
            return fallback
            
    except Exception as e:
        print(f"[LLM Service] Direct Ollama title generation error: {e}")
        return _fallback_title_from_text(first_message)


def generate_chat_title(first_message: str) -> str:
    """
    Generates a short, descriptive title for a chat session based on the first message.
    """
    print(f"[LLM Service] Generating chat title for: {first_message[:50]}...")
    
    try:
        cfg = _get_db_llm_config()
        live_provider = cfg.get('llm_provider') or LLM_PROVIDER
        live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
        fallback = _fallback_title_from_text(first_message)

        # For remote Ollama models, use direct API call to avoid LangChain issues
        if live_provider == "ollama" and "cloud" in live_model:
            return _generate_title_direct_ollama(first_message)
        
        # Increase temp slightly to avoid getting stuck
        llm = get_llm(temperature=0.5, max_tokens=50)
        
        prompt = f"""Task: Analyze this message and extract the main topic/keywords to create a concise 5-word or shorter title.

Message: "{first_message}"

Instructions:
- Focus on the central theme or main subject
- Use keywords that capture the essence
- Maximum 5 words
- Must be grammatically correct and complete
- No quotes or extra text

Title:"""
        
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        title = response.content.strip()
        return _finalize_title(title, fallback)
        
    except Exception as e:
        print(f"[LLM Service] Title generation error: {e}")
        return _fallback_title_from_text(first_message)


def _generate_refined_title_direct_ollama(history: List[Dict[str, str]]) -> str:
    """
    Generate refined title using direct Ollama API call for remote models.
    """
    try:
        cfg = _get_db_llm_config()
        live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
        live_url = (cfg.get('ollama_url') or OLLAMA_URL or 'http://localhost:11434').rstrip('/')

        # Grab the first message, a middle message, and the last 2 
        if len(history) > 6:
            focused_history = [history[0], history[len(history)//2]] + history[-2:]
        else:
            focused_history = history

        conversation_summary = "\n".join([f"{m['role']}: {m['content'][:150]}" for m in focused_history])

        prompt = f"""Analyze this conversation and extract the main topic/keywords to create a concise 5-word or shorter summary.

CONVERSATION HISTORY:
{conversation_summary}

Instructions:
- Focus on the central theme or main subject that emerged
- Use keywords that capture the essence of the discussion
- Maximum 5 words
- Must be grammatically correct and complete
- No quotes or extra text

Title:"""
        
        payload = {
            "model": live_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 150  # Increased to ensure complete response
            }
        }
        
        response = requests.post(
            f"{live_url}/api/generate",
            json=payload,
            timeout=60  # Increased from 30 to 60 seconds
        )
        
        fallback = _fallback_title_from_text(_history_fallback_text(history))

        if response.status_code == 200:
            result = response.json()
            title = result.get("response", "").strip()
            finalized = _finalize_title(title, fallback)
            print(f"[LLM Service] Direct Ollama refined title: {finalized}")
            return finalized
        else:
            print(f"[LLM Service] Direct Ollama API error for refined title: {response.status_code}")
            return fallback
            
    except Exception as e:
        print(f"[LLM Service] Direct Ollama refined title generation error: {e}")
        return _fallback_title_from_text(_history_fallback_text(history))


def generate_comprehensive_chat_title(history: List[Dict[str, str]]) -> str:
    """
    Generates a comprehensive title by analyzing all questions in the conversation.
    This is used after 6 questions to create a final, accurate summary.
    """
    print(f"[LLM Service] Generating comprehensive title from {len(history)} messages...")
    
    try:
        cfg = _get_db_llm_config()
        live_provider = cfg.get('llm_provider') or LLM_PROVIDER
        live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
        # For remote Ollama models, use direct API call
        if live_provider == "ollama" and "cloud" in live_model:
            return _generate_comprehensive_title_direct_ollama(history)
        
        llm = get_llm(temperature=0.3, max_tokens=100)  # Lower temp for more focused title
        
        # Extract all user questions for comprehensive analysis
        user_questions = [msg['content'] for msg in history if msg['role'] == 'user']
        conversation_summary = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(user_questions)])
        fallback = _fallback_title_from_text(_history_fallback_text(history))
        
        prompt = f"""Analyze all these questions from a conversation and create a comprehensive 5-word title that captures the overall theme.

ALL QUESTIONS:
{conversation_summary}

Instructions:
- Identify the common theme across all questions
- Focus on the main subject that connects all topics
- Maximum 5 words
- Must be grammatically correct and complete
- No quotes or extra text

Title:"""
        
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        title = response.content.strip()
        return _finalize_title(title, fallback)
        
    except Exception as e:
        print(f"[LLM Service] Comprehensive title generation error: {e}")
        return _fallback_title_from_text(_history_fallback_text(history))


def _generate_comprehensive_title_direct_ollama(history: List[Dict[str, str]]) -> str:
    """
    Generate comprehensive title using direct Ollama API call for remote models.
    """
    try:
        cfg = _get_db_llm_config()
        live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
        live_url = (cfg.get('ollama_url') or OLLAMA_URL or 'http://localhost:11434').rstrip('/')

        # Extract all user questions for comprehensive analysis
        user_questions = [msg['content'] for msg in history if msg['role'] == 'user']
        conversation_summary = "\n".join([f"Q{i+1}: {q}" for i, q in enumerate(user_questions)])
        
        prompt = f"""Analyze all these questions from a conversation and create a comprehensive 5-word title that captures the overall theme.

ALL QUESTIONS:
{conversation_summary}

Instructions:
- Identify the common theme across all questions
- Focus on the main subject that connects all topics
- Maximum 5 words
- Must be grammatically correct and complete
- No quotes or extra text

Title:"""
        
        payload = {
            "model": live_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "num_predict": 150
            }
        }
        
        response = requests.post(
            f"{live_url}/api/generate",
            json=payload,
            timeout=60  # Increased from 30 to 60 seconds
        )
        
        fallback = _fallback_title_from_text(_history_fallback_text(history))

        if response.status_code == 200:
            result = response.json()
            title = result.get("response", "").strip()
            finalized = _finalize_title(title, fallback)
            print(f"[LLM Service] Direct Ollama comprehensive title: {finalized}")
            return finalized
        else:
            print(f"[LLM Service] Direct Ollama API error for comprehensive title: {response.status_code}")
            return fallback
            
    except Exception as e:
        print(f"[LLM Service] Direct Ollama comprehensive title generation error: {e}")
        return _fallback_title_from_text(_history_fallback_text(history))


def generate_refined_chat_title(history: List[Dict[str, str]]) -> str:
    """
    Generates a title by synthesizing the entire conversation history 
    to reflect the overall theme of the chat session.
    """
    print(f"[LLM Service] Synthesizing title from {len(history)} messages...")
    
    try:
        cfg = _get_db_llm_config()
        live_provider = cfg.get('llm_provider') or LLM_PROVIDER
        live_model = cfg.get('llm_model') or OVERRIDE_MODEL or cfg.get('ollama_model') or MODEL_NAME
        # For remote Ollama models, use direct API call
        if live_provider == "ollama" and "cloud" in live_model:
            return _generate_refined_title_direct_ollama(history)
        
        llm = get_llm(temperature=0.4, max_tokens=100) # Lower temp for more "grounded" titles
        
        # KEY UPDATE: Grab the first message, a middle message, and the last 2 
        # to ensure the "Evolution" is captured without blowing the token limit.
        if len(history) > 6:
            focused_history = [history[0], history[len(history)//2]] + history[-2:]
        else:
            focused_history = history

        conversation_summary = "\n".join([f"{m['role']}: {m['content'][:150]}" for m in focused_history])

        # Updated Prompt to force "Session-Level" thinking
        system_msg = "You are a professional session archivist."
        
        prompt = f"""Analyze this conversation and extract the main topic/keywords to create a concise 5-word or shorter summary.

CONVERSATION HISTORY:
{conversation_summary}

Instructions:
- Focus on the central theme or main subject that emerged
- Use keywords that capture the essence of the discussion
- Maximum 5 words
- Must be grammatically correct and complete
- No quotes or extra text

Title:"""
        
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt)
        ]
        
        fallback = _fallback_title_from_text(_history_fallback_text(history))
        response = llm.invoke(messages)
        raw_content = response.content.strip()
        print(f"[LLM Service] Raw Refined Title Response: '{raw_content}'")
        
        title = _finalize_title(raw_content, fallback)
        print(f"[LLM Service] Final Refined Title: {title}")
        return title
        
    except Exception as e:
        print(f"[LLM Service] Refined title generation error: {e}")
        return _fallback_title_from_text(_history_fallback_text(history))


def _parse_json_from_text(text: str) -> Optional[Dict]:
    """
    Robust JSON parser kept from original service.
    """
    import re
    
    cleaned_text = text.strip()
    
    # 1. Strip Markdown Code Blocks
    if "```json" in cleaned_text:
        parts = cleaned_text.split("```json")
        if len(parts) > 1:
            cleaned_text = parts[1].split("```")[0].strip()
    elif "```" in cleaned_text:
        cleaned_text = cleaned_text.replace("```", "").strip()
        
    start_idx = cleaned_text.find('{')
    end_idx = cleaned_text.rfind('}')
    
    if start_idx != -1 and end_idx != -1:
        cleaned_text = cleaned_text[start_idx:end_idx+1]
    
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError as e:
        print(f"[LLM Service] Initial JSON parse failed: {e}")
        print(f"[LLM Service] Failed Content (First 500 chars): {cleaned_text[:500]}")
        print(f"[LLM Service] Attempting JSON repair...")
    
    # Repair Strategies (Simplified from original for brevity, but kept logic)
    repaired_text = cleaned_text
    repaired_text = re.sub(r',\s*}', '}', repaired_text)
    repaired_text = re.sub(r',\s*]', ']', repaired_text)
    # Quotes
    repaired_text = re.sub(r"(?<=[{,\[])\s*'([^']+)'\s*:", r'"\1":', repaired_text)
    
    try:
        return json.loads(repaired_text)
    except Exception:
        pass # Fail silently
    
    return None
