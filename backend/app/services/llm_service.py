
import os
import sys
import json
from typing import Dict, List, Optional, Any

# LangChain Imports
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.outputs import LLMResult

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

# Configuration
from config import LLM_PROVIDER, LLM_API_KEY, LLM_MODEL as OVERRIDE_MODEL

# Default to local Ollama instance
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

# Determine Model Name based on Provider
# If LLM_MODEL is set in env, it overrides everything.
DEFAULT_MODELS = {
    "ollama": "gpt-oss:120b-cloud",
    "openrouter": "google/gemini-2.0-flash-001", # Cost effective default
    "openai": "gpt-4o",
}

MODEL_NAME = OVERRIDE_MODEL if OVERRIDE_MODEL else DEFAULT_MODELS.get(LLM_PROVIDER, "gpt-3.5-turbo")

# Base URLs for paid providers
PROVIDER_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": None # Uses default OpenAI URL
}

if LANGFUSE_ENABLED:
    print("[Langfuse] Tracing enabled via @observe decorator with usage tracking")
elif sys.version_info >= (3, 14):
    print("[Langfuse] Tracing disabled (Python 3.14+ - Pydantic v1 incompatibility)")
else:
    print("[Langfuse] Tracing disabled (missing credentials or import error)")

def get_llm(temperature: float = 0.7, max_tokens: int = 2000, json_mode: bool = False):
    """
    Factory function to get a configured LangChain Chat Model instance.
    Supports: Ollama (Local), OpenRouter, OpenAI
    """
    
    # 1. Ollama (Local)
    if LLM_PROVIDER == "ollama":
        format_val = "json" if json_mode else ""
        return ChatOllama(
            base_url=OLLAMA_URL,
            model=MODEL_NAME,
            temperature=temperature,
            num_predict=max_tokens,
            format=format_val,
            timeout=120.0
        )
    
    # 2. OpenAI Compatible (OpenRouter, OpenAI)
    elif LLM_PROVIDER in ["openrouter", "openai"]:
        if not LLM_API_KEY:
            print(f"[LLM Service] CRITICAL: Missing API Key for provider {LLM_PROVIDER}")
            # Fallback to Ollama or Raise Error? 
            # For now, let it fail so user knows config is wrong.
        
        model_kwargs = {}
        if json_mode:
            model_kwargs["response_format"] = {"type": "json_object"}
            
        return ChatOpenAI(
            model=MODEL_NAME,
            api_key=LLM_API_KEY,
            base_url=PROVIDER_URLS.get(LLM_PROVIDER),
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs,
            timeout=60.0
        )
    
    # 3. Fallback / Unknown
    else:
        print(f"[LLM Service] Warning: Unknown provider '{LLM_PROVIDER}'. Defaulting to Ollama.")
        return ChatOllama(
            base_url=OLLAMA_URL,
            model=MODEL_NAME,
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

@observe(name="call_llm_json", as_type="generation")
def call_llm_json(
    system_prompt: str, 
    user_prompt: str, 
    temperature: float = 0.1,
    max_tokens: int = 20000
) -> Optional[Dict[str, Any]]:
    """
    Executes a structured JSON request using LangChain and tracks it with Langfuse.
    """
    print(f"[LLM Service] Calling Model (JSON): {MODEL_NAME}")
    
    try:
        llm = get_llm(temperature=temperature, max_tokens=max_tokens, json_mode=True)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        content = response.content
        
        if not content:
            print("[LLM Service] Empty content received.")
            return None
            
        # Extract and log token usage
        if response.response_metadata:
            metadata = response.response_metadata
            
            # Ollama returns tokens directly in metadata, not in nested 'usage'
            # Keys: prompt_eval_count (input), eval_count (output)
            input_tokens = metadata.get('prompt_eval_count') or 0
            output_tokens = metadata.get('eval_count') or 0
            
            # Fallback to nested 'usage' dict (for OpenAI-compatible providers)
            if input_tokens == 0 and output_tokens == 0:
                usage = metadata.get('usage', {})
                input_tokens = usage.get('prompt_tokens') or usage.get('input_tokens') or 0
                output_tokens = usage.get('completion_tokens') or usage.get('output_tokens') or 0
            
            total_tokens = input_tokens + output_tokens
            
            print(f"[LLM Stats] Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
            # Send token usage to Langfuse with proper format for cost calculation
            if LANGFUSE_ENABLED and langfuse_client:
                try:
                    langfuse_client.update_current_generation(
                        model=MODEL_NAME,
                        usage_details={
                            "input": input_tokens,
                            "output": output_tokens,
                            "total": total_tokens
                        },
                        model_parameters={
                            "temperature": temperature, 
                            "max_tokens": max_tokens
                        },
                        metadata={"mode": "json"}
                    )
                except Exception as e:
                    print(f"[Langfuse] Failed to update generation: {e}")
        
        return _parse_json_from_text(content)
            
    except Exception as e:
        print(f"[LLM Service] JSON Call Error: {e}")
        import traceback
        traceback.print_exc()
        return None

@observe(name="call_llm", as_type="generation")
def call_llm(
    system_prompt: str, 
    user_prompt: str, 
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> Optional[str]:
    """
    Executes a standard chat request using LangChain and tracks it with Langfuse.
    """
    print(f"[LLM Service] Calling Model (Text): {MODEL_NAME}")
    
    try:
        llm = get_llm(temperature=temperature, max_tokens=max_tokens)
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        content = response.content
        
        if not content:
            print("[LLM Service] Empty content received.")
            return None
        
        # Extract and log token usage
        if response.response_metadata:
            metadata = response.response_metadata
            
            # Ollama returns tokens directly in metadata, not in nested 'usage'
            # Keys: prompt_eval_count (input), eval_count (output)
            input_tokens = metadata.get('prompt_eval_count') or 0
            output_tokens = metadata.get('eval_count') or 0
            
            # Fallback to nested 'usage' dict (for OpenAI-compatible providers)
            if input_tokens == 0 and output_tokens == 0:
                usage = metadata.get('usage', {})
                input_tokens = usage.get('prompt_tokens') or usage.get('input_tokens') or 0
                output_tokens = usage.get('completion_tokens') or usage.get('output_tokens') or 0
            
            total_tokens = input_tokens + output_tokens
            
            print(f"[LLM Stats] Input: {input_tokens}, Output: {output_tokens}, Total: {total_tokens}")
            
            # Send token usage to Langfuse with proper format for cost calculation
            if LANGFUSE_ENABLED and langfuse_client:
                try:
                    langfuse_client.update_current_generation(
                        model=MODEL_NAME,
                        usage_details={
                            "input": input_tokens,
                            "output": output_tokens,
                            "total": total_tokens
                        },
                        model_parameters={
                            "temperature": temperature, 
                            "max_tokens": max_tokens
                        },
                        metadata={"mode": "text"}
                    )
                except Exception as e:
                    print(f"[Langfuse] Failed to update generation: {e}")

        return content
            
    except Exception as e:
        print(f"[LLM Service] Text Call Error: {e}")
        return None


def generate_chat_title(first_message: str) -> str:
    """
    Generates a short, descriptive title for a chat session based on the first message.
    """
    print(f"[LLM Service] Generating chat title for: {first_message[:50]}...")
    
    try:
        # Increase temp slightly to avoid getting stuck
        llm = get_llm(temperature=0.5, max_tokens=50)
        
        prompt = f"""Task: Create a 3-5 word title for a chat starting with: "{first_message}"
Output ONLY the title. No quotes."""
        
        messages = [HumanMessage(content=prompt)]
        response = llm.invoke(messages)
        title = response.content.strip()
        
        # Clean up the title
        title = title.strip('"\'')
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title if title else "New Chat"
        
    except Exception as e:
        print(f"[LLM Service] Title generation error: {e}")
        return "New Chat"


def generate_refined_chat_title(history: List[Dict[str, str]]) -> str:
    """
    Generates a refined, highly accurate title based on conversation history.
    Used for the 2nd stage of title generation (Turn 3+).
    """
    print(f"[LLM Service] Generatng refined title from {len(history)} messages...")
    
    try:
        # Increase tokens to ensure we get a response
        llm = get_llm(temperature=0.6, max_tokens=150)
        
        # Format history for the prompt
        conversation_text = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "AI Coach"
            content = msg["content"][:200] 
            conversation_text += f"{role}: {content}\n"
            
        print(f"[LLM Service] Refined Title Input Context:\n{conversation_text}")

        # Structured Prompt with System Message
        system_msg = "You are a helpful AI assistant. Your task is to generate short, concise titles for conversations."
        
        prompt = f"""Read the conversation below and generate a short title (3-5 words) that summarizes the specific topic or goal.

Conversation:
{conversation_text}

Rules:
1. ONLY output the title.
2. NO quotes.
3. NO "Title:" prefix.
4. Examples: "Keto Meal Plan", "Leg Day Workout", "Yoga Advice"

Title:"""
        
        messages = [
            SystemMessage(content=system_msg),
            HumanMessage(content=prompt)
        ]
        
        response = llm.invoke(messages)
        raw_content = response.content.strip()
        print(f"[LLM Service] Raw Refined Title Response: '{raw_content}'")
        
        title = raw_content
        
        # Remove "Title:" prefix if present
        if title.lower().startswith("title:"):
            title = title[6:].strip()
            
        # Clean up quotes
        title = title.strip('"\'')
        
        # Final Fallback check
        if not title:
            print("[LLM Service] Empty title generated. Using fallback.")
            return "Active Chat" # Better than "New Chat" to show some state change
            
        if len(title) > 50:
            title = title[:47] + "..."
            
        print(f"[LLM Service] Final Refined Title: {title}")
        return title
        
    except Exception as e:
        print(f"[LLM Service] Refined title generation error: {e}")
        return "New Chat"


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
