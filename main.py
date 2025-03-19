
# cli.py
import sys
import asyncio
from alpaca.trade_manager import TradeManager
from alpaca.portfolio_manager import PortfolioManager
from alpaca.watchlist_manager import WatchlistManager
from alpaca.trading_bot import TradingBot
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

class CLI:
    def __init__(self):
        self.trade_manager = TradeManager()
        self.portfolio_manager = PortfolioManager()
        self.watchlist_manager = WatchlistManager()
        self.console = Console()

    def extract_account_field(self, account, field):
        return account.get(field, 'N/A') if isinstance(account, dict) else getattr(account, field, 'N/A')


    def view_account_info(self):
        try:
            account = self.portfolio_manager.view_account()
            info_panel = Panel.fit(
                f"[bold green]Cash:[/bold green] {self.extract_account_field(account, 'cash')}\n"
                f"[bold cyan]Buying Power:[/bold cyan] {self.extract_account_field(account, 'buying_power')}\n"
                f"[bold magenta]Equity:[/bold magenta] {self.extract_account_field(account, 'equity')}\n"
                f"[bold yellow]Portfolio Value:[/bold yellow] {self.extract_account_field(account, 'portfolio_value')}",
                title="[bold red]Account Information[/bold red]",
                border_style="green"
            )
            self.console.print(info_panel)
        except Exception as e:
            self.console.print(f"[red]Error retrieving account info: {e}[/red]")

    def show_portfolio_status(self):
        try:
            account = self.portfolio_manager.view_account()
            table = Table(title="Portfolio Status", style="bold green", show_edge=True)
            table.add_column("Cash", justify="right", style="green")
            table.add_column("Buying Power", justify="right", style="cyan")
            table.add_column("Equity", justify="right", style="magenta")
            table.add_column("Portfolio Value", justify="right", style="yellow")
            table.add_row(
                str(self.extract_account_field(account, 'cash')),
                str(self.extract_account_field(account, 'buying_power')),
                str(self.extract_account_field(account, 'equity')),
                str(self.extract_account_field(account, 'portfolio_value'))
            )
            self.console.print(table)
        except Exception as e:
            self.console.print(f"[red]Error retrieving portfolio status: {e}[/red]")

    def print_menu(self):
        self.console.clear()
        self.show_portfolio_status()
        menu_text = (
            "\n[bold blue]Unified Trading App[/bold blue]\n\n"
            "[bold yellow]1.[/bold yellow] View Account Information\n"
            "[bold yellow]2.[/bold yellow] View Portfolio Positions & P/L\n"
            "[bold yellow]3.[/bold yellow] Enter a Trade (Buy/Sell)\n"
            "[bold yellow]4.[/bold yellow] View Open Orders\n"
            "[bold yellow]5.[/bold yellow] Manage Watchlist\n"
            "[bold yellow]6.[/bold yellow] RAG Agent - Ask Advisor\n"
            "[bold yellow]7.[/bold yellow] Run Trading Bot\n"
            "[bold yellow]8.[/bold yellow] Watchlist View\n"
            "[bold yellow]9.[/bold yellow] Run Options Trading Evaluation Session\n"
            "[bold yellow]0.[/bold yellow] Exit\n"
        )
        menu_panel = Panel.fit(menu_text, title="[bold red]Main Menu[/bold red]", border_style="blue")
        self.console.print(menu_panel)

    def manage_watchlist_menu(self):
        while True:
            self.console.print("\n[bold blue]--- Watchlist Management ---[/bold blue]")
            self.console.print("[bold yellow]1.[/bold yellow] List Watchlists")
            self.console.print("[bold yellow]2.[/bold yellow] Create a Watchlist")
            self.console.print("[bold yellow]3.[/bold yellow] Add Symbol to Watchlist")
            self.console.print("[bold yellow]4.[/bold yellow] Remove Symbol from Watchlist")
            self.console.print("[bold yellow]5.[/bold yellow] View a Watchlist")
            self.console.print("[bold yellow]6.[/bold yellow] Delete a Watchlist")
            self.console.print("[bold yellow]7.[/bold yellow] Back to Main Menu")
            choice = Prompt.ask("Select an option", default="7")
            if choice == "1":
                try:
                    watchlists = self.watchlist_manager.list_watchlists()
                    if not watchlists:
                        self.console.print("[red]No watchlists found.[/red]")
                    else:
                        for wl in watchlists:
                            symbols = ', '.join(wl.symbols) if hasattr(wl, 'symbols') else "N/A"
                            self.console.print(f"ID: [bold]{wl.id}[/bold], Name: [green]{wl.name}[/green], Symbols: [cyan]{symbols}[/cyan]")
                except Exception as e:
                    self.console.print(f"[red]Error listing watchlists: {e}[/red]")
            elif choice == "2":
                name = Prompt.ask("Enter watchlist name")
                symbols_input = Prompt.ask("Enter symbols (comma separated)")
                symbols = [s.strip().upper() for s in symbols_input.split(',')]
                try:
                    wl = self.watchlist_manager.create_watchlist(name, symbols)
                    self.console.print(f"[green]Created watchlist '{wl.name}' with ID: {wl.id}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Error creating watchlist: {e}[/red]")
            elif choice == "3":
                wl_id = Prompt.ask("Enter watchlist ID (or name)")
                symbol = Prompt.ask("Enter symbol to add").upper().strip()
                try:
                    self.watchlist_manager.add_to_watchlist(wl_id, symbol)
                    self.console.print(f"[green]Added {symbol} to watchlist {wl_id}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Error adding symbol: {e}[/red]")
            elif choice == "4":
                wl_id = Prompt.ask("Enter watchlist ID")
                symbol = Prompt.ask("Enter symbol to remove").upper().strip()
                try:
                    self.watchlist_manager.remove_from_watchlist(wl_id, symbol)
                    self.console.print(f"[green]Removed {symbol} from watchlist {wl_id}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Error removing symbol: {e}[/red]")
            elif choice == "5":
                wl_id = Prompt.ask("Enter watchlist ID")
                try:
                    watchlist = self.watchlist_manager.get_watchlist(wl_id)
                    assets = watchlist.assets if hasattr(watchlist, 'assets') else "N/A"
                    self.console.print(f"Watchlist '[green]{watchlist.name}[/green]': {assets}")
                except Exception as e:
                    self.console.print(f"[red]Error retrieving watchlist: {e}[/red]")
            elif choice == "6":
                wl_id = Prompt.ask("Enter watchlist ID to delete")
                try:
                    self.watchlist_manager.delete_watchlist(wl_id)
                    self.console.print(f"[green]Deleted watchlist with ID: {wl_id}[/green]")
                except Exception as e:
                    self.console.print(f"[red]Error deleting watchlist: {e}[/red]")
            elif choice == "7":
                break
            else:
                self.console.print("[red]Invalid option. Try again.[/red]")

    def enter_trade(self):
        symbol = Prompt.ask("Enter symbol").upper().strip()
        qty_str = Prompt.ask("Enter quantity")
        try:
            qty = int(qty_str)
        except ValueError:
            self.console.print("[red]Quantity must be an integer.[/red]")
            return
        side = Prompt.ask("Enter side (buy/sell)").lower().strip()
        if side not in ['buy', 'sell']:
            self.console.print("[red]Side must be either 'buy' or 'sell'.[/red]")
            return
        order_type = Prompt.ask("Enter order type (market/limit)").lower().strip()
        time_in_force = Prompt.ask("Enter time in force (gtc, day, etc.)").lower().strip()

        try:
            if side == 'buy':
                order = self.trade_manager.buy(symbol, qty, order_type, time_in_force)
            elif side == 'sell':
                order = self.trade_manager.sell(symbol, qty, order_type, time_in_force)
            if order:
                self.console.print(f"[green]Order submitted:[/green]\n{order}")
            else:
                self.console.print("[red]Order submission failed.[/red]")
        except Exception as e:
            self.console.print(f"[red]Error submitting trade: {e}[/red]")

    def view_open_orders(self):
        try:
            orders = self.trade_manager.list_open_orders()
            if not orders:
                self.console.print("[red]No open orders.[/red]")
            else:
                self.console.print("\n[bold blue]--- Open Orders ---[/bold blue]")
                for order in orders:
                    self.console.print(f"ID: [bold]{order.id}[/bold], Symbol: [green]{order.symbol}[/green], "
                                       f"Side: [cyan]{order.side}[/cyan], Qty: [magenta]{order.qty}[/magenta], "
                                       f"Status: [yellow]{order.status}[/yellow]")
        except Exception as e:
            self.console.print(f"[red]Error retrieving open orders: {e}[/red]")

    def view_positions(self):
        try:
            positions = self.portfolio_manager.view_positions()
            if not positions:
                self.console.print("[red]No positions found.[/red]")
            else:
                table = Table(title="Portfolio Positions & P/L", style="bold blue")
                table.add_column("Symbol", justify="center", style="green")
                table.add_column("Qty", justify="right", style="cyan")
                table.add_column("Market Value", justify="right", style="magenta")
                table.add_column("Unrealized P/L %", justify="right", style="yellow")
                for pos in positions:
                    table.add_row(
                        str(pos.get('symbol', 'N/A')),
                        str(pos.get('qty', 'N/A')),
                        str(pos.get('market_value', 'N/A')),
                        f"{pos.get('unrealized_pl_percent', 'N/A'):.2f}%" 
                        if isinstance(pos.get('unrealized_pl_percent'), (float, int)) else 'N/A'
                    )
                self.console.print(table)
        except Exception as e:
            self.console.print(f"[red]Error retrieving positions: {e}[/red]")

    def get_trading_advice(self):
        prompt_text = Prompt.ask("Enter your prompt for trading advice")
        try:
            from chatgpt_advisor import get_account_overview
            advice = get_account_overview(prompt_text)
            advice_panel = Panel.fit(advice, title="[bold red]Trading Advice[/bold red]", border_style="blue")
            self.console.print(advice_panel)
        except Exception as e:
            self.console.print(f"[red]Error retrieving trading advice: {e}[/red]")

    def run_trading_bot(self):
        symbols_input = Prompt.ask("Enter symbols (comma separated) for the trading bot (or press Enter to use default)")
        symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
        try:
            bot = TradingBot(auto_confirm=False, vet_trade_logic=True, vetter_vendor="local")
            asyncio.run(bot.run(symbols if symbols else None))
        except Exception as e:
            self.console.print(f"[red]Error running trading bot: {e}[/red]")

    def run_options_trading_session(self):
        try:
            from options_integration import run_options_analysis
            asyncio.run(run_options_analysis())
        except Exception as e:
            self.console.print(f"[red]Error running options trading session: {e}[/red]")

    def launch_watchlist_view(self):
        try:
            from watchlist_view import main as watchlist_view_main
            watchlist_view_main()
        except Exception as e:
            self.console.print(f"[red]Error launching watchlist view: {e}[/red]")

    def run(self):
        while True:
            self.print_menu()
            choice = Prompt.ask("Select an option", choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"])
            if choice == "1":
                self.view_account_info()
            elif choice == "2":
                self.view_positions()
            elif choice == "3":
                self.enter_trade()
            elif choice == "4":
                self.view_open_orders()
            elif choice == "5":
                self.manage_watchlist_menu()
            elif choice == "6":
                self.get_trading_advice()
            elif choice == "7":
                self.run_trading_bot()
            elif choice == "8":
                self.launch_watchlist_view()
            elif choice == "9":
                self.run_options_trading_session()
            elif choice == "0":
                self.console.print("[bold red]Exiting the app.[/bold red]")
                sys.exit(0)
            else:
                self.console.print("[red]Invalid option. Please try again.[/red]")
            Prompt.ask("\nPress Enter to return to the Main Menu", default="")

if __name__ == "__main__":
    cli = CLI()
    cli.run()
# End cli.py


# Begin main.py
# main.py

# main.py
from cli import CLI

def main():
    app = CLI()
    app.run()


if __name__ == "__main__":
    main()

# End main.py


# Begin alpaca_bot.py
# alpaca_bot.py
import asyncio
from alpaca.trading_bot import TradingBot

async def main():
    # Define the list of symbols to evaluate
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    # Initialize the bot (set auto_confirm=False for manual confirmation)
    print(f"TradingBot loaded from {TradingBot.__module__}")
    bot = TradingBot(auto_confirm=False)
    
    # Optionally, get advice from ChatGPT before trading begins
    advice = bot.get_chatgpt_advice(
        "Please provide a review of the current account risk profile and suggest any adjustments."
    )
    print("ChatGPT Advisor:", advice)
    
    # Run the trading bot for the specified symbols
    await bot.run(symbols)

if __name__ == "__main__":
    asyncio.run(main())


# End alpaca_bot.py
