
import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca API credentials and endpoint (paper trading endpoint)
API_KEY = os.getenv("ALPACA_API_KEY", "your_api_key_here")
API_SECRET = os.getenv("ALPACA_API_SECRET", "your_api_secret_here")
BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
DATA_URL = os.getenv("ALPACA_DATA_URL", "https://data.alpaca.markets")

# OpenAI API key for ChatGPT integration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your_openai_api_key_here")

# Local LLM API endpoint (for your custom local model)
LOCAL_LLM_API_URL = os.getenv("LOCAL_LLM_API_URL", "http://localhost:5051/v1/chat")
LOCAL_LLM_API_KEY= os.getenv("LOCAL_LLM_API_KEY", "your_local_llm_key")
USE_LOCAL_LLM = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"

# Ticker filtering for trading bot (comma-separated strings)
DEFAULT_TICKERS = os.getenv("DEFAULT_TICKERS", "AAPL,MSFT,GOOGL,AMZN,FB")
EXCLUDE_TICKERS = os.getenv("EXCLUDE_TICKERS", "")

# Flag to indicate if default tickers should be fetched via GPT
DEFAULT_TICKERS_FROM_GPT = os.getenv("DEFAULT_TICKERS_FROM_GPT", "false").lower() == "true"

# SMTP configuration for notifications (if needed)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.example.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your_email@example.com")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_email_password")
NOTIFICATION_EMAIL = os.getenv("NOTIFICATION_EMAIL", "recipient@example.com")

# Simulation settings for paper account
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "False").lower() == "true"
SIMULATED_STARTING_CASH = float(os.getenv("SIMULATED_STARTING_CASH", "5000"))

# Micro account configuration
MICRO_MODE = os.getenv("MICRO_MODE", "false").lower() == "true"
MICRO_ACCOUNT_SIZE = float(os.getenv("MICRO_ACCOUNT_SIZE", "100"))

if MICRO_MODE:
    # Override starting cash when running in micro mode
    SIMULATED_STARTING_CASH = MICRO_ACCOUNT_SIZE

# GPT model configuration (centralized so all modules use the same model)
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")

# Tradier API key for live options data
TRADIER_API_KEY = os.getenv("TRADIER_API_KEY", "your_tradier_api_key_here")

# Trading daemon limits
MAX_TRADES_PER_HOUR = int(os.getenv("MAX_TRADES_PER_HOUR", "10"))
DAILY_STOP_LOSS = float(os.getenv("DAILY_STOP_LOSS", "1000"))
DAILY_PROFIT_TARGET = float(os.getenv("DAILY_PROFIT_TARGET", "1000"))

# Trading schedule (UTC times)
PRE_MARKET_START = os.getenv("PRE_MARKET_START", "08:00")
EXTENDED_HOURS_END = os.getenv("EXTENDED_HOURS_END", "20:00")
