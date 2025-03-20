
# options_trading_bot.py
import asyncio
import logging
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt
from options_integration import evaluate_option_strategy, evaluate_options_for_multiple_tickers

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
    
    # Prompt for expiration; if provided, bot will use it, otherwise will choose automatically.
    expiry = Prompt.ask("Enter desired expiry (YYYY-MM-DD) (or leave blank for automatic selection)", default="")
    
    # No strike prompt now – strikes will be auto‐selected.
    
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

    # Build base trade details template – only expiration is provided (if any); strikes will be determined automatically.
    base_trade_details = {
        "expiry": expiry,
        "option_type": "call",  # default for long options; evaluation functions adjust as needed
        "position": "long",     # default for long
    }
    
    # Set strategy in base trade details for each evaluation.
    # (If no additional parameters are provided, the evaluation functions auto-select strikes.)
    if "long" in styles:
        base_trade_details["strategy"] = "long"
    elif "credit_spread" in styles:
        base_trade_details["strategy"] = "credit_spread"
    elif "debit_spread" in styles:
        base_trade_details["strategy"] = "debit_spread"
    elif "iron_condor" in styles:
        base_trade_details["strategy"] = "iron_condor"
    
    # Evaluate options for each style and each ticker.
    results = {}
    table = Table(title="Options Evaluation Results", show_lines=True)
    table.add_column("Ticker", style="bold green")
    table.add_column("Style", style="cyan")
    table.add_column("Metric", style="magenta")
    table.add_column("Result", style="yellow")
    
    for style in styles:
        trade_details = base_trade_details.copy()
        trade_details["strategy"] = style
        evaluations = evaluate_options_for_multiple_tickers(tickers, trade_details)
        results[style] = evaluations
        for ticker, result in evaluations.items():
            if "error" in result:
                metric = "Error"
                res_str = result["error"]
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
            table.add_row(ticker, style, metric, res_str)
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

