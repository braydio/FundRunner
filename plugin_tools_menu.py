# CLI hooks for plugin testing (Minimal Version)

from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
import pandas as pd

from plugins.plot_trades import plot_trades
from plugins.portfolio_optimizer import optimize_portfolio
from plugins.sentiment_finbert import analyze_sentiment

console = Console()


def plugin_tools_menu():
    while True:
        console.print("\n[bold cyan]PLUGIN TEST MENU[/bold cyan]")
        console.print("[1] Plot Trades")
        console.print("[2] Optimize Portfolio")
        console.print("[3] Analyze Sentiment")
        console.print("[0] Return to Main Menu")

        choice = Prompt.ask("Select", choices=["0", "1", "2", "3"])

        if choice == "1":
            # Simulated data
            dates = pd.date_range("2024-01-01", periods=5)
            df = pd.DataFrame(
                {
                    "open": [100, 102, 104, 106, 108],
                    "high": [101, 103, 105, 107, 109],
                    "low": [99, 101, 103, 105, 107],
                    "close": [101, 104, 103, 108, 110],
                    "volume": [1000] * 5,
                },
                index=dates,
            )
            trades = [{"date": dates[i], "profit": (i + 1) * 10} for i in range(5)]
            plot_trades(df, trades)

        elif choice == "2":
            prices = pd.DataFrame(
                {
                    "AAPL": [150, 152, 153, 151, 155],
                    "MSFT": [300, 305, 310, 308, 307],
                    "TSLA": [700, 710, 720, 715, 730],
                }
            )
            weights = optimize_portfolio(prices)
            console.print(Panel.fit(str(weights), title="Optimized Weights"))

        elif choice == "3":
            text = Prompt.ask("Enter text to analyze")
            sentiment = analyze_sentiment(text)
            console.print(Panel.fit(str(sentiment), title="Sentiment Scores"))

        elif choice == "0":
            break
