"""Options analysis utilities using Alpaca market data."""

import math
import datetime
import logging
import requests
import numpy as np
import pandas as pd
from config import API_KEY, API_SECRET, BASE_URL, DATA_URL
from live_options_api import (
    get_live_options_chain,
    get_latest_stock_price,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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
        logger.error("Invalid T or sigma for greeks: T=%s, sigma=%s", T, sigma)
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

    logger.debug(
        "Calculated greeks: delta=%.4f, gamma=%.4f, theta=%.4f, vega=%.4f, rho=%.4f",
        delta,
        gamma,
        theta,
        vega,
        rho,
    )
    return {
        "delta": delta,
        "gamma": gamma,
        "theta": theta,
        "vega": vega,
        "rho": rho,
        "d2": d2,
    }


def round_to_nearest(value, base=5):
    """Round a value to the nearest multiple of 'base'."""
    try:
        return round(value / base) * base
    except Exception as e:
        logger.error("Error rounding value %s: %s", value, e)
        return value


def adjust_probability(probability, intrinsic_ratio, factor=0.3):
    """
    Adjust the probability of profit by blending it with the intrinsic_ratio.
    The factor determines the weight given to the intrinsic_ratio.
    """
    try:
        adjusted = (probability + factor * intrinsic_ratio) / (1 + factor)
        return max(0, min(1, adjusted))
    except Exception as e:
        logger.error("Error adjusting probability: %s", e)
        return probability


def monte_carlo_prob_ITM(S, K, T, r, sigma, option_type, simulations=10000):
    """
    Estimate probability that option finishes ITM using Monte Carlo simulation.
    """
    Z = np.random.normal(0, 1, simulations)
    S_T = S * np.exp((r - 0.5 * sigma**2) * T + sigma * math.sqrt(T) * Z)
    if option_type == "call":
        return np.mean(S_T > K)
    else:
        return np.mean(S_T < K)


def get_nearest_expiry(ticker, requested_expiry):
    try:
        ticker_data = AlpacaTicker(ticker)
        options = ticker_data.options
        if not options:
            logger.error("No available options found for %s", ticker)
            return None
        if requested_expiry:
            req_date = datetime.datetime.strptime(requested_expiry, "%Y-%m-%d")
            available = sorted(
                options, key=lambda d: datetime.datetime.strptime(d, "%Y-%m-%d")
            )
            for exp in available:
                exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d")
                if exp_date >= req_date:
                    logger.debug(
                        "Nearest expiry for %s based on requested %s is %s",
                        ticker,
                        requested_expiry,
                        exp,
                    )
                    return exp
            return available[-1]
        else:
            if ticker.upper() != "SPY":
                today = datetime.datetime.today()
                min_date = today + datetime.timedelta(weeks=4)
                available = sorted(
                    options, key=lambda d: datetime.datetime.strptime(d, "%Y-%m-%d")
                )
                for exp in available:
                    exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d")
                    if exp_date.weekday() == 4 and exp_date >= min_date:
                        logger.debug(
                            "Auto-selected Friday expiry for %s: %s", ticker, exp
                        )
                        return exp
                for exp in available:
                    exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d")
                    if exp_date >= min_date:
                        logger.debug(
                            "Auto-selected expiry for %s meeting min_date: %s",
                            ticker,
                            exp,
                        )
                        return exp
                return available[-1]
            else:
                logger.debug("Ticker SPY: using first available expiry %s", options[0])
                return options[0]
    except Exception as e:
        logger.error("Error determining nearest expiry for %s: %s", ticker, e)
        return requested_expiry


def get_atm_strike(ticker, expiry, option_type):
    """
    Retrieve the ATM strike for a given ticker and expiry from Alpaca option data.
    For long puts (bearish view), we choose one strike above ATM.
    """
    try:
        t = AlpacaTicker(ticker)
        if option_type == "put":
            underlying_price = t.info.get("regularMarketPrice")
            base_strike = round_to_nearest(underlying_price, 5)
            if base_strike < underlying_price:
                base_strike += 5
            logger.debug(
                "For bearish long put on %s, selected strike=%s", ticker, base_strike
            )
            return base_strike
        else:
            chain = (
                t.option_chain(expiry).calls
                if option_type == "call"
                else t.option_chain(expiry).puts
            )
            underlying_price = t.info.get("regularMarketPrice")
            if underlying_price is None:
                logger.error("No underlying price available for %s", ticker)
                return None
            strikes = chain["strike"].tolist()
            atm_strike = min(strikes, key=lambda x: abs(x - underlying_price))
            rounded_atm = round_to_nearest(atm_strike, 5)
            logger.debug(
                "For %s (%s), underlying=%.2f, ATM strike=%s (rounded to %s)",
                ticker,
                option_type,
                underlying_price,
                atm_strike,
                rounded_atm,
            )
            return rounded_atm
    except Exception as e:
        logger.error("Error selecting ATM strike for %s: %s", ticker, e)
        return None


def get_option_leg_data(ticker, expiry, strike, option_type):
    """
    Retrieve option data for a single leg (price and greeks) using Alpaca data.
    If an exact match is not found, selects the closest strike available.
    """
    try:
        t = AlpacaTicker(ticker)
        chain = (
            t.option_chain(expiry).calls
            if option_type == "call"
            else t.option_chain(expiry).puts
        )
        leg_data = chain[chain["strike"] == strike]
        if leg_data.empty:
            strikes = chain["strike"].tolist()
            if not strikes:
                logger.error("No strikes available for %s", ticker)
                return {"error": f"No strikes available for {ticker}"}
            closest_strike = min(strikes, key=lambda x: abs(x - strike))
            logger.warning(
                "Exact strike %s not found for %s (%s); using closest strike %s",
                strike,
                ticker,
                option_type,
                closest_strike,
            )
            leg_data = chain[chain["strike"] == closest_strike]
        if leg_data.empty:
            logger.error(
                "No leg data found for %s at strike %s (%s)",
                ticker,
                strike,
                option_type,
            )
            return {"error": f"No data for strike {strike} and type {option_type}"}
        data = leg_data.iloc[0].to_dict()
        price = data.get("lastPrice")
        iv = data.get("impliedVolatility")
        underlying_price = t.info.get("regularMarketPrice")
        expiry_date = datetime.datetime.strptime(expiry, "%Y-%m-%d")
        T = (expiry_date - datetime.datetime.today()).days / 365.0
        r = 0.01
        greeks = black_scholes_greeks(
            underlying_price, data.get("strike"), T, r, iv if iv else 0.2, option_type
        )
        logger.debug(
            "Leg data for %s: strike=%s, price=%.2f, iv=%.6f, greeks=%s",
            ticker,
            data.get("strike"),
            price,
            iv if iv else 0,
            greeks,
        )
        return {
            "strike": data.get("strike"),
            "lastPrice": price,
            "impliedVolatility": iv,
            "greeks": greeks,
        }
    except Exception as e:
        logger.error("Error retrieving leg data for %s: %s", ticker, e)
        return {"error": str(e)}


def analyze_sentiment(ticker):
    """
    Analyze recent price activity of the ticker and return a default sentiment:
    'bullish' if current price is above 20-day MA, else 'bearish'.
    """
    try:
        t = AlpacaTicker(ticker)
        # Placeholder: Alpaca API does not provide historical daily data here.
        hist = pd.DataFrame()
        response = requests.get(
            f"{DATA_URL}/v2/stocks/{ticker}/bars",
            params={"timeframe": "1Day", "limit": 20},
            headers={
                "APCA-API-KEY-ID": API_KEY,
                "APCA-API-SECRET-KEY": API_SECRET,
            },
        )
        if response.status_code == 200:
            json_data = response.json()
            bars = json_data.get("bars", [])
            if bars:
                hist = pd.DataFrame(bars)
                hist.rename(columns={"c": "Close"}, inplace=True)
        if hist.empty:
            return "neutral"
        ma20 = hist["Close"].rolling(window=20).mean().iloc[-1]
        current_price = hist["Close"].iloc[-1]
        sentiment = "bullish" if current_price > ma20 else "bearish"
        logger.debug(
            "Sentiment for %s: current=%.2f, MA20=%.2f, sentiment=%s",
            ticker,
            current_price,
            ma20,
            sentiment,
        )
        return sentiment
    except Exception as e:
        logger.error("Error analyzing sentiment for %s: %s", ticker, e)
        return "neutral"


def format_primary_metric(evaluation: dict, primary_key: str, other_keys: list) -> dict:
    """
    Given an evaluation dictionary and a primary metric key (e.g., 'profit_ratio'),
    along with other metric keys (e.g., ['adjusted_probability', 'expected_return']),
    compute the total magnitude and then compute a score and weight for the primary metric.
    The function adds a new key '{primary_key}_formatted' with a string showing the value rounded
    to 2 decimals along with its Score and Weight.
    """
    try:
        primary_value = evaluation.get(primary_key)
        if primary_value is None:
            return evaluation
        primary_value = float(primary_value)
        metric_magnitudes = [abs(primary_value)]
        for key in other_keys:
            val = evaluation.get(key)
            if val is not None:
                metric_magnitudes.append(abs(float(val)))
        total = sum(metric_magnitudes)
        score = abs(primary_value)
        weight = (score / total) if total > 0 else 0
        evaluation[f"{primary_key}_formatted"] = (
            f"{primary_value:.2f} (Score: {score:.2f}, Weight: {weight:.2f})"
        )
    except Exception as e:
        logger.error("Error formatting primary metric: %s", e)
    return evaluation


def evaluate_option_trade(trade_details):
    """
    Evaluate a long option trade (call or put) using Alpaca data.
    Uses the analytic probability (N(d2) for calls, N(-d2) for puts) and a Monte Carlo estimate.
    Returns evaluation metrics including intrinsic/extrinsic values, adjusted probability, and expected return.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    option_type = trade_details.get("option_type", "call").lower()
    position = trade_details.get("position", "long").lower()

    if "strike" not in trade_details or not trade_details.get("strike"):
        strike = get_atm_strike(underlying, expiry_str, option_type)
    else:
        strike = float(trade_details.get("strike"))
    # For long puts under bearish view, choose one strike above ATM:
    if option_type == "put":
        t = AlpacaTicker(underlying)
        underlying_price = t.info.get("regularMarketPrice")
        atm = round_to_nearest(underlying_price, 5)
        if atm < underlying_price:
            atm += 5
        strike = atm

    logger.debug(
        "Evaluating long %s option for %s at strike %s and expiry %s",
        option_type,
        underlying,
        strike,
        expiry_str,
    )
    ticker = AlpacaTicker(underlying)
    try:
        options = ticker.options
        if expiry_str not in options:
            return {
                "error": f"Expiry {expiry_str} not available for {underlying}. Available expiries: {options}"
            }
    except Exception as e:
        return {"error": f"Failed to retrieve options for {underlying}: {e}"}
    try:
        opt_chain = ticker.option_chain(expiry_str)
    except Exception as e:
        return {
            "error": f"Failed to retrieve option chain for expiry {expiry_str}: {e}"
        }
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
    d2 = greeks.get("d2")
    if option_type == "call":
        analytic_prob = norm_cdf(d2)
    else:
        analytic_prob = norm_cdf(-d2)
    mc_prob = monte_carlo_prob_ITM(S, strike, T, r, sigma, option_type)
    base_prob = (analytic_prob + mc_prob) / 2

    risk_amount = option_price if position == "long" else 2 * option_price
    if option_type == "call":
        intrinsic_value = max(S - strike, 0)
    else:
        intrinsic_value = max(strike - S, 0)
    extrinsic_value = option_price - intrinsic_value
    intrinsic_ratio = intrinsic_value / option_price if option_price > 0 else 0
    adjusted_probability = adjust_probability(base_prob, intrinsic_ratio)

    potential_move = 0.05 * S
    if option_type == "call":
        potential_profit = max(S + potential_move - strike, 0) - option_price
    else:
        potential_profit = max(strike - (S - potential_move), 0) - option_price
    profit_ratio = potential_profit / risk_amount if risk_amount != 0 else None
    expected_return = (
        profit_ratio * adjusted_probability if profit_ratio is not None else None
    )

    logger.debug(
        "Long option evaluation for %s: type=%s, strike=%s, option_price=%.2f, intrinsic=%.2f, extrinsic=%.2f, intrinsic_ratio=%.2f, analytic_prob=%.2f, mc_prob=%.2f, base_prob=%.2f, adjusted_prob=%.2f, profit_ratio=%.2f, expected_return=%.2f",
        underlying,
        option_type,
        strike,
        option_price,
        intrinsic_value,
        extrinsic_value,
        intrinsic_ratio,
        analytic_prob,
        mc_prob,
        base_prob,
        adjusted_probability,
        profit_ratio or 0,
        expected_return or 0,
    )

    result = {
        "option_price": option_price,
        "implied_volatility": implied_vol,
        "time_to_expiry_years": T,
        "greeks": greeks,
        "risk_amount": risk_amount,
        "base_probability": base_prob,
        "adjusted_probability": adjusted_probability,
        "profit_ratio": profit_ratio,
        "expected_return": expected_return,
        "intrinsic_value": intrinsic_value,
        "extrinsic_value": extrinsic_value,
        "intrinsic_ratio": intrinsic_ratio,
        "underlying_price": S,
        "evaluated_expiry": expiry_str,
        "selected_strike": strike,
        "option_type": option_type,
    }
    # Format the primary metric (profit_ratio) using related metrics.
    result = format_primary_metric(
        result, "profit_ratio", ["adjusted_probability", "expected_return"]
    )
    return result


def evaluate_credit_spread(trade_details, live=False):
    """
    Evaluate a credit spread trade.
    For a short spread the probability of profit is computed as 1 - p_ITM of the short leg.
    Returns evaluation metrics along with leg details and expected return.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    option_type = trade_details.get("option_type", None)
    if not option_type:
        sentiment = trade_details.get("sentiment", "bullish")
        option_type = "put" if sentiment == "bearish" else "call"
    else:
        option_type = option_type.lower()
    ticker = AlpacaTicker(underlying)
    underlying_price = ticker.info.get("regularMarketPrice")

    logger.debug(
        "Evaluating credit spread for %s (%s) with expiry %s",
        underlying,
        option_type,
        expiry_str,
    )
    if "strike_short" not in trade_details or not trade_details.get("strike_short"):
        if option_type == "call":
            strike_short = get_atm_strike(underlying, expiry_str, option_type)
        else:
            t = AlpacaTicker(underlying)
            base_strike = round_to_nearest(t.info.get("regularMarketPrice"), 5)
            if base_strike < t.info.get("regularMarketPrice"):
                base_strike += 5
            strike_short = base_strike
        trade_details["strike_short"] = strike_short
        logger.debug("Auto-selected strike_short=%s for %s", strike_short, underlying)
    else:
        strike_short = float(trade_details.get("strike_short"))
    if "strike_long" not in trade_details or not trade_details.get("strike_long"):
        if option_type == "call":
            proposed = strike_short + underlying_price * 0.05
        else:
            proposed = strike_short - underlying_price * 0.05
        strike_long = round_to_nearest(proposed, 5)
        if option_type == "put" and strike_long >= strike_short:
            strike_long = strike_short - 5
        trade_details["strike_long"] = strike_long
        logger.debug("Auto-selected strike_long=%s for %s", strike_long, underlying)
    else:
        strike_long = float(trade_details.get("strike_long"))

    leg_short = get_option_leg_data(underlying, expiry_str, strike_short, option_type)
    leg_long = get_option_leg_data(underlying, expiry_str, strike_long, option_type)
    if "error" in leg_short or "error" in leg_long:
        logger.error(
            "Error retrieving leg data for credit spread on %s: short=%s, long=%s",
            underlying,
            leg_short,
            leg_long,
        )
        return {"error": "Error retrieving leg data for credit spread."}

    if live:
        live_data = get_live_options_chain(underlying, expiry_str)
        if not live_data:
            logger.error("Live data not available for %s", underlying)
            live = False

    if not live:
        try:
            opt_chain = ticker.option_chain(expiry_str)
            chain = opt_chain.calls if option_type == "call" else opt_chain.puts
            short_data = chain[chain["strike"] == strike_short]
            long_data = chain[chain["strike"] == strike_long]
            if short_data.empty or long_data.empty:
                logger.error(
                    "No price data found for one or both legs of credit spread for %s",
                    underlying,
                )
                return {
                    "error": "Could not find option prices for one or both legs of the spread."
                }
            short_price = short_data.iloc[0]["lastPrice"]
            long_price = long_data.iloc[0]["lastPrice"]
            logger.debug(
                "Retrieved Alpaca prices for credit spread on %s: short=%.2f, long=%.2f",
                underlying,
                short_price,
                long_price,
            )
        except Exception as e:
            logger.error(
                "Exception fetching options chain for credit spread on %s: %s",
                underlying,
                e,
            )
            return {"error": f"Failed to fetch options chain: {e}"}
    else:
        try:
            live_options = get_live_options_chain(underlying, expiry_str)
            options = live_options["options"]["option"]
            short_options = [
                o
                for o in options
                if abs(float(o["strike"]) - strike_short) < 1e-3
                and o["option_type"].lower() == option_type
            ]
            long_options = [
                o
                for o in options
                if abs(float(o["strike"]) - strike_long) < 1e-3
                and o["option_type"].lower() == option_type
            ]
            if not short_options or not long_options:
                logger.error(
                    "Live data: missing leg options for credit spread on %s", underlying
                )
                return {"error": "Live data: could not find both legs."}
            short_price = float(short_options[0]["last"])
            long_price = float(long_options[0]["last"])
            logger.debug(
                "Retrieved live prices for credit spread on %s: short=%.2f, long=%.2f",
                underlying,
                short_price,
                long_price,
            )
        except Exception as e:
            logger.error("Error parsing live options data for %s: %s", underlying, e)
            return {"error": f"Error parsing live options data: {e}"}

    credit_received = short_price - long_price
    max_profit = credit_received
    spread_width = abs(strike_long - strike_short)
    max_loss = spread_width - credit_received if spread_width > credit_received else 0
    risk_reward_ratio = credit_received / max_loss if max_loss else None

    t = AlpacaTicker(underlying)
    S = t.info.get("regularMarketPrice")
    r = 0.01
    opt_info = leg_short.get("greeks", {})
    d2 = opt_info.get("d2", None)
    sigma = leg_short.get("impliedVolatility", 0.2) or 0.2
    T = (
        datetime.datetime.strptime(expiry_str, "%Y-%m-%d") - datetime.datetime.today()
    ).days / 365.0
    if d2 is not None:
        analytic_prob_short = norm_cdf(d2) if option_type == "call" else norm_cdf(-d2)
    else:
        analytic_prob_short = 0.5
    mc_prob_short = monte_carlo_prob_ITM(S, strike_short, T, r, sigma, option_type)
    short_itm_prob = (analytic_prob_short + mc_prob_short) / 2
    base_prob = 1 - short_itm_prob

    intrinsic_short = (
        max(S - strike_short, 0) if option_type == "call" else max(strike_short - S, 0)
    )
    intrinsic_long = (
        max(S - strike_long, 0) if option_type == "call" else max(strike_long - S, 0)
    )
    net_intrinsic = intrinsic_short - intrinsic_long
    intrinsic_ratio = net_intrinsic / credit_received if credit_received > 0 else 0
    adjusted_probability = adjust_probability(base_prob, intrinsic_ratio)
    expected_return = (
        (risk_reward_ratio * adjusted_probability)
        if risk_reward_ratio is not None
        else None
    )

    logger.debug(
        "Credit spread for %s: short strike=%s, long strike=%s, credit=%.2f, risk/reward=%.2f, base_prob=%.2f, intrinsic_ratio=%.2f, adjusted_prob=%.2f, expected_return=%.2f",
        underlying,
        strike_short,
        strike_long,
        credit_received,
        risk_reward_ratio or 0,
        base_prob,
        intrinsic_ratio,
        adjusted_probability,
        expected_return or 0,
    )

    result = {
        "credit_received": credit_received,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "base_probability": base_prob,
        "adjusted_probability": adjusted_probability,
        "expected_return": expected_return,
        "evaluated_expiry": expiry_str,
        "selected_strikes": {"strike_short": strike_short, "strike_long": strike_long},
        "leg_details": {"short": leg_short, "long": leg_long},
        "option_type": option_type,
        "intrinsic_ratio": intrinsic_ratio,
    }
    result = format_primary_metric(
        result, "risk_reward_ratio", ["adjusted_probability", "expected_return"]
    )
    return result


def evaluate_debit_spread(trade_details):
    """
    Evaluate a debit spread trade.
    For a bull call spread, probability is approximated as the chance the underlying exceeds the break–even (strike_buy + net debit).
    For a bear put spread, use the probability that underlying is below the break–even.
    Returns evaluation metrics and leg details along with expected return.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    option_type = trade_details.get("option_type", "call").lower()
    ticker = AlpacaTicker(underlying)
    underlying_price = ticker.info.get("regularMarketPrice")

    logger.debug(
        "Evaluating debit spread for %s (%s) with expiry %s",
        underlying,
        option_type,
        expiry_str,
    )
    if "strike_buy" not in trade_details or not trade_details.get("strike_buy"):
        if option_type == "call":
            strike_buy = get_atm_strike(underlying, expiry_str, option_type)
        else:
            t = AlpacaTicker(underlying)
            base_strike = round_to_nearest(t.info.get("regularMarketPrice"), 5)
            if base_strike < t.info.get("regularMarketPrice"):
                base_strike += 5
            strike_buy = base_strike
        trade_details["strike_buy"] = strike_buy
        logger.debug("Auto-selected strike_buy=%s for %s", strike_buy, underlying)
    else:
        strike_buy = float(trade_details.get("strike_buy"))
    if "strike_sell" not in trade_details or not trade_details.get("strike_sell"):
        if option_type == "call":
            proposed = strike_buy + underlying_price * 0.05
        else:
            proposed = strike_buy - underlying_price * 0.05
        strike_sell = round_to_nearest(proposed, 5)
        if option_type == "put" and strike_sell >= strike_buy:
            strike_sell = strike_buy - 5
        trade_details["strike_sell"] = strike_sell
        logger.debug("Auto-selected strike_sell=%s for %s", strike_sell, underlying)
    else:
        strike_sell = float(trade_details.get("strike_sell"))

    leg_buy = get_option_leg_data(underlying, expiry_str, strike_buy, option_type)
    leg_sell = get_option_leg_data(underlying, expiry_str, strike_sell, option_type)
    if "error" in leg_buy or "error" in leg_sell:
        logger.error(
            "Error retrieving leg data for debit spread on %s: buy=%s, sell=%s",
            underlying,
            leg_buy,
            leg_sell,
        )
        return {"error": "Error retrieving leg data for debit spread."}

    try:
        opt_chain = ticker.option_chain(expiry_str)
    except Exception as e:
        logger.error(
            "Error fetching option chain for debit spread on %s: %s", underlying, e
        )
        return {"error": f"Failed to retrieve option chain: {e}"}
    chain = opt_chain.calls if option_type == "call" else opt_chain.puts
    buy_data = chain[chain["strike"] == strike_buy]
    sell_data = chain[chain["strike"] == strike_sell]
    if buy_data.empty or sell_data.empty:
        logger.error(
            "Missing price data for debit spread on %s: buy or sell leg empty",
            underlying,
        )
        return {
            "error": "Could not find option prices for one or both legs of the debit spread."
        }
    buy_price = buy_data.iloc[0]["lastPrice"]
    sell_price = sell_data.iloc[0]["lastPrice"]
    net_debit = buy_price - sell_price
    max_profit = (
        (strike_sell - strike_buy) - net_debit
        if strike_sell > strike_buy
        else net_debit
    )
    risk_reward_ratio = max_profit / net_debit if net_debit != 0 else None

    import datetime

    expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
    today = datetime.datetime.today()
    T = (expiry_date - today).days / 365.0
    sigma = leg_buy.get("impliedVolatility", 0.2) or 0.2
    r = 0.01

    if option_type == "call":
        break_even = strike_buy + net_debit
        analytic_prob = norm_cdf(
            (math.log(underlying_price / break_even) + (r - 0.5 * sigma**2) * T)
            / (sigma * math.sqrt(T))
        )
        mc_prob = monte_carlo_prob_ITM(
            underlying_price, break_even, T, r, sigma, "call"
        )
    else:
        break_even = strike_buy - net_debit
        analytic_prob = norm_cdf(
            (math.log(underlying_price / break_even) + (r - 0.5 * sigma**2) * T)
            / (sigma * math.sqrt(T))
        )
        mc_prob = monte_carlo_prob_ITM(underlying_price, break_even, T, r, sigma, "put")
    base_prob = (analytic_prob + mc_prob) / 2

    if option_type == "call":
        intrinsic_buy = max(underlying_price - strike_buy, 0)
        intrinsic_sell = max(underlying_price - strike_sell, 0)
    else:
        intrinsic_buy = max(strike_buy - underlying_price, 0)
        intrinsic_sell = max(strike_sell - underlying_price, 0)
    net_intrinsic = intrinsic_buy - intrinsic_sell
    intrinsic_ratio = net_intrinsic / net_debit if net_debit > 0 else 0

    adjusted_probability = adjust_probability(base_prob, intrinsic_ratio)
    expected_return = (
        risk_reward_ratio * adjusted_probability
        if risk_reward_ratio is not None
        else None
    )

    logger.debug(
        "Debit spread for %s: strike_buy=%s, strike_sell=%s, net_debit=%.2f, risk/reward=%.2f, break-even=%.2f, base_prob=%.2f, intrinsic_ratio=%.2f, adjusted_prob=%.2f, expected_return=%.2f",
        underlying,
        strike_buy,
        strike_sell,
        net_debit,
        risk_reward_ratio or 0,
        break_even,
        base_prob,
        intrinsic_ratio,
        adjusted_probability,
        expected_return or 0,
    )

    result = {
        "net_debit": net_debit,
        "max_profit": max_profit,
        "risk_reward_ratio": risk_reward_ratio,
        "expected_return": expected_return,
        "evaluated_expiry": expiry_str,
        "selected_strikes": {"strike_buy": strike_buy, "strike_sell": strike_sell},
        "leg_details": {"buy": leg_buy, "sell": leg_sell},
        "option_type": option_type,
        "intrinsic_ratio": intrinsic_ratio,
    }
    result = format_primary_metric(
        result, "risk_reward_ratio", ["adjusted_probability", "expected_return"]
    )
    return result


def evaluate_iron_condor(trade_details):
    """
    Evaluate an iron condor strategy.
    Returns evaluation metrics and leg details along with expected return.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    ticker = AlpacaTicker(underlying)
    underlying_price = ticker.info.get("regularMarketPrice")

    logger.debug("Evaluating iron condor for %s with expiry %s", underlying, expiry_str)
    if "strike_short_call" not in trade_details or not trade_details.get(
        "strike_short_call"
    ):
        trade_details["strike_short_call"] = get_atm_strike(
            underlying, expiry_str, "call"
        )
    if "strike_long_call" not in trade_details or not trade_details.get(
        "strike_long_call"
    ):
        proposed = float(trade_details["strike_short_call"]) + underlying_price * 0.05
        trade_details["strike_long_call"] = round_to_nearest(proposed, 5)
    if "strike_short_put" not in trade_details or not trade_details.get(
        "strike_short_put"
    ):
        trade_details["strike_short_put"] = get_atm_strike(
            underlying, expiry_str, "put"
        )
    if "strike_long_put" not in trade_details or not trade_details.get(
        "strike_long_put"
    ):
        proposed = float(trade_details["strike_short_put"]) - underlying_price * 0.05
        trade_details["strike_long_put"] = round_to_nearest(proposed, 5)

    strike_short_call = float(trade_details.get("strike_short_call"))
    strike_long_call = float(trade_details.get("strike_long_call"))
    strike_short_put = float(trade_details.get("strike_short_put"))
    strike_long_put = float(trade_details.get("strike_long_put"))

    leg_short_call = get_option_leg_data(
        underlying, expiry_str, strike_short_call, "call"
    )
    leg_long_call = get_option_leg_data(
        underlying, expiry_str, strike_long_call, "call"
    )
    leg_short_put = get_option_leg_data(underlying, expiry_str, strike_short_put, "put")
    leg_long_put = get_option_leg_data(underlying, expiry_str, strike_long_put, "put")
    for leg in [leg_short_call, leg_long_call, leg_short_put, leg_long_put]:
        if "error" in leg:
            logger.error(
                "Error retrieving leg data for iron condor on %s: %s", underlying, leg
            )
            return {"error": "Error retrieving leg data for iron condor."}

    try:
        opt_chain = ticker.option_chain(expiry_str)
    except Exception as e:
        logger.error(
            "Error fetching option chain for iron condor on %s: %s", underlying, e
        )
        return {"error": f"Failed to retrieve option chain: {e}"}
    calls = opt_chain.calls
    puts = opt_chain.puts

    short_call_data = calls[calls["strike"] == strike_short_call]
    long_call_data = calls[calls["strike"] == strike_long_call]
    short_put_data = puts[puts["strike"] == strike_short_put]
    long_put_data = puts[puts["strike"] == strike_long_put]

    if (
        short_call_data.empty
        or long_call_data.empty
        or short_put_data.empty
        or long_put_data.empty
    ):
        logger.error("Missing leg price data for iron condor on %s", underlying)
        return {
            "error": "Could not find prices for one or more legs of the iron condor."
        }

    short_call_price = short_call_data.iloc[0]["lastPrice"]
    long_call_price = long_call_data.iloc[0]["lastPrice"]
    short_put_price = short_put_data.iloc[0]["lastPrice"]
    long_put_price = long_put_data.iloc[0]["lastPrice"]

    net_credit = (short_call_price - long_call_price) + (
        short_put_price - long_put_price
    )
    max_loss_call = (
        strike_long_call - strike_short_call - (short_call_price - long_call_price)
    )
    max_loss_put = (
        strike_short_put - strike_long_put - (short_put_price - long_put_price)
    )
    max_loss = max(max_loss_call, max_loss_put)
    risk_reward_ratio = net_credit / max_loss if max_loss != 0 else None

    intrinsic_sc = max(underlying_price - strike_short_call, 0)
    intrinsic_lc = max(underlying_price - strike_long_call, 0)
    intrinsic_sp = max(strike_short_put - underlying_price, 0)
    intrinsic_lp = max(strike_long_put - underlying_price, 0)

    net_intrinsic = (intrinsic_sc + intrinsic_sp) - (intrinsic_lc + intrinsic_lp)
    intrinsic_ratio = max(0, net_intrinsic / net_credit) if net_credit > 0 else 0

    adjusted_probability = adjust_probability(0.5, intrinsic_ratio)
    expected_return = (
        (risk_reward_ratio * adjusted_probability)
        if risk_reward_ratio is not None
        else None
    )

    logger.debug(
        "Iron condor for %s: strikes: SC=%s, LC=%s, SP=%s, LP=%s, net_credit=%.2f, max_loss=%.2f, risk/reward=%.2f, intrinsic_ratio=%.2f, adjusted_prob=%.2f, expected_return=%.2f",
        underlying,
        strike_short_call,
        strike_long_call,
        strike_short_put,
        strike_long_put,
        net_credit,
        max_loss,
        risk_reward_ratio or 0,
        intrinsic_ratio,
        adjusted_probability,
        expected_return or 0,
    )

    result = {
        "net_credit": net_credit,
        "max_profit": net_credit,
        "max_loss": max_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "expected_return": expected_return,
        "evaluated_expiry": expiry_str,
        "selected_strikes": {
            "strike_short_call": strike_short_call,
            "strike_long_call": strike_long_call,
            "strike_short_put": strike_short_put,
            "strike_long_put": strike_long_put,
        },
        "leg_details": {
            "short_call": leg_short_call,
            "long_call": leg_long_call,
            "short_put": leg_short_put,
            "long_put": leg_long_put,
        },
        "option_types": {"call": "call", "put": "put"},
        "intrinsic_ratio": intrinsic_ratio,
    }
    result = format_primary_metric(result, "risk_reward_ratio", [])
    return result


def evaluate_option_strategy(trade_details, live=False):
    """
    Evaluate an option trade based on the specified strategy.
    Supported strategies:
      - "long": Uses evaluate_option_trade.
      - "credit_spread": Uses evaluate_credit_spread.
      - "debit_spread": Uses evaluate_debit_spread.
      - "iron_condor": Uses evaluate_iron_condor.
    Returns evaluation metrics.
    """
    strategy = trade_details.get("strategy", "long").lower()
    logger.debug("Evaluating option strategy: %s", strategy)
    if strategy == "credit_spread":
        return evaluate_credit_spread(trade_details, live=live)
    elif strategy == "debit_spread":
        return evaluate_debit_spread(trade_details)
    elif strategy == "iron_condor":
        return evaluate_iron_condor(trade_details)
    else:
        return evaluate_option_trade(trade_details)


def evaluate_options_for_multiple_tickers(tickers, base_trade_details):
    """
    Evaluate an option trade for multiple tickers.
    `tickers` is a list of ticker symbols.
    `base_trade_details` is a dictionary with common parameters.
    Returns a dictionary mapping ticker to evaluation result.
    """
    results = {}
    for ticker in tickers:
        trade_details = base_trade_details.copy()
        trade_details["underlying"] = ticker
        if base_trade_details.get("strategy") in [
            "credit_spread",
            "debit_spread",
            "iron_condor",
        ]:
            sentiment = base_trade_details.get("sentiment", "bullish")
            trade_details["option_type"] = "put" if sentiment == "bearish" else "call"
        results[ticker] = evaluate_option_strategy(trade_details)
    return results
