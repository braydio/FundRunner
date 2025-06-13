"""Simplified options evaluation using Alpaca market data."""

import math
import datetime
import logging
import requests  # used for live data if needed
import pandas as pd
from config import API_KEY, API_SECRET, BASE_URL
from live_options_api import (
    get_live_options_chain,
    get_latest_stock_price,
)

# Initialize logger for this module.
logger = logging.getLogger(__name__)


class AlpacaTicker:
    """Minimal ticker interface using Alpaca data."""

    def __init__(self, symbol: str):
        self.symbol = symbol

    @property
    def info(self):
        price = get_latest_stock_price(self.symbol)
        return {"regularMarketPrice": price} if price is not None else {}

    @property
    def options(self):
        data = get_live_options_chain(self.symbol)
        if not data:
            return []
        contracts = data.get("options", {}).get("option", [])
        expiries = {
            c.get("expiration_date") for c in contracts if c.get("expiration_date")
        }
        return sorted(expiries)

    def option_chain(self, expiry):
        data = get_live_options_chain(self.symbol, expiry)
        if not data:
            raise ValueError("No option chain data")
        contracts = data.get("options", {}).get("option", [])
        df = pd.DataFrame(contracts)
        if not df.empty:
            df = df.rename(
                columns={"last": "lastPrice", "implied_volatility": "impliedVolatility"}
            )
            greeks_cols = ["delta", "gamma", "theta", "vega", "rho"]
            for col in greeks_cols:
                if col not in df.columns and "greeks" in df.columns:
                    df[col] = df["greeks"].apply(
                        lambda g: g.get(col) if isinstance(g, dict) else None
                    )
        calls = df[df["option_type"].str.lower() == "call"]
        puts = df[df["option_type"].str.lower() == "put"]
        return type("Chain", (object,), {"calls": calls, "puts": puts})


def norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def black_scholes_greeks(S, K, T, r, sigma, option_type="call"):
    """
    Compute Black-Scholes option greeks for a European option.
    Returns a dictionary with delta, gamma, theta, vega, and rho.
    """
    if T <= 0 or sigma <= 0:
        return {"delta": None, "gamma": None, "theta": None, "vega": None, "rho": None}

    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    norm_pdf_d1 = (1.0 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1 * d1)
    gamma = norm_pdf_d1 / (S * sigma * math.sqrt(T))

    if option_type == "call":
        delta = norm_cdf(d1)
        theta = -(S * norm_pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(
            -r * T
        ) * norm_cdf(d2)
        rho = K * T * math.exp(-r * T) * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1
        theta = -(S * norm_pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(
            -r * T
        ) * norm_cdf(-d2)
        rho = -K * T * math.exp(-r * T) * norm_cdf(-d2)

    vega = S * math.sqrt(T) * norm_pdf_d1

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}


def evaluate_option_trade(trade_details):
    """
    Basic evaluation for a long option trade (call or put) using Alpaca data.
    Expects trade_details to include:
      - underlying, expiry, strike, option_type, position.
    Returns metrics similar to your current implementation.
    """
    underlying = trade_details.get("underlying")
    expiry_str = trade_details.get("expiry")
    strike = float(trade_details.get("strike"))
    option_type = trade_details.get("option_type").lower()
    position = trade_details.get("position").lower()

    ticker = AlpacaTicker(underlying)
    try:
        options = ticker.options
    except Exception as e:
        return {"error": f"Failed to retrieve options for {underlying}: {e}"}

    if expiry_str not in options:
        return {
            "error": f"Expiry {expiry_str} not available for {underlying}. Available expiries: {options}"
        }

    opt_chain = ticker.option_chain(expiry_str)
    chain = opt_chain.calls if option_type == "call" else opt_chain.puts
    option_data = chain[chain["strike"] == strike]
    if option_data.empty:
        return {"error": f"No option found for strike {strike} and type {option_type}"}

    option_info = option_data.iloc[0].to_dict()
    option_price = option_info.get("lastPrice")
    implied_vol = option_info.get("impliedVolatility")

    expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
    today = datetime.datetime.today()
    T = (expiry_date - today).days / 365.0
    if T <= 0:
        return {"error": "Option has expired."}

    S = ticker.info.get("regularMarketPrice")
    r = 0.01
    sigma = implied_vol if implied_vol else 0.2
    greeks = black_scholes_greeks(S, strike, T, r, sigma, option_type)

    if position == "long":
        risk_amount = option_price
    else:
        risk_amount = 2 * option_price  # simplistic placeholder

    if position == "long":
        probability_of_profit = (
            greeks.get("delta", 0)
            if option_type == "call"
            else 1 - greeks.get("delta", 0)
        )
    else:
        probability_of_profit = (
            1 - greeks.get("delta", 0)
            if option_type == "call"
            else greeks.get("delta", 0)
        )

    potential_move = 0.05 * S
    if option_type == "call":
        potential_profit = max(S + potential_move - strike, 0) - option_price
    else:
        potential_profit = max(strike - (S - potential_move), 0) - option_price
    profit_ratio = potential_profit / risk_amount if risk_amount != 0 else None

    return {
        "option_price": option_price,
        "implied_volatility": implied_vol,
        "time_to_expiry_years": T,
        "greeks": greeks,
        "risk_amount": risk_amount,
        "probability_of_profit": probability_of_profit,
        "profit_ratio": profit_ratio,
        "underlying_price": S,
    }


def evaluate_credit_spread(trade_details, live=False):
    """
    Evaluate a credit spread trade (e.g., bull put spread or bear call spread).

    Expected trade_details should include:
      - underlying: str, ticker symbol.
      - expiry: str, expiration date 'YYYY-MM-DD'.
      - strike_short: float, strike price of the short (sold) option.
      - strike_long: float, strike price of the long (bought) option.
      - option_type: 'put' for bull put spread or 'call' for bear call spread.
      - strategy: should be "credit_spread".

    If ``live`` is True, fetch option prices from Alpaca. Otherwise, use the
    static data returned from the contracts endpoint.

    Returns a dictionary with:
      - credit_received: net premium received.
      - max_profit: equal to credit_received.
      - max_loss: difference between strikes minus credit_received.
      - risk_reward_ratio: credit_received divided by max_loss.
      - probability_of_profit: approximated via the short option's delta.
    """
    underlying = trade_details.get("underlying")
    expiry_str = trade_details.get("expiry")
    strike_short = float(trade_details.get("strike_short"))
    strike_long = float(trade_details.get("strike_long"))
    option_type = trade_details.get("option_type").lower()

    # Use live data if requested; otherwise fall back to contract data.
    if live:
        live_data = get_live_options_chain(underlying, expiry_str)
        if not live_data:
            logger.error("Live data not available")
            live = False

    if not live:
        ticker = AlpacaTicker(underlying)
        try:
            opt_chain = ticker.option_chain(expiry_str)
        except Exception as e:
            return {"error": f"Failed to fetch options chain: {e}"}
        chain = opt_chain.calls if option_type == "call" else opt_chain.puts
        # For credit spreads, assume strike_short < strike_long for bull put and vice versa for bear call.
        short_option_data = chain[chain["strike"] == strike_short]
        long_option_data = chain[chain["strike"] == strike_long]
        if short_option_data.empty or long_option_data.empty:
            return {
                "error": "Could not find option prices for one or both legs of the spread."
            }
        short_price = short_option_data.iloc[0]["lastPrice"]
        long_price = long_option_data.iloc[0]["lastPrice"]
    else:
        # Live data using Tradier – adjust keys as per the Tradier API response.
        live_options = get_live_options_chain(underlying, expiry_str)
        try:
            options = live_options["options"]["option"]
            # Filter for each leg by strike
            short_options = [
                o
                for o in options
                if float(o["strike"]) == strike_short
                and o["option_type"].lower() == option_type
            ]
            long_options = [
                o
                for o in options
                if float(o["strike"]) == strike_long
                and o["option_type"].lower() == option_type
            ]
            if not short_options or not long_options:
                return {"error": "Live data: could not find both legs."}
            short_price = float(short_options[0]["last"])
            long_price = float(long_options[0]["last"])
        except Exception as e:
            return {"error": f"Error parsing live options data: {e}"}

    credit_received = short_price - long_price
    max_profit = credit_received
    spread_width = abs(strike_long - strike_short)
    max_loss = spread_width - credit_received if spread_width > credit_received else 0
    risk_reward_ratio = credit_received / max_loss if max_loss else None

    # Approximate probability of profit using the short option's delta.
    ticker = AlpacaTicker(underlying)
    try:
        opt_chain = ticker.option_chain(expiry_str)
        chain = opt_chain.calls if option_type == "call" else opt_chain.puts
        short_option_data = chain[chain["strike"] == strike_short]
        if not short_option_data.empty:
            delta = short_option_data.iloc[0].get("delta", 0)
        else:
            delta = 0.5  # default approximation
    except Exception:
        delta = 0.5
    probability_of_profit = delta  # simplistic approximation

    return {
        "credit_received": credit_received,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "probability_of_profit": probability_of_profit,
    }


def evaluate_option_strategy(trade_details, live=False):
    """
    Evaluate an option trade based on the specified strategy.
    If trade_details contains a key "strategy", use that to select the evaluation method.

    Supported strategies:
      - "long" (default): Uses evaluate_option_trade.
      - "credit_spread": Uses evaluate_credit_spread.
      - (Other strategies like spreads, iron condors, buy-write, etc., can be added.)

    Returns a dictionary with evaluation metrics.
    """
    strategy = trade_details.get("strategy", "long").lower()
    if strategy == "credit_spread":
        return evaluate_credit_spread(trade_details, live=live)
    else:
        return evaluate_option_trade(trade_details)
