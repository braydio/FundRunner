# v1.0.0
# llm_integration.py
import openai
import os
import json
import requests
import base64
import logging
import tiktoken
from dotenv import load_dotenv
from config import USE_LOCAL_LLM, LOCAL_LLM_API_URL, OPENAI_API_KEY

# Load environment variables
project_dir = os.path.dirname(__file__)
env_path = os.path.join(project_dir, ".env")
load_dotenv(env_path)

username = os.getenv("WEBUI_USR")
password = os.getenv("WEBUI_PSWD")
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key and not USE_LOCAL_LLM:
    raise ValueError("OPENAI_API_KEY environment variable not set or failed to load from .env.")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# (Assume logger_config.py will be used elsewhere to set up the common format.)

# Log file for LLM interactions
gpt_request_log_path = os.path.join(project_dir, "gpt_requests.log")

def count_tokens(prompt, model="gpt-4"):
    try:
        encoding = tiktoken.encoding_for_model(model)
    except Exception:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(prompt))

def log_gpt_request(prompt, api_response, token_count):
    with open(gpt_request_log_path, "a") as log_file:
        log_file.write(f"--- GPT Request ---\n")
        log_file.write(f"Token Count: {token_count}\n")
        log_file.write(f"Prompt Sent:\n{prompt}\n")
        log_file.write(f"--- GPT Response ---\n")
        log_file.write(f"{json.dumps(api_response, indent=2)}\n")
        log_file.write(f"--- End of GPT Interaction ---\n\n")

def get_token(username, password):
    return base64.b64encode(f"{username}:{password}".encode()).decode()

def call_local_webui(url, username, password, message):
    payload = {"prompt": message, "max_tokens": 1000}
    response = requests.post(url, json=payload)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code: {response.status_code}")
    return response.json()

def format_api_response(api_response):
    try:
        return api_response["choices"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Error formatting API response: {e}")
        return None

def ask_gpt(prompt):
    token_count = count_tokens(prompt, model="gpt-4")
    if USE_LOCAL_LLM:
        try:
            logger.debug(f"Sending request to local LLM at {LOCAL_LLM_API_URL}")
            api_response = call_local_webui(LOCAL_LLM_API_URL, username, password, prompt)
            formatted_response = format_api_response(api_response)
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logger.error(f"Error during local web UI call: {e}")
            return None
    else:
        if not openai.api_key:
            raise RuntimeError("OpenAI API key is not set. Please check .env and environment variables.")
        try:
            api_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            formatted_response = api_response.choices[0].message.content
            log_gpt_request(prompt, api_response, token_count)
            return formatted_response
        except Exception as e:
            logger.error(f"Error during GPT API call: {e}")
            return None

def get_account_overview(prompt):
    """Wrapper to obtain an account overview or trading advice."""
    return ask_gpt(prompt)

class LLMVetter:
    def __init__(self, vendor="local"):
        self.vendor = vendor.lower()

    def vet_trade_logic(self, trade_details: dict, prompt: str = None) -> bool:
        if prompt is None:
            prompt = f"Review the following trade logic details and state whether this is a sound trade: {trade_details}"
        try:
            response = ask_gpt(prompt)
            if response:
                response_lower = response.lower()
                logger.debug(f"LLM vetting response: {response_lower}")
                return "approved" in response_lower or "yes" in response_lower
            else:
                logger.error("No response received from LLM vetting.")
                return False
        except Exception as e:
            logger.error(f"Error during LLM vetting: {e}", exc_info=True)
            return False
