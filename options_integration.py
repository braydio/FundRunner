
# options_integration.py
import math
import datetime
import yfinance as yf
import logging
import requests  # used for live data if needed
from live_options_api import get_live_options_chain  # our updated module using Alpaca Options API

logger = logging.getLogger(__name__)

def norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
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
    
    if option_type == 'call':
        delta = norm_cdf(d1)
        theta = -(S * norm_pdf_d1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)
        rho = K * T * math.exp(-r * T) * norm_cdf(d2)
    else:
        delta = norm_cdf(d1) - 1
        theta = -(S * norm_pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)
        rho = -K * T * math.exp(-r * T) * norm_cdf(-d2)
    
    vega = S * math.sqrt(T) * norm_pdf_d1

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}

def get_nearest_expiry(ticker, requested_expiry):
    """
    Given a ticker and a requested expiry date string, return the nearest available expiry date (as string)
    that is >= requested date. If none available, return the last expiry.
    """
    try:
        options = yf.Ticker(ticker).options
        if not requested_expiry:
            return options[0] if options else None
        requested_date = datetime.datetime.strptime(requested_expiry, "%Y-%m-%d")
        available = sorted(options, key=lambda d: datetime.datetime.strptime(d, "%Y-%m-%d"))
        for exp in available:
            exp_date = datetime.datetime.strptime(exp, "%Y-%m-%d")
            if exp_date >= requested_date:
                return exp
        return available[-1] if available else None
    except Exception as e:
        logger.error("Error determining nearest expiry for %s: %s", ticker, e)
        return requested_expiry

def get_atm_strike(ticker, expiry, option_type):
    """
    Retrieve the ATM strike for a given ticker and expiry from yfinance option chain.
    """
    try:
        t = yf.Ticker(ticker)
        chain = t.option_chain(expiry).calls if option_type == "call" else t.option_chain(expiry).puts
        underlying_price = t.info.get("regularMarketPrice")
        if underlying_price is None:
            return None
        strikes = chain['strike'].tolist()
        atm_strike = min(strikes, key=lambda x: abs(x - underlying_price))
        return atm_strike
    except Exception as e:
        logger.error("Error selecting ATM strike for %s: %s", ticker, e)
        return None

