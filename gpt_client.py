# gpt_client.py
import os
import openai
import requests
import logging
import tiktoken
from config import USE_LOCAL_LLM, LOCAL_LLM_API_URL

logger = logging.getLogger(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")


def count_tokens(prompt: str, model: str = "gpt-4") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))


def call_local_webui(prompt: str, max_tokens: int = 1000) -> str:
    payload = {"prompt": prompt, "max_tokens": max_tokens}
    response = requests.post(LOCAL_LLM_API_URL, json=payload)
    response.raise_for_status()
    return response.json().get("choices", [{}])[0].get("text", "").strip()


def ask_gpt(prompt: str, model: str = "gpt-4") -> str:
    token_count = count_tokens(prompt, model)
    if USE_LOCAL_LLM:
        try:
            logger.debug(f"Calling local LLM at {LOCAL_LLM_API_URL}")
            response = call_local_webui(prompt)
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            return None
    else:
        try:
            response = openai.ChatCompletion.create(
                model=model, messages=[{"role": "user", "content": prompt}]
            )
            response = response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return None
    logger.info(f"Used {token_count} tokens")
    return response
