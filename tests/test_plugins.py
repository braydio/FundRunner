# Plugin Interfaces for FundRunner Extensions
"""Optional plugin examples tested only when dependencies exist."""

import pytest

import pytest

pytest.importorskip("pypfopt")
pytest.importorskip("mplfinance")
pytest.importorskip("transformers")
pytest.importorskip("torch")

# ----------------------------
# 1. PyPortfolioOpt Plugin (Risk Management / Allocation)
# ----------------------------

from pypfopt import EfficientFrontier, risk_models, expected_returns


def optimize_portfolio(prices_df):
    # prices_df: DataFrame with historical price data (columns = tickers)
    mu = expected_returns.mean_historical_return(prices_df)
    S = risk_models.sample_cov(prices_df)
    ef = EfficientFrontier(mu, S)
    _ = ef.max_sharpe()
    cleaned = ef.clean_weights()
    return cleaned


# Example usage in risk_manager.py:
# weights = optimize_portfolio(price_data)


# ----------------------------
# 2. mplfinance Plugin (Backtest Visualization)
# ----------------------------

# requirements.txt: mplfinance
import mplfinance as mpf


def plot_trades(df, trades=None, title="Backtest Result"):
    # df should be a DataFrame with datetime index, OHLCV columns
    # trades: optional list of dicts with 'date', 'qty', 'profit'
    if trades:
        addplot = [mpf.make_addplot([t["profit"] for t in trades], panel=1, color="g")]
    else:
        addplot = []
    mpf.plot(df, type="candle", style="charles", title=title, addplot=addplot)


# Example usage in dashboard.py:
# plot_trades(price_df, trades=backtest_result['trades'])


# ----------------------------
# 3. FinBERT Plugin (LLM sentiment augmentation)
# ----------------------------

# requirements.txt: transformers, torch
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch

    # Load once at startup
    tokenizer = AutoTokenizer.from_pretrained("yiyanghkust/finbert-sentiment")
    model = AutoModelForSequenceClassification.from_pretrained(
        "yiyanghkust/finbert-sentiment"
    )
except Exception:  # pragma: no cover - optional dependency may be unavailable
    tokenizer = None
    model = None


def analyze_sentiment(text):
    if tokenizer is None or model is None:
        raise RuntimeError("FinBERT model unavailable")
    inputs = tokenizer(text, return_tensors="pt", truncation=True)
    outputs = model(**inputs)
    scores = (
        torch.nn.functional.softmax(outputs.logits, dim=1).detach().numpy()[0]
    )
    return {"positive": scores[0], "neutral": scores[1], "negative": scores[2]}


# Example usage in llm_vetter.py or chatgpt_advisor.py:
# sentiment = analyze_sentiment("AAPL earnings call: strong iPhone sales...")
