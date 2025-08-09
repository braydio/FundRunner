"""Simple historical backtesting utilities.

This module provides helper functions for benchmarking trading strategies. In
addition to a basic single-symbol backtest, it supports portfolio simulations
with configurable rebalancing rules and reports common performance metrics.
"""

import logging
from typing import Dict, Iterable, List, Optional

import pandas as pd

from fundrunner.alpaca.api_client import AlpacaClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _calculate_cagr(values: List[float], periods_per_year: int = 252) -> float:
    """Return the compound annual growth rate for a series of values."""

    if not values or len(values) < 2:
        return 0.0
    years = len(values) / periods_per_year
    return (values[-1] / values[0]) ** (1 / years) - 1


def _max_drawdown(values: List[float]) -> float:
    """Return the maximum drawdown for a series of portfolio values."""

    peak = values[0] if values else 0.0
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        drawdown = (peak - v) / peak if peak else 0.0
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def run_backtest(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    allocation_limit: float = 0.05,
) -> Optional[dict]:
    """Run a simple backtest for a single symbol.

    Strategy:
    - For each day, if the intraday return (from open to close) exceeds a
      threshold, simulate a trade.
    - Buy at the open and sell at the close; update capital based on the profit.

    Args:
        symbol: Stock ticker.
        start_date: Start date in ``YYYY-MM-DD`` format.
        end_date: End date in ``YYYY-MM-DD`` format.
        initial_capital: Starting capital.
        allocation_limit: Fraction of capital allocated per trade.

    Returns:
        Dictionary of performance metrics including final capital, CAGR, max
        drawdown, and trade details. ``None`` if no data was returned.
    """

    client = AlpacaClient()
    data = client.get_bars(symbol, start_date, end_date)
    if not data:
        logger.error("No data found for symbol %s", symbol)
        return None

    capital = initial_capital
    capital_history = [capital]
    trades: List[dict] = []
    threshold = 0.01  # Example: 1% intraday move triggers a trade

    for bar in data:
        open_price = bar["o"]
        close_price = bar["c"]
        daily_return = (close_price - open_price) / open_price

        if daily_return > threshold:
            # Simulate trade: buy at open, sell at close.
            allocation = capital * allocation_limit
            qty = allocation / open_price
            trade_profit = qty * (close_price - open_price)
            capital += trade_profit
            trades.append(
                {
                    "date": bar["t"],
                    "open": open_price,
                    "close": close_price,
                    "qty": qty,
                    "profit": trade_profit,
                }
            )

        capital_history.append(capital)

    performance = {
        "final_capital": capital,
        "total_return": (capital - initial_capital) / initial_capital,
        "num_trades": len(trades),
        "trades": trades,
        "cagr": _calculate_cagr(capital_history),
        "max_drawdown": _max_drawdown(capital_history),
    }
    logger.info(
        "Backtest complete for %s. Final capital: %.2f, Total return: %.2f%%, Trades: %d",
        symbol,
        capital,
        performance["total_return"] * 100,
        len(trades),
    )
    return performance


def backtest_portfolio(
    symbols: Iterable[str],
    weights: Dict[str, float],
    start_date: str,
    end_date: str,
    initial_capital: float = 100000,
    rebalance_frequency: int = 21,
    rebalance_threshold: float = 0.05,
) -> dict:
    """Backtest a portfolio with configurable rebalancing rules.

    The portfolio is initialised to ``weights`` and evolves with daily close
    prices. Holdings are rebalanced either every ``rebalance_frequency`` trading
    days or when any asset's weight deviates from its target by more than
    ``rebalance_threshold``.

    Args:
        symbols: Iterable of stock tickers.
        weights: Target portfolio weights for each symbol. Must sum to 1.
        start_date: Start date in ``YYYY-MM-DD`` format.
        end_date: End date in ``YYYY-MM-DD`` format.
        initial_capital: Starting capital.
        rebalance_frequency: Trading-day interval between forced rebalances.
        rebalance_threshold: Maximum allowed absolute deviation from target
            weight before a rebalance is triggered.

    Returns:
        Dictionary of performance metrics including final value, CAGR, maximum
        drawdown and the daily portfolio value history.
    """

    client = AlpacaClient()
    price_frames = {}
    dates: Optional[List[str]] = None

    for symbol in symbols:
        bars = client.get_bars(symbol, start_date, end_date)
        if not bars:
            raise ValueError(f"No data found for symbol {symbol}")
        if dates is None:
            dates = [bar["t"] for bar in bars]
        price_frames[symbol] = [bar["c"] for bar in bars]

    df = pd.DataFrame(price_frames, index=pd.to_datetime(dates))

    holdings = {
        sym: (initial_capital * weights[sym]) / df.iloc[0][sym] for sym in symbols
    }

    values: List[float] = []
    for i, (_, row) in enumerate(df.iterrows()):
        portfolio_value = sum(holdings[sym] * row[sym] for sym in symbols)
        values.append(portfolio_value)

        current_weights = {
            sym: (holdings[sym] * row[sym]) / portfolio_value for sym in symbols
        }

        deviation = max(abs(current_weights[sym] - weights[sym]) for sym in symbols)
        if (i + 1) % rebalance_frequency == 0 or deviation > rebalance_threshold:
            for sym in symbols:
                holdings[sym] = (portfolio_value * weights[sym]) / row[sym]

    performance = {
        "final_value": values[-1],
        "cagr": _calculate_cagr(values),
        "max_drawdown": _max_drawdown(values),
        "history": values,
    }

    logger.info(
        "Portfolio backtest complete. Final value: %.2f, CAGR: %.2f%%",
        performance["final_value"],
        performance["cagr"] * 100,
    )
    return performance
