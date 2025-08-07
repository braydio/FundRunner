"""Client utilities for querying GPT models.

This module wraps OpenAI's Chat API as well as an optional locally hosted
LLM endpoint. It also exposes a :func:`count_tokens` helper using ``tiktoken``
so callers can track token usage.
"""

import os
from openai import OpenAI
import requests
import logging
import tiktoken
from fundrunner.utils.config import USE_LOCAL_LLM, LOCAL_LLM_API_URL

logger = logging.getLogger(__name__)
api_key = os.getenv("OPENAI_API_KEY")
openai_client = OpenAI(api_key=api_key) if api_key else None


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


def ask_gpt(prompt: str, model: str = "gpt-4") -> str:
    """Send ``prompt`` to GPT and return the text response."""
    token_count = count_tokens(prompt, model)
    if USE_LOCAL_LLM:
        try:
            logger.debug(f"Calling local LLM at {LOCAL_LLM_API_URL}")
            response = call_local_webui(prompt)
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            return None
    else:
        client = openai_client
        if client is None:
            key = os.getenv("OPENAI_API_KEY")
            if key:
                client = OpenAI(api_key=key)
            else:
                logger.error("OPENAI_API_KEY not configured")
                return None
        try:
            response = client.chat.completions.create(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            response = response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return None
    logger.info(f"Used {token_count} tokens")
    return response
