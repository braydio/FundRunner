# options_trading_bot.py
import asyncio
import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from options_integration import evaluate_option_strategy, evaluate_options_for_multiple_tickers, analyze_sentiment

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def monitor_options_positions():
    console = Console()
    while True:
        # Placeholder for monitoring open options positions
        await asyncio.sleep(60)

async def run_options_analysis():
    console = Console()
    console.print("[bold blue]Options Trading Analysis Session[/bold blue]")
    
    # Prompt for multiple underlying tickers (default 3)
    tickers_input = Prompt.ask("Enter underlying tickers (comma separated)", default="AAPL,MSFT,GOOGL")
    tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]
    
    # Date: default to automatic selection (which now picks Friday at least 4 weeks out)
    expiry = Prompt.ask("Enter desired expiry (YYYY-MM-DD) (or leave blank for automatic Friday selection)", default="")
    
    # Determine sentiment from recent activity for each ticker and prompt for override
    sentiments = {}
    for ticker in tickers:
        default_sent = analyze_sentiment(ticker)
        override = Prompt.ask(f"Default sentiment for {ticker} is {default_sent}. Override? (bullish/bearish/neutral)", default=default_sent)
        sentiments[ticker] = override.lower()
    
    # Prompt for options trade style
    console.print("Select options trade style:")
    console.print("1. Long")
    console.print("2. Credit Spread")
    console.print("3. Debit Spread")
    console.print("4. Iron Condor")
    style_choice = Prompt.ask("Enter choice (1-4, or press Enter to scan all)", default="")
    if style_choice == "":
        styles = ["long", "credit_spread", "debit_spread", "iron_condor"]
    else:
        mapping = {
            "1": "long",
            "2": "credit_spread",
            "3": "debit_spread",
            "4": "iron_condor"
        }
        styles = [mapping.get(style_choice, "long")]

    # Build base trade details template – only expiration is provided; strikes auto-selected.
    base_trade_details = {
        "expiry": expiry,
        "option_type": "call",  # default; later override based on sentiment for long trades
        "position": "long",     # default for long
    }
    
    # For each ticker, if sentiment is bearish and strategy is long, change option_type to put.
    # We'll incorporate that logic during evaluation.
    
    # Evaluate options for each style and each ticker.
    results = {}
    table = Table(title="Options Evaluation Results", show_lines=True)
    table.add_column("Ticker", style="bold green")
    table.add_column("Style", style="cyan")
    table.add_column("Metric", style="magenta")
    table.add_column("Result", style="yellow")
    table.add_column("Leg Details", style="blue")
    
    for style in styles:
        # Copy base details and set strategy
        trade_details = base_trade_details.copy()
        trade_details["strategy"] = style
        # For long options, adjust option type based on sentiment (default bullish->call, bearish->put)
        for ticker in tickers:
            if style == "long":
                sentiment = sentiments.get(ticker, "bullish")
                trade_details["option_type"] = "call" if sentiment == "bullish" else "put"
            # Evaluate for each ticker independently
            evals = evaluate_options_for_multiple_tickers([ticker], trade_details)
            results.setdefault(style, {})[ticker] = evals.get(ticker, {})
            result = evals.get(ticker, {})
            if "error" in result:
                metric = "Error"
                res_str = result["error"]
                leg_str = "N/A"
            else:
                if style == "long":
                    metric = "Profit Ratio"
                    res_str = f"{result.get('profit_ratio', 'N/A'):.2f}"
                elif style in ["credit_spread", "debit_spread", "iron_condor"]:
                    metric = "Risk Reward"
                    res_str = f"{result.get('risk_reward_ratio', 'N/A'):.2f}"
                else:
                    metric = "N/A"
                    res_str = "N/A"
                # For spreads, summarize leg details (e.g., strikes and delta for each leg)
                if style == "credit_spread":
                    leg_info = result.get("leg_details", {})
                    leg_str = f"Short@{leg_info.get('short', {}).get('strike', 'N/A')} (δ={leg_info.get('short', {}).get('greeks', {}).get('delta', 'N/A'):.2f}), Long@{leg_info.get('long', {}).get('strike', 'N/A')} (δ={leg_info.get('long', {}).get('greeks', {}).get('delta', 'N/A'):.2f})"
                elif style == "debit_spread":
                    leg_info = result.get("leg_details", {})
                    leg_str = f"Buy@{leg_info.get('buy', {}).get('strike', 'N/A')} (δ={leg_info.get('buy', {}).get('greeks', {}).get('delta', 'N/A'):.2f}), Sell@{leg_info.get('sell', {}).get('strike', 'N/A')} (δ={leg_info.get('sell', {}).get('greeks', {}).get('delta', 'N/A'):.2f})"
                elif style == "iron_condor":
                    leg_info = result.get("leg_details", {})
                    leg_str = (f"SC@{leg_info.get('short_call', {}).get('strike', 'N/A')} (δ={leg_info.get('short_call', {}).get('greeks', {}).get('delta', 'N/A'):.2f}), "
                               f"LC@{leg_info.get('long_call', {}).get('strike', 'N/A')} (δ={leg_info.get('long_call', {}).get('greeks', {}).get('delta', 'N/A'):.2f}), "
                               f"SP@{leg_info.get('short_put', {}).get('strike', 'N/A')} (δ={leg_info.get('short_put', {}).get('greeks', {}).get('delta', 'N/A'):.2f}), "
                               f"LP@{leg_info.get('long_put', {}).get('strike', 'N/A')} (δ={leg_info.get('long_put', {}).get('greeks', {}).get('delta', 'N/A'):.2f})")
                else:
                    leg_str = "N/A"
            table.add_row(ticker, style, metric, res_str, leg_str)
            console.print(f"Evaluated {style} for {ticker}: {result}")
            await asyncio.sleep(1)
    console.print(table)
    
    exec_choice = Prompt.ask("Simulate executing one of these trades? (y/n)", default="n")
    if exec_choice.lower() == "y":
        chosen_ticker = Prompt.ask("Enter the ticker to execute")
        chosen_style = Prompt.ask("Enter the style to execute", choices=styles)
        evals = evaluate_options_for_multiple_tickers([chosen_ticker], base_trade_details)
        result = evals.get(chosen_ticker, {})
        if result and "error" not in result:
            console.print(f"[green]Simulated execution for {chosen_ticker} with style {chosen_style}: {result}[/green]")
        else:
            console.print(f"[red]Execution simulation failed for {chosen_ticker}: {result.get('error', 'Unknown error')}[/red]")
    
    cont_choice = Prompt.ask("Run another scan? (y/n)", default="y")
    if cont_choice.lower() == "y":
        await run_options_analysis()
    else:
        console.print("[bold red]Exiting Options Trading Analysis Session.[/bold red]")
        return

async def main():
    monitor_task = asyncio.create_task(monitor_options_positions())
    await run_options_analysis()
    monitor_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())