def evaluate_option_trade(trade_details):
    """
    Evaluate a long option trade (call or put) using yfinance data.
    Expects trade_details to include:
      - underlying, expiry, [strike], option_type, position.
    If strike is not provided, automatically choose the ATM strike.
    Returns evaluation metrics.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    option_type = trade_details.get("option_type", "call").lower()
    position = trade_details.get("position", "long").lower()

    if "strike" not in trade_details or not trade_details.get("strike"):
        atm_strike = get_atm_strike(underlying, expiry_str, option_type)
        if atm_strike is None:
            return {"error": "Unable to determine ATM strike."}
        strike = atm_strike
    else:
        strike = float(trade_details.get("strike"))
    
    ticker = yf.Ticker(underlying)
    try:
        options = ticker.options
        if expiry_str not in options:
            return {"error": f"Expiry {expiry_str} not available for {underlying}. Available expiries: {options}"}
    except Exception as e:
        return {"error": f"Failed to retrieve options for {underlying}: {e}"}
    
    try:
        opt_chain = ticker.option_chain(expiry_str)
    except Exception as e:
        return {"error": f"Failed to retrieve option chain for expiry {expiry_str}: {e}"}
    chain = opt_chain.calls if option_type == "call" else opt_chain.puts
    option_data = chain[chain['strike'] == strike]
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
        risk_amount = 2 * option_price
    
    if position == "long":
        probability_of_profit = greeks.get("delta", 0) if option_type == "call" else 1 - greeks.get("delta", 0)
    else:
        probability_of_profit = 1 - greeks.get("delta", 0) if option_type == "call" else greeks.get("delta", 0)
    
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
        "evaluated_expiry": expiry_str,
        "selected_strike": strike
    }

def evaluate_credit_spread(trade_details, live=False):
    """
    Evaluate a credit spread trade.
    Expected trade_details should include:
      - underlying, expiry, [strike_short], [strike_long], option_type, strategy.
    If strikes are not provided, automatically determine them based on ATM.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    option_type = trade_details.get("option_type", "call").lower()
    ticker = yf.Ticker(underlying)
    underlying_price = ticker.info.get("regularMarketPrice")
    
    if "strike_short" not in trade_details or not trade_details.get("strike_short"):
        atm = get_atm_strike(underlying, expiry_str, option_type)
        if atm is None:
            return {"error": "Unable to determine ATM strike for credit spread."}
        trade_details["strike_short"] = atm
    if "strike_long" not in trade_details or not trade_details.get("strike_long"):
        if option_type == "call":
            trade_details["strike_long"] = float(trade_details["strike_short"]) + underlying_price * 0.05
        else:
            trade_details["strike_long"] = float(trade_details["strike_short"]) - underlying_price * 0.05

    strike_short = float(trade_details.get("strike_short"))
    strike_long = float(trade_details.get("strike_long"))
    
    if live:
        live_data = get_live_options_chain(underlying, expiry_str)
        if not live_data:
            logger.error("Live data not available; falling back to yfinance.")
            live = False

    if not live:
        try:
            opt_chain = ticker.option_chain(expiry_str)
        except Exception as e:
            return {"error": f"Failed to fetch options chain: {e}"}
        chain = opt_chain.calls if option_type == "call" else opt_chain.puts
        short_data = chain[chain['strike'] == strike_short]
        long_data = chain[chain['strike'] == strike_long]
        if short_data.empty or long_data.empty:
            return {"error": "Could not find option prices for one or both legs of the spread."}
        short_price = short_data.iloc[0]["lastPrice"]
        long_price = long_data.iloc[0]["lastPrice"]
    else:
        live_options = get_live_options_chain(underlying, expiry_str)
        try:
            options = live_options["options"]["option"]
            short_options = [o for o in options if float(o["strike"]) == strike_short and o["option_type"].lower() == option_type]
            long_options = [o for o in options if float(o["strike"]) == strike_long and o["option_type"].lower() == option_type]
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

    try:
        opt_chain = ticker.option_chain(expiry_str)
        chain = opt_chain.calls if option_type == "call" else opt_chain.puts
        short_data = chain[chain['strike'] == strike_short]
        if not short_data.empty:
            delta = short_data.iloc[0].get("delta", 0)
        else:
            delta = 0.5
    except Exception:
        delta = 0.5
    probability_of_profit = delta
    
    return {
        "credit_received": credit_received,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "probability_of_profit": probability_of_profit,
        "evaluated_expiry": expiry_str,
        "selected_strikes": {"strike_short": strike_short, "strike_long": strike_long}
    }

