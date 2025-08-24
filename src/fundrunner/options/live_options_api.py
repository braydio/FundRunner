"""Helpers for retrieving live options data via Alpaca."""

import logging

import requests

from fundrunner.utils.config import API_KEY, API_SECRET, BASE_URL, DATA_URL

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
    url = f"{DATA_URL}/v2/options/contracts"
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
    url = f"{DATA_URL}/v2/stocks/{symbol}/trades/latest"
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


def get_metrics_for_multi_analysis(symbol, expiry, strike, option_type="call"):
    chain_data = get_live_options_chain(symbol, expiration=expiry)
    if not chain_data or "results" not in chain_data or not chain_data["results"]:
        print(f"No chain data found for {symbol} {expiry}")
        return {}

    # Find the contract matching the strike and type
    contracts = [
        c
        for c in chain_data["results"]
        if float(c["strike_price"]) == float(strike)
        and c["option_type"].lower() == option_type.lower()
    ]
    if not contracts:
        print(f"No matching contract for {symbol} {expiry} {strike} {option_type}")
        return {}

    opt = contracts[0]

    # Collect other stats for ALL contracts to compute things like put_call_ratio
    puts = [c for c in chain_data["results"] if c["option_type"] == "put"]
    calls = [c for c in chain_data["results"] if c["option_type"] == "call"]
    put_volume = sum(float(c.get("volume") or 0) for c in puts)
    call_volume = sum(float(c.get("volume") or 0) for c in calls)
    put_call_ratio = (put_volume / call_volume) if call_volume else 0

    # Fill with real values if available; placeholder logic for advanced metrics
    metrics = {
        "open_interest": float(opt.get("open_interest") or 0),
        "volume": float(opt.get("volume") or 0),
        "put_call_ratio": put_call_ratio,
        "iv_rank": float(opt.get("implied_volatility") or 0),
        "iv_percentile": float(opt.get("implied_volatility") or 0),  # TODO: real logic
        "max_pain": None,  # Placeholder unless you want to compute from payouts
        "unusual_activity_score": None,  # TODO: add logic
        "skew": None,  # TODO: add logic
        "gamma_exposure": None,  # TODO: add logic
        "largest_trade_size": float(opt.get("open_interest") or 0),  # Or use volume
    }
    return metrics
