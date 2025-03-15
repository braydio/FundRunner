
# Begin options_analyzer.py
# options_analyzer.py
import math
import datetime
import yfinance as yf

def norm_cdf(x):
    """Cumulative distribution function for the standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))

def black_scholes_greeks(S, K, T, r, sigma, option_type='call'):
    """
    Compute Black-Scholes option greeks for a European option.
    Returns a dictionary with delta, gamma, theta, vega, and rho.
    """
    # Avoid division by zero
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
    else:  # put option
        delta = norm_cdf(d1) - 1
        theta = -(S * norm_pdf_d1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)
        rho = -K * T * math.exp(-r * T) * norm_cdf(-d2)
    
    vega = S * math.sqrt(T) * norm_pdf_d1

    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}

def evaluate_option_trade(trade_details):
    """
    Evaluate an options trade based on the provided trade details.
    
    trade_details should be a dict containing:
      - underlying: the underlying ticker (string)
      - expiry: expiration date as 'YYYY-MM-DD' (string)
      - strike: strike price (float)
      - option_type: 'call' or 'put' (string)
      - position: 'long' or 'short' (string)
    
    This function retrieves the option chain from yfinance and selects the option
    with the given strike and type. It then computes key metrics using a Black-Scholes model.
    
    Returns a dictionary with:
      - option_price: Last price of the option
      - implied_volatility: Implied volatility from the chain
      - time_to_expiry_years: Time to expiry in years
      - greeks: A dictionary of calculated option greeks
      - risk_amount: Approximate risk amount (premium for long; a placeholder for short)
      - probability_of_profit: Approximate probability of profit (using delta as a proxy)
      - profit_ratio: Estimated profit-to-risk ratio (using a simple underlying move assumption)
      - underlying_price: Current price of the underlying asset
    """
    underlying = trade_details.get("underlying")
    expiry_str = trade_details.get("expiry")
    strike = float(trade_details.get("strike"))
    option_type = trade_details.get("option_type").lower()  # 'call' or 'put'
    position = trade_details.get("position").lower()  # 'long' or 'short'
    
    ticker = yf.Ticker(underlying)
    try:
        options = ticker.options
    except Exception as e:
        return {"error": f"Failed to retrieve options for {underlying}: {e}"}
    
    if expiry_str not in options:
        return {"error": f"Expiry {expiry_str} not available for {underlying}. Available expiries: {options}"}
    
    opt_chain = ticker.option_chain(expiry_str)
    chain = opt_chain.calls if option_type == "call" else opt_chain.puts
    
    option_data = chain[chain['strike'] == strike]
    if option_data.empty:
        return {"error": f"No option found for strike {strike} and type {option_type}"}
    
    option_info = option_data.iloc[0].to_dict()
    option_price = option_info.get("lastPrice")
    implied_vol = option_info.get("impliedVolatility")
    
    # Compute time to expiry in years.
    expiry_date = datetime.datetime.strptime(expiry_str, "%Y-%m-%d")
    today = datetime.datetime.today()
    T = (expiry_date - today).days / 365.0
    if T <= 0:
        return {"error": "Option has expired."}
    
    S = ticker.info.get("regularMarketPrice")
    K = strike
    r = 0.01  # assume 1% risk-free rate
    sigma = implied_vol if implied_vol else 0.2
    
    greeks = black_scholes_greeks(S, K, T, r, sigma, option_type)
    
    if position == "long":
        risk_amount = option_price  # risk is the premium paid
    else:
        risk_amount = 2 * option_price  # placeholder risk metric for short options
    
    if position == "long":
        if option_type == "call":
            probability_of_profit = greeks.get("delta", 0)
        else:
            probability_of_profit = 1 - greeks.get("delta", 0)
    else:
        if option_type == "call":
            probability_of_profit = 1 - greeks.get("delta", 0)
        else:
            probability_of_profit = greeks.get("delta", 0)
    
    potential_move = 0.05 * S
    if option_type == "call":
        potential_profit = max(S + potential_move - K, 0) - option_price
    else:
        potential_profit = max(K - (S - potential_move), 0) - option_price
    profit_ratio = potential_profit / risk_amount if risk_amount != 0 else None
    
    metrics = {
        "option_price": option_price,
        "implied_volatility": implied_vol,
        "time_to_expiry_years": T,
        "greeks": greeks,
        "risk_amount": risk_amount,
        "probability_of_profit": probability_of_profit,
        "profit_ratio": profit_ratio,
        "underlying_price": S
    }
    return metrics

def evaluate_open_option_position(position):
    """
    Evaluate an open options position using its calculated metrics.
    
    The `position` argument should be a dictionary containing details such as:
      - greeks: dictionary with option greeks
      - profit_ratio: estimated profit ratio
      - probability_of_profit: estimated likelihood of profit
    
    This function applies simple threshold criteria and returns a recommendation string.
    """
    delta = position.get("greeks", {}).get("delta", 0)
    theta = position.get("greeks", {}).get("theta", 0)
    profit_ratio = position.get("profit_ratio", 0)
    
    # Define example thresholds.
    max_delta_threshold = 0.7   # if |delta| > 0.7, risk may be excessive.
    max_theta_threshold = -5    # if theta is very negative (rapid decay)
    min_profit_ratio = 0.5      # target profit ratio
    
    recommendations = []
    if abs(delta) > max_delta_threshold:
        recommendations.append("High delta exposure")
    if theta < max_theta_threshold:
        recommendations.append("Excessive theta decay")
    if profit_ratio < min_profit_ratio:
        recommendations.append("Low profit ratio")
    
    if recommendations:
        return "Consider adjusting position: " + ", ".join(recommendations)
    else:
        return "Position appears to be within acceptable risk parameters."

def get_options_trades():
    """
    In a real implementation, this might load trade definitions from a file or database.
    Here, we simulate by returning a list of sample options trade definitions.
    
    Each trade definition is a dictionary with:
      - underlying: ticker symbol (string)
      - expiry: option expiration date in 'YYYY-MM-DD' format (string)
      - strike: strike price (float)
      - option_type: 'call' or 'put' (string)
      - position: 'long' or 'short' (string)
    """
    return [
        {"underlying": "AAPL", "expiry": "2025-03-20", "strike": 150, "option_type": "call", "position": "long"},
        {"underlying": "MSFT", "expiry": "2025-03-20", "strike": 300, "option_type": "put", "position": "long"}
    ]

async def run_options_analysis():
    """
    Continuously analyze options trades throughout the day.
    For each trade definition, it calculates key metrics and evaluates risk.
    """
    logger.info("Starting options trading bot analysis.")
    while True:
        trades = get_options_trades()
        for trade in trades:
            logger.info("Evaluating option trade: %s", trade)
            metrics = evaluate_option_trade(trade)
            if "error" in metrics:
                logger.error("Error evaluating option trade: %s", metrics["error"])
            else:
                logger.info("Options trade metrics: %s", metrics)
                recommendation = evaluate_open_option_position(metrics)
                logger.info("Risk evaluation recommendation: %s", recommendation)
        logger.info("Options analysis cycle complete. Sleeping for 60 seconds.")
        await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_options_analysis())

# End options_trading_bot.py
