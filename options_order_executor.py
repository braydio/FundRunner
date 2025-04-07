
# options_order_executor.py
import requests
import logging
from config import BASE_URL, API_KEY, API_SECRET
from live_options_api import get_live_options_chain

logger = logging.getLogger(__name__)

def get_contract_symbol(underlying, expiry, strike, option_type):
    """
    Retrieve the options contract symbol from the live options chain data based on underlying, expiry, strike, and option type.
    """
    data = get_live_options_chain(underlying, expiry)
    if not data:
        logger.error("No live options data available for %s on expiry %s", underlying, expiry)
        return None
    # Assume the response contains a structure like: {"options": {"option": [ { ... contract details ... }, ... ]}}
    try:
        contracts = data.get("options", {}).get("option", [])
        for contract in contracts:
            contract_strike = float(contract.get("strike", 0))
            contract_type = contract.get("option_type", "").lower()
            if abs(contract_strike - float(strike)) < 1e-3 and contract_type == option_type.lower():
                return contract.get("symbol")
    except Exception as e:
        logger.error("Error parsing contracts: %s", e)
    return None

def place_options_order(symbol, qty, side, order_type, time_in_force, limit_price=None):
    """
    Place an options order using Alpaca's Options API.
    Args:
       symbol (str): Options contract symbol.
       qty (int): Quantity of contracts.
       side (str): 'buy' or 'sell'.
       order_type (str): 'market' or 'limit'.
       time_in_force (str): e.g. 'gtc'.
       limit_price (float): Required if order_type is 'limit'.
    Returns:
       dict: The order response data or error.
    """
    url = f"{BASE_URL}/v2/orders"
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": API_SECRET,
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "symbol": symbol,
        "qty": qty,
        "side": side,
        "type": order_type,
        "time_in_force": time_in_force,
        "extended_hours": False
    }
    if order_type.lower() == "limit":
        if limit_price is None:
            raise ValueError("limit_price must be provided for limit orders")
        payload["limit_price"] = limit_price
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        logger.error("Options order failed: %s", response.text)
        return {"error": response.text}
    return response.json()
