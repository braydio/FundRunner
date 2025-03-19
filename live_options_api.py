
# live_options_api.py
import requests
import logging
from config import TRADIER_API_KEY

logger = logging.getLogger(__name__)

def get_live_options_chain(symbol, expiration):
    """
    Fetch live options chain data for a given symbol and expiration date using the Tradier API.
    
    Args:
        symbol (str): Underlying stock ticker.
        expiration (str): Expiration date in YYYY-MM-DD format.
        
    Returns:
        dict: JSON data containing the options chain or None on error.
    """
    url = "https://api.tradier.com/v1/markets/options/chains"
    headers = {
        "Authorization": f"Bearer {TRADIER_API_KEY}",
        "Accept": "application/json"
    }
    params = {
        "symbol": symbol,
        "expiration": expiration
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        logger.error("Error fetching live options chain data: %s", response.text)
        return None
    return response.json()