def evaluate_debit_spread(trade_details):
    """
    Evaluate a debit spread trade.
    Expected trade_details should include:
      - underlying, expiry, [strike_buy], [strike_sell], option_type.
    If strikes are not provided, determine them automatically based on ATM.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    option_type = trade_details.get("option_type", "call").lower()
    ticker = yf.Ticker(underlying)
    underlying_price = ticker.info.get("regularMarketPrice")
    
    if "strike_buy" not in trade_details or not trade_details.get("strike_buy"):
        atm = get_atm_strike(underlying, expiry_str, option_type)
        if atm is None:
            return {"error": "Unable to determine ATM strike for debit spread."}
        trade_details["strike_buy"] = atm
    if "strike_sell" not in trade_details or not trade_details.get("strike_sell"):
        if option_type == "call":
            trade_details["strike_sell"] = float(trade_details["strike_buy"]) + underlying_price * 0.05
        else:
            trade_details["strike_sell"] = float(trade_details["strike_buy"]) - underlying_price * 0.05

    strike_buy = float(trade_details.get("strike_buy"))
    strike_sell = float(trade_details.get("strike_sell"))
    
    try:
        opt_chain = ticker.option_chain(expiry_str)
    except Exception as e:
        return {"error": f"Failed to retrieve option chain for expiry {expiry_str}: {e}"}
    chain = opt_chain.calls if option_type == "call" else opt_chain.puts
    buy_data = chain[chain['strike'] == strike_buy]
    sell_data = chain[chain['strike'] == strike_sell]
    if buy_data.empty or sell_data.empty:
        return {"error": "Could not find option prices for one or both legs of the debit spread."}
    buy_price = buy_data.iloc[0]["lastPrice"]
    sell_price = sell_data.iloc[0]["lastPrice"]
    net_debit = buy_price - sell_price
    max_profit = (strike_sell - strike_buy) - net_debit if strike_sell > strike_buy else net_debit
    risk_reward_ratio = max_profit / net_debit if net_debit != 0 else None
    return {
        "net_debit": net_debit,
        "max_profit": max_profit,
        "risk_reward_ratio": risk_reward_ratio,
        "evaluated_expiry": expiry_str,
        "selected_strikes": {"strike_buy": strike_buy, "strike_sell": strike_sell}
    }

def evaluate_iron_condor(trade_details):
    """
    Evaluate an iron condor strategy.
    Expected trade_details should include:
      - underlying, expiry, [strike_short_call], [strike_long_call], [strike_short_put], [strike_long_put].
    If strikes are not provided, determine them automatically based on ATM.
    """
    underlying = trade_details.get("underlying")
    requested_expiry = trade_details.get("expiry", "")
    expiry_str = get_nearest_expiry(underlying, requested_expiry)
    ticker = yf.Ticker(underlying)
    underlying_price = ticker.info.get("regularMarketPrice")
    
    if "strike_short_call" not in trade_details or not trade_details.get("strike_short_call"):
        trade_details["strike_short_call"] = get_atm_strike(underlying, expiry_str, "call")
    if "strike_long_call" not in trade_details or not trade_details.get("strike_long_call"):
        trade_details["strike_long_call"] = float(trade_details["strike_short_call"]) + underlying_price * 0.05
    if "strike_short_put" not in trade_details or not trade_details.get("strike_short_put"):
        trade_details["strike_short_put"] = get_atm_strike(underlying, expiry_str, "put")
    if "strike_long_put" not in trade_details or not trade_details.get("strike_long_put"):
        trade_details["strike_long_put"] = float(trade_details["strike_short_put"]) - underlying_price * 0.05

    strike_short_call = float(trade_details.get("strike_short_call"))
    strike_long_call = float(trade_details.get("strike_long_call"))
    strike_short_put = float(trade_details.get("strike_short_put"))
    strike_long_put = float(trade_details.get("strike_long_put"))
    
    try:
        opt_chain = ticker.option_chain(expiry_str)
    except Exception as e:
        return {"error": f"Failed to retrieve option chain for expiry {expiry_str}: {e}"}
    calls = opt_chain.calls
    puts = opt_chain.puts
    
    short_call_data = calls[calls['strike'] == strike_short_call]
    long_call_data = calls[calls['strike'] == strike_long_call]
    short_put_data = puts[puts['strike'] == strike_short_put]
    long_put_data = puts[puts['strike'] == strike_long_put]
    
    if short_call_data.empty or long_call_data.empty or short_put_data.empty or long_put_data.empty:
        return {"error": "Could not find prices for one or more legs of the iron condor."}
    
    short_call_price = short_call_data.iloc[0]["lastPrice"]
    long_call_price = long_call_data.iloc[0]["lastPrice"]
    short_put_price = short_put_data.iloc[0]["lastPrice"]
    long_put_price = long_put_data.iloc[0]["lastPrice"]
    
    net_credit = (short_call_price - long_call_price) + (short_put_price - long_put_price)
    max_loss_call = strike_long_call - strike_short_call - (short_call_price - long_call_price)
    max_loss_put = strike_short_put - strike_long_put - (short_put_price - long_put_price)
    max_loss = max(max_loss_call, max_loss_put)
    risk_reward_ratio = net_credit / max_loss if max_loss != 0 else None
    
    return {
        "net_credit": net_credit,
        "max_profit": net_credit,
        "max_loss": max_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "evaluated_expiry": expiry_str,
        "selected_strikes": {
            "strike_short_call": strike_short_call,
            "strike_long_call": strike_long_call,
            "strike_short_put": strike_short_put,
            "strike_long_put": strike_long_put
        }
    }

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
        results[ticker] = evaluate_option_strategy(trade_details)
    return results

