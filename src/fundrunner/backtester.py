# backtester.py
"""Simple historical backtesting utilities."""

import logging
from fundrunner.alpaca.api_client import AlpacaClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def run_backtest(symbol, start_date, end_date, initial_capital=100000, allocation_limit=0.05):
    """
    Run a simple backtest for the given symbol between start_date and end_date.
    Strategy:
      - For each day, if the intraday return (from Open to Close) exceeds a threshold, simulate a trade.
      - Buy at the open and sell at the close; update capital based on the profit.
    
    Args:
        symbol (str): Stock ticker.
        start_date (str): Start date in 'YYYY-MM-DD' format.
        end_date (str): End date in 'YYYY-MM-DD' format.
        initial_capital (float): Starting capital.
        allocation_limit (float): Fraction of capital allocated per trade.
    
    Returns:
        dict: Performance metrics including final capital, total return, and trade details.
    """
    client = AlpacaClient()
    data = client.get_bars(symbol, start_date, end_date)
    if not data:
        logger.error("No data found for symbol %s", symbol)
        return None

    capital = initial_capital
    trades = []
    threshold = 0.01  # Example: 1% intraday move triggers a trade

    for bar in data:
        open_price = bar['o']
        close_price = bar['c']
        daily_return = (close_price - open_price) / open_price

        if daily_return > threshold:
            # Simulate trade: buy at open, sell at close.
            allocation = capital * allocation_limit
            qty = allocation / open_price
            trade_profit = qty * (close_price - open_price)
            capital += trade_profit
            trades.append({
                'date': bar['t'],
                'open': open_price,
                'close': close_price,
                'qty': qty,
                'profit': trade_profit
            })

    performance = {
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital,
        'num_trades': len(trades),
        'trades': trades
    }
    logger.info("Backtest complete for %s. Final capital: %.2f, Total return: %.2f%%, Trades: %d",
                symbol, capital, performance['total_return'] * 100, len(trades))
    return performance
