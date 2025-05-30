# Determined that switching the data source from yfinance to Alpacca for the backester module was prudent

New Backtesting Logic Scaffold follows:

```
from alpaca.api_client import AlpacaAPIClient  # adjust import if needed
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def run_backtest(symbol: str, start_date: str, end_date: str,
                 initial_capital: float = 100_000,
                 allocation_limit: float = 0.05,
                 threshold: float = 0.01):
    """
    Run a backtest using Alpaca market data.

    Strategy:
    - If intraday return > threshold, buy at open, sell at close
    - Allocate a portion of capital each time

    Returns:
    - Dict with performance summary
    """
    client = AlpacaAPIClient()
    try:
        # Must return list of dicts with 't', 'o', 'c' keys
        data = client.get_historical_bars(symbol, start_date, end_date, timeframe="1Day")
    except Exception as e:
        logger.error("Failed to fetch Alpaca data: %s", str(e))
        return None

    if not data:
        logger.warning("No data for symbol %s", symbol)
        return None

    trades = []
    capital = initial_capital

    for bar in data:
        date = bar['t']
        open_price = bar['o']
        close_price = bar['c']
        daily_return = (close_price - open_price) / open_price

        if daily_return > threshold:
            trade_capital = capital * allocation_limit
            qty = trade_capital / open_price
            profit = qty * (close_price - open_price)
            capital += profit

            trades.append({
                'date': date,
                'open': open_price,
                'close': close_price,
                'qty': qty,
                'profit': profit
            })

    performance = {
        'final_capital': capital,
        'total_return': (capital - initial_capital) / initial_capital,
        'num_trades': len(trades),
        'trades': trades
    }

    logger.info("Backtest complete: Final $%.2f | Return: %.2f%% | Trades: %d",
                capital, performance['total_return'] * 100, len(trades))

    return performance

```

<https://github.com/wilsonfreitas/awesome-quant>
