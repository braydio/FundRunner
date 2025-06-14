
# cli.py
import sys
import asyncio
import json
import os
from datetime import datetime  # <-- Added import for timestamps
from alpaca.trade_manager import TradeManager
from alpaca.portfolio_manager import PortfolioManager
from alpaca.watchlist_manager import WatchlistManager
from alpaca.trading_bot import TradingBot
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from config import SIMULATED_STARTING_CASH, SIMULATION_MODE, MICRO_MODE

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
            positions = self.portfolio_manager.view_positions()
            # Compute overall P/L from positions (sum of (current_price - avg_entry)*qty)
            overall_pl = 0.0
            for pos in positions:
                avg_entry = pos.get('avg_entry_price')
                current_price = pos.get('current_price')
                qty = pos.get('qty', 0)
                if avg_entry is not None and current_price is not None:
                    overall_pl += (current_price - avg_entry) * qty
            # If in simulation mode, include cash change relative to SIMULATED_STARTING_CASH
            if SIMULATION_MODE:
                cash = self.extract_account_field(account, 'cash')
                try:
                    overall_pl += float(cash) - SIMULATED_STARTING_CASH
                except Exception:
                    pass

            info_panel = Panel.fit(
                f"[bold green]Cash:[/bold green] {self.extract_account_field(account, 'cash')}\n"
                f"[bold cyan]Buying Power:[/bold cyan] {self.extract_account_field(account, 'buying_power')}\n"
                f"[bold magenta]Equity:[/bold magenta] {self.extract_account_field(account, 'equity')}\n"
                f"[bold yellow]Portfolio Value:[/bold yellow] {self.extract_account_field(account, 'portfolio_value')}\n"
                f"[bold red]Overall P/L:[/bold red] {overall_pl:.2f}",
                title="[bold red]Account Information[/bold red]",
                border_style="green"
            )
            self.console.print(info_panel)
        except Exception as e:
            self.console.print(f"[red]Error retrieving account info: {e}[/red]")

    def show_portfolio_status(self):
        """
        Displays the portfolio status in a table along with the current date/time in the title.
        Also computes overall P/L from all positions.
        """
        try:
            account = self.portfolio_manager.view_account()
            positions = self.portfolio_manager.view_positions()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # <-- Get current date/time
            table = Table(
                title=f"Portfolio Status (as of {timestamp})",  # <-- Include timestamp in the title
                style="bold green",
                show_edge=True
            )
            table.add_column("Symbol", justify="center", style="green")
            table.add_column("Qty", justify="right", style="cyan")
            table.add_column("Avg Entry", justify="right", style="magenta")
            table.add_column("Current Price", justify="right", style="yellow")
            table.add_column("$ P/L", justify="right", style="red")

            overall_pl = 0.0
            for pos in positions:
                symbol = str(pos.get('symbol', 'N/A'))
                qty = pos.get('qty', 0)
                avg_entry = pos.get('avg_entry_price', None)
                current_price = pos.get('current_price', None)
                if avg_entry is not None and current_price is not None:
                    dollar_pl = (current_price - avg_entry) * qty
                    overall_pl += dollar_pl
                    avg_entry_str = f"{avg_entry:.2f}"
                    current_price_str = f"{current_price:.2f}"
                    dollar_pl_str = f"{dollar_pl:.2f}"
                else:
                    avg_entry_str = "N/A"
                    current_price_str = "N/A"
                    dollar_pl_str = "N/A"

                table.add_row(symbol, str(qty), avg_entry_str, current_price_str, dollar_pl_str)
            # Append overall P/L as a separate row or print after the table
            self.console.print(table)
            self.console.print(f"[bold red]Overall Account P/L: {overall_pl:.2f}[/bold red]")
            return {"account": account, "positions": positions}
        except Exception as e:
            self.console.print(f"[red]Error retrieving portfolio status: {e}[/red]")
            return {}

    def save_portfolio_snapshot(self):
        snapshot = {}
        try:
            account = self.portfolio_manager.view_account()
            positions = self.portfolio_manager.view_positions()
            snapshot["account"] = account
            snapshot["positions"] = positions
            snapshot["portfolio_status"] = self.show_portfolio_status()
            with open("portfolio_snapshot.json", "w") as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            self.console.print(f"[red]Error saving portfolio snapshot: {e}[/red]")

    def print_menu(self):
        self.console.clear()
        self.save_portfolio_snapshot()  # Save snapshot each time main menu is rendered
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
        """
        Displays positions in a table along with the current date/time in the title.
        """
        try:
            positions = self.portfolio_manager.view_positions()
            if not positions:
                self.console.print("[red]No positions found.[/red]")
            else:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # <-- Get current date/time
                table = Table(
                    title=f"Portfolio Positions & P/L (as of {timestamp})",  # <-- Include timestamp in the title
                    style="bold blue"
                )
                table.add_column("Symbol", justify="center", style="green")
                table.add_column("Qty", justify="right", style="cyan")
                table.add_column("Market Value", justify="right", style="blue")
                table.add_column("Avg Entry", justify="right", style="magenta")
                table.add_column("Current Price", justify="right", style="yellow")
                table.add_column("$ P/L", justify="right", style="red")
                table.add_column("% P/L", justify="right", style="red")

                for pos in positions:
                    symbol = str(pos.get('symbol', 'N/A'))
                    qty = pos.get('qty', 0)
                    market_val = pos.get('market_value', 'N/A')
                    unrealized_pl = getattr(pos, 'unrealized_pl', 'N/A')
                    if unrealized_pl is not None:
                        unrealized_pl_str = f"${unrealized_pl}"
                    avg_entry = pos.get('avg_entry_price', None)
                    current_price = pos.get('current_price', None)

                    # Initialize placeholders
                    avg_entry_str = "N/A"
                    current_price_str = "N/A"
                    dollar_pl_str = "N/A"
                    pct_pl_str = "N/A"

                    if qty is not None and current_price is not None:
                        try:
                            market_val_calc = float(current_price) * float(qty)
                            market_val_str = f"${market_val_calc:.2f}"
                        except:
                            market_val_str = "N/A"
                    else:
                        market_val_str = "N/A"

                    if avg_entry is not None and current_price is not None:
                        try:
                            avg_entry_val = float(avg_entry)
                            current_price_val = float(current_price)
                            dollar_pl = (current_price_val - avg_entry_val) * float(qty)
                            avg_entry_str = f"{avg_entry_val:.2f}"
                            current_price_str = f"{current_price_val:.2f}"
                            dollar_pl_str = f"${dollar_pl:.2f}"
                            pct_pl = 0.0
                            if avg_entry_val != 0:
                                pct_pl = (current_price_val - avg_entry_val) / avg_entry_val * 100
                            pct_pl_str = f"{pct_pl:.2f}%"
                        except:
                            pass

                    table.add_row(symbol, str(qty), market_val_str,  avg_entry_str, current_price_str, dollar_pl_str, pct_pl_str)

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
        """Launch the trading bot with optional symbol overrides."""
        symbols_input = Prompt.ask("Enter symbols (comma separated) for the trading bot (or press Enter to use default)")
        symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
        try:
            bot = TradingBot(
                auto_confirm=False,
                vet_trade_logic=True,
                vetter_vendor="local",
                micro_mode=MICRO_MODE,
            )
            asyncio.run(bot.run(symbols if symbols else None))
        except Exception as e:
            self.console.print(f"[red]Error running trading bot: {e}[/red]")

    def run_options_trading_session(self):
        try:
            from options_trading_bot import run_options_analysis
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

