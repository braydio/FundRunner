"""
LLM-Driven Multi-Metric Options Sentiment Analysis Plugin

Analyzes 10 different options metrics at multiple levels of granularity,
calls the local LLM per-metric and then for the aggregate, returns detailed sentiment.
"""

from typing import Dict, Any, List
import logging

# Example: These could be passed in from fundrunner.options.options_integration or api_client
OPTION_METRICS = [
    "open_interest",
    "volume",
    "put_call_ratio",
    "iv_rank",
    "iv_percentile",
    "max_pain",
    "unusual_activity_score",
    "skew",
    "gamma_exposure",
    "largest_trade_size",
]


def run_llm_analysis(metric: str, value: Any, context: Dict) -> Dict:
    """
    Sends a structured prompt to the local LLM to analyze a single options metric.
    Returns the LLM's analysis as a dictionary.
    """
    # Example prompt construction
    prompt = (
        f"Analyze the following options market metric for sentiment:\n"
        f"Metric: {metric}\n"
        f"Value: {value}\n"
        f"Context: {context.get('symbol', '')}, {context.get('date', '')}\n"
        f"Explain what this metric value means in this market context for sentiment and possible direction. "
        f"Be specific, concise, and focus on actionable insights."
    )
    # TODO: Wire to your local LLM endpoint here!
    # Replace this line with a call to your LLM API.
    llm_result = {
        "sentiment": "neutral",
        "summary": f"LLM analysis not implemented for {metric}.",
    }
    return llm_result


def analyze_option_metrics(symbol: str, metrics: Dict[str, Any], context: Dict) -> Dict:
    """
    Analyzes all metrics individually via LLM and then aggregates for a final sentiment verdict.
    """
    results = {}
    for metric in OPTION_METRICS:
        value = metrics.get(metric)
        if value is not None:
            analysis = run_llm_analysis(metric, value, {**context, "symbol": symbol})
            results[metric] = analysis
        else:
            results[metric] = {
                "sentiment": "unknown",
                "summary": f"No data for {metric}.",
            }

    # Now aggregate all metric-level LLM verdicts
    aggregate_prompt = (
        "Given these individual metric analyses for the options chain on {symbol}:\n"
        + "\n".join([f"{m}: {results[m]['summary']}" for m in OPTION_METRICS])
        + "\n\nAggregate all the above and determine the overall sentiment and expected move direction for the underlying."
    )
    # TODO: Replace this call with local LLM
    aggregate_llm_result = {
        "sentiment": "neutral",
        "summary": "Aggregate LLM analysis not implemented.",
    }
    results["aggregate"] = aggregate_llm_result
    return results


# Example entrypoint for daemon or dashboard:
def analyze_symbol_options_sentiment(
    symbol: str, metrics: Dict[str, Any], context: Dict
) -> Dict:
    """
    Top-level entry: Pass symbol, metrics, and context.
    Returns dict of per-metric and aggregate LLM analyses.
    """
    return analyze_option_metrics(symbol, metrics, context)


def get_metrics_for_multi_analysis(symbol, expiry, strike, option_type="call"):
    """
    Get option metrics for a symbol, expiry, and strike from Alpaca.
    Returns a dictionary with the metrics needed for the LLM plugin.
    """
    # Fetch option chain for the symbol/expiry
    # Note: Alpaca's SDK supports fetch_option_chain(), but you may need to use their REST endpoint directly for full metrics
    # Here is an example using the SDK; adjust fields as needed for your Alpaca API version

    # Get all options for the symbol at a certain expiry
    try:
        chain = alpaca.get_option_chain(symbol, expiry=expiry)
    except Exception as e:
        print(f"Error fetching option chain: {e}")
        return {}

    # Filter for the specific strike/option type
    options = [
        o
        for o in chain
        if float(o.strike_price) == float(strike)
        and o.option_type.lower() == option_type.lower()
    ]
    if not options:
        print(f"No options found for {symbol} {expiry} {strike} {option_type}")
        return {}

    opt = options[0]

    # Calculate put/call ratio (across all strikes, same expiry)
    puts = [o for o in chain if o.option_type == "put"]
    calls = [o for o in chain if o.option_type == "call"]
    put_volume = sum(float(o.volume or 0) for o in puts)
    call_volume = sum(float(o.volume or 0) for o in calls)
    put_call_ratio = (put_volume / call_volume) if call_volume else 0

    # Example placeholder values for metrics that may need additional logic
    iv_rank = float(opt.implied_volatility or 0)
    iv_percentile = float(
        opt.implied_volatility or 0
    )  # Replace with actual percentile logic
    max_pain = (
        None  # You'd need to calculate this from the chain, or skip if not needed now
    )
    unusual_activity_score = None  # Placeholder, see note below
    skew = None  # Placeholder
    gamma_exposure = None  # Placeholder
    largest_trade_size = float(
        opt.open_interest or 0
    )  # Best available unless you track trades

    metrics = {
        "open_interest": float(opt.open_interest or 0),
        "volume": float(opt.volume or 0),
        "put_call_ratio": put_call_ratio,
        "iv_rank": iv_rank,
        "iv_percentile": iv_percentile,
        "max_pain": max_pain,
        "unusual_activity_score": unusual_activity_score,
        "skew": skew,
        "gamma_exposure": gamma_exposure,
        "largest_trade_size": largest_trade_size,
    }
    return metrics
