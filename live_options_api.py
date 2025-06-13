# live_options_api.py
import requests
import logging
from config import BASE_URL, API_KEY, API_SECRET

logger = logging.getLogger(__name__)


def get_live_options_chain(symbol, expiration=None):
    """
    Fetch live options chain data for a given symbol and expiration date using the Alpaca Options API.

    Args:
        symbol (str): Underlying stock ticker.
        expiration (str): Expiration date in YYYY-MM-DD format.

    Returns:
        dict: JSON data containing the options chain or None on error.
    """
    url = f"{BASE_URL}/options/contracts"
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": API_SECRET,
        "Accept": "application/json",
    }
    params = {"symbol": symbol}
    if expiration:
        params["expiration_date"] = expiration
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        logger.error("Error fetching live options chain data: %s", response.text)
        return None
    return response.json()


def get_latest_stock_price(symbol):
    """Fetch the latest trade price for a stock using Alpaca's market data API."""
    url = f"{BASE_URL}/v2/stocks/{symbol}/trades/latest"
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": API_SECRET,
        "Accept": "application/json",
    }
    try:
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get("trade", {}).get("p")
    except Exception as e:
        logger.error("Error fetching latest price for %s: %s", symbol, e)
        return None
