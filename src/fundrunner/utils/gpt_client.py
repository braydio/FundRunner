"""Client utilities for querying GPT models.

This module wraps OpenAI's Chat API as well as an optional locally hosted
LLM endpoint. It provides structured JSON output, rate limiting, retry logic,
and robust error handling for reliable agentic workflows.
"""

import json
import re
import time
import logging
from typing import Dict, Any, Optional, Union
from functools import wraps
import os

from openai import OpenAI
import requests
import tiktoken

from fundrunner.utils.config import (
    USE_LOCAL_LLM, 
    LOCAL_LLM_API_URL, 
    LOCAL_LLM_API_KEY,
    GPT_MODEL,
    GPT_JSON_STRICT,
    LLM_REQUEST_TIMEOUT
)

logger = logging.getLogger(__name__)

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key) if api_key else None

# Rate limiting state
_last_request_time = 0
_min_request_interval = 1.0  # Minimum seconds between requests
_request_count = 0
_cost_tracking = {"total_tokens": 0, "estimated_cost_usd": 0.0}


def count_tokens(prompt: str, model: str = "gpt-4") -> int:
    """Return the number of tokens ``prompt`` would consume for ``model``."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))


def call_local_webui(prompt: str, max_tokens: int = 1000) -> str:
    """Query a locally hosted LLM WebUI endpoint and return the response."""
    payload = {"prompt": prompt, "max_tokens": max_tokens}
    response = requests.post(LOCAL_LLM_API_URL, json=payload)
    response.raise_for_status()
    return response.json().get("choices", [{}])[0].get("text", "").strip()


def _rate_limit() -> None:
    """Enforce rate limiting between requests."""
    global _last_request_time
    current_time = time.time()
    time_since_last = current_time - _last_request_time
    
    if time_since_last < _min_request_interval:
        sleep_time = _min_request_interval - time_since_last
        logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)
    
    _last_request_time = time.time()


def _retry_on_failure(max_retries: int = 3, backoff_factor: float = 2.0):
    """Decorator for exponential backoff retries."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor ** attempt
                        logger.warning(f"{func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}), retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"{func.__name__} failed after {max_retries + 1} attempts: {e}")
            
            raise last_exception
        return wrapper
    return decorator


def _estimate_cost(tokens: int, model: str) -> float:
    """Estimate cost in USD for token usage."""
    # Rough pricing as of late 2024 (adjust as needed)
    pricing = {
        "gpt-4": 0.06 / 1000,  # $0.06 per 1K tokens
        "gpt-4o-mini": 0.0015 / 1000,  # $0.0015 per 1K tokens
        "gpt-3.5-turbo": 0.002 / 1000,  # $0.002 per 1K tokens
    }
    
    # Default to gpt-4 pricing if model not found
    rate = pricing.get(model, pricing["gpt-4"])
    return tokens * rate


def _update_cost_tracking(tokens: int, model: str) -> None:
    """Update global cost tracking statistics."""
    global _cost_tracking
    cost = _estimate_cost(tokens, model)
    _cost_tracking["total_tokens"] += tokens
    _cost_tracking["estimated_cost_usd"] += cost


def get_cost_summary() -> Dict[str, Union[int, float]]:
    """Return current cost tracking summary."""
    return _cost_tracking.copy()


def reset_cost_tracking() -> None:
    """Reset cost tracking counters."""
    global _cost_tracking
    _cost_tracking = {"total_tokens": 0, "estimated_cost_usd": 0.0}


def _clean_json_response(text: str) -> str:
    """Clean LLM response to extract valid JSON.
    
    Handles common issues like markdown code fences, extra text, etc.
    """
    if not text:
        return ""
    
    # Remove markdown code fences
    text = re.sub(r'```json\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'```\s*$', '', text)
    text = text.strip()
    
    # Try to extract JSON object/array from response
    # Look for balanced braces/brackets
    def find_balanced_json(text, start_char, end_char):
        count = 0
        start_pos = text.find(start_char)
        if start_pos != -1:
            for i, char in enumerate(text[start_pos:], start_pos):
                if char == start_char:
                    count += 1
                elif char == end_char:
                    count -= 1
                    if count == 0:
                        return text[start_pos:i+1]
        return None
    
    # Check what appears first in the text
    obj_pos = text.find('{')
    array_pos = text.find('[')
    
    # If array comes before object (or no object), try array first
    if array_pos != -1 and (obj_pos == -1 or array_pos < obj_pos):
        array_match = find_balanced_json(text, '[', ']')
        if array_match:
            return array_match
        # Fallback to object if array parsing fails
        obj_match = find_balanced_json(text, '{', '}')
        if obj_match:
            return obj_match
    else:
        # Object comes first or no array found, try object first
        obj_match = find_balanced_json(text, '{', '}')
        if obj_match:
            return obj_match
        # Fallback to array if object parsing fails
        array_match = find_balanced_json(text, '[', ']')
        if array_match:
            return array_match
    
    # Fallback to regex patterns (less reliable but covers edge cases)
    json_patterns = [
        r'\{.*?\}',    # Non-greedy object match
        r'\[.*?\]',    # Non-greedy array match
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Return the largest match (most likely to be complete)
            return max(matches, key=len)
    
    return text


def _call_local_llm_enhanced(prompt: str, max_tokens: int = 1000, timeout: int = None) -> Optional[str]:
    """Enhanced local LLM call with headers and timeout."""
    headers = {"Content-Type": "application/json"}
    if LOCAL_LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LOCAL_LLM_API_KEY}"
    
    payload = {"prompt": prompt, "max_tokens": max_tokens}
    timeout = timeout or LLM_REQUEST_TIMEOUT
    
    response = requests.post(
        LOCAL_LLM_API_URL, 
        json=payload, 
        headers=headers,
        timeout=timeout
    )
    response.raise_for_status()
    
    result = response.json()
    return result.get("choices", [{}])[0].get("text", "").strip()


@_retry_on_failure(max_retries=3)
def ask_gpt_enhanced(prompt: str, model: str = None, timeout: int = None) -> Optional[str]:
    """Enhanced GPT query with rate limiting, retries, and cost tracking.
    
    Args:
        prompt: The prompt to send
        model: Model to use (defaults to config GPT_MODEL)
        timeout: Request timeout in seconds
        
    Returns:
        Response text or None on failure
    """
    global _request_count
    
    model = model or GPT_MODEL
    timeout = timeout or LLM_REQUEST_TIMEOUT
    token_count = count_tokens(prompt, model)
    
    _rate_limit()
    _request_count += 1
    
    logger.debug(f"LLM request #{_request_count}, {token_count} tokens, model: {model}")
    
    try:
        if USE_LOCAL_LLM:
            logger.debug(f"Calling local LLM at {LOCAL_LLM_API_URL}")
            response = _call_local_llm_enhanced(prompt, timeout=timeout)
        else:
            client = openai_client
            if not client:
                key = os.getenv("OPENAI_API_KEY")
                if not key:
                    logger.error("OPENAI_API_KEY not configured")
                    return None
                client = OpenAI(api_key=key)
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout
            )
            response = response.choices[0].message.content
        
        # Update cost tracking
        _update_cost_tracking(token_count, model)
        
        logger.info(f"LLM request completed: {token_count} tokens, estimated cost: ${_estimate_cost(token_count, model):.4f}")
        return response
        
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        raise


def ask_gpt_json(prompt: str, schema: Optional[Dict[str, Any]] = None, model: str = None) -> Optional[Dict[str, Any]]:
    """Send prompt to GPT and return parsed JSON response.
    
    Args:
        prompt: The prompt to send
        schema: Optional JSON schema for validation
        model: Model to use (defaults to config GPT_MODEL)
        
    Returns:
        Parsed JSON object or None on failure
    """
    # Enhance prompt to request JSON output
    if GPT_JSON_STRICT:
        json_instruction = "\n\nIMPORTANT: Respond ONLY with valid JSON. No additional text or explanation."
        if schema:
            json_instruction += f"\nUse this schema: {json.dumps(schema, indent=2)}"
        prompt = prompt + json_instruction
    
    response = ask_gpt_enhanced(prompt, model=model)
    if not response:
        logger.error("No response from LLM for JSON request")
        return None
    
    # Clean and parse JSON
    cleaned = _clean_json_response(response)
    
    # Try multiple parsing strategies
    for attempt, text in enumerate([cleaned, response], 1):
        try:
            result = json.loads(text)
            logger.debug(f"JSON parsed successfully on attempt {attempt}")
            
            # Basic schema validation if provided
            if schema and isinstance(result, dict):
                required_keys = schema.get("required", [])
                missing_keys = [key for key in required_keys if key not in result]
                if missing_keys:
                    logger.warning(f"JSON response missing required keys: {missing_keys}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.debug(f"JSON parse attempt {attempt} failed: {e}")
    
    # Final fallback: try to extract JSON from any part of the response
    try:
        # Look for JSON-like structures with regex
        json_match = re.search(r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except json.JSONDecodeError:
        pass
    
    logger.error(f"Failed to parse JSON from response: {response[:200]}...")
    return None


# Legacy function - maintained for backwards compatibility
def ask_gpt(prompt: str, model: str = "gpt-4") -> Optional[str]:
    """Send ``prompt`` to GPT and return the text response.
    
    This is the legacy function maintained for backwards compatibility.
    New code should use ask_gpt_enhanced().
    """
    return ask_gpt_enhanced(prompt, model=model)
