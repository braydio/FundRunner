# main.py

import sys
import asyncio
import json
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

from alpaca.trading_bot import TradingBot
from alpaca.portfolio_manager import PortfolioManager
from alpaca.trade_manager import TradeManager
from alpaca.watchlist_manager import WatchlistManager
from options_trading_bot import run_options_analysis
from alpaca.llm_vetter import LLMVetter
from config import SIMULATION_MODE, SIMULATED_STARTING_CASH

console = Console()


class FundRunnerCLI:
    def __init__(self):
        self.bot = TradingBot(
            auto_confirm=False, vet_trade_logic=True, vetter_vendor="local"
        )
        self.portfolio = PortfolioManager()
        self.trader = TradeManager()
        self.watchlist = WatchlistManager()
        self.vetter = LLMVetter()

    def extract(self, obj, field):
        return (
            obj.get(field, "n/a")
            if isinstance(obj, dict)
            else getattr(obj, field, "n/a")
        )

    def save_snapshot(self):
        """Capture account and portfolio state to a local JSON snapshot."""
        try:
            data = {
                "account": self.portfolio.view_account(),
                "positions": self.portfolio.view_positions(),
            }
            data["portfolio_status"] = self.view_positions(render=False)
            with open("portfolio_snapshot.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            console.print(f"[red]Error saving snapshot: {e}[/red]")

    def print_menu(self):
        """Render the main user menu and save current snapshot state."""
        console.clear()
        self.save_snapshot()
        panel_text = (
            "\n[bold blue]Unified Trading App[/bold blue]\n\n"
            "[yellow]1.[/yellow] View Account Info\n"
            "[yellow]2.[/yellow] View Portfolio Positions\n"
            "[yellow]3.[/yellow] Enter Trade\n"
            "[yellow]4.[/yellow] View Open Orders\n"
            "[yellow]5.[/yellow] Manage Watchlist\n"
            "[yellow]6.[/yellow] Ask Advisor\n"
            "[yellow]7.[/yellow] Run Trading Bot\n"
            "[yellow]8.[/yellow] Watchlist View\n"
            "[yellow]9.[/yellow] Run Options Session\n"
            "[yellow]0.[/yellow] Exit\n"
        )
        console.print(
            Panel.fit(
                panel_text, title="[bold red]Main Menu[/bold red]", border_style="blue"
            )
        )

    def view_account_info(self):
        """Display core account financials and simulated P/L."""
        try:
            acct = self.portfolio.view_account()
            cash = self.extract(acct, "cash")
            bp = self.extract(acct, "buying_power")
            eq = self.extract(acct, "equity")
            pv = self.extract(acct, "portfolio_value")
            pl = float(cash) - SIMULATED_STARTING_CASH if SIMULATION_MODE else 0.0
            panel_text = (
                f"[green]Cash:[/green] {cash}\n"
                f"[cyan]Buying Power:[/cyan] {bp}\n"
                f"[magenta]Equity:[/magenta] {eq}\n"
                f"[yellow]Portfolio Value:[/yellow] {pv}\n"
                f"[red]Overall P/L:[/red] {pl:.2f}"
            )
            console.print(
                Panel.fit(
                    panel_text, title="[bold]Account Info[/bold]", border_style="green"
                )
            )
        except Exception as e:
            console.print(f"[red]Error retrieving account info: {e}[/red]")

    def view_positions(self, render=True):
        """Display and optionally return table of active portfolio positions."""
        try:
            positions = self.portfolio.view_positions()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            table = Table(
                title=f"Portfolio Positions as of {timestamp}", style="bold blue"
            )
            for col in [
                "Symbol",
                "Qty",
                "Avg Entry",
                "Current Price",
                "$ P/L",
                "% P/L",
            ]:
                table.add_column(col, justify="right")
            data_out = []
            for pos in positions:
                try:
                    sym = pos.get("symbol", "n/a")
                    qty = float(pos.get("qty", 0))
                    ae = float(pos.get("avg_entry_price", 0))
                    cp = float(pos.get("current_price", 0))
                    dlr_pl = (cp - ae) * qty
                    pct_pl = ((cp - ae) / ae * 100) if ae else 0.0
                    row = [
                        sym,
                        str(int(qty)),
                        f"{ae:.2f}",
                        f"{cp:.2f}",
                        f"{dlr_pl:.2f}",
                        f"{pct_pl:.2f}%",
                    ]
                    table.add_row(*row)
                    data_out.append(row)
                except:
                    continue
            if render:
                console.print(table)
            return data_out
        except Exception as e:
            console.print(f"[red]Error retrieving positions: {e}[/red]")
            return []

    def enter_trade(self):
        """Submit a basic buy/sell order through the trade manager."""
        try:
            sym = Prompt.ask("Symbol").upper()
            qty = int(Prompt.ask("Qty"))
            side = Prompt.ask("Buy/Sell", choices=["buy", "sell"])
            otype = Prompt.ask("Order Type", default="market")
            tif = Prompt.ask("Time in Force", default="gtc")
            order = (
                self.trader.buy(sym, qty, otype, tif)
                if side == "buy"
                else self.trader.sell(sym, qty, otype, tif)
            )
            console.print(
                f"[green]Order submitted:[/green]\n{order}"
            ) if order else console.print("[red]Order failed.[/red]")
        except Exception as e:
            console.print(f"[red]Trade error: {e}[/red]")

    def view_open_orders(self):
        """Display all currently open market orders."""
        try:
            orders = self.trader.list_open_orders()
            if not orders:
                console.print("[red]No open orders.[/red]")
            else:
                for o in orders:
                    console.print(
                        f"ID: {o.id}, Sym: {o.symbol}, Side: {o.side}, Qty: {o.qty}, Status: {o.status}"
                    )
        except Exception as e:
            console.print(f"[red]Order list error: {e}[/red]")

    def manage_watchlist(self):
        """Simple multi-action watchlist CRUD interface."""
        action = Prompt.ask(
            "[1] List [2] Create [3] Add [4] Delete", choices=["1", "2", "3", "4"]
        )
        try:
            if action == "1":
                for wl in self.watchlist.list_watchlists():
                    console.print(
                        f"[green]{wl.name}[/green] ({wl.id}): {','.join(wl.symbols)}"
                    )
            elif action == "2":
                name = Prompt.ask("Watchlist name")
                syms = Prompt.ask("Symbols (comma-separated)").split(",")
                wl = self.watchlist.create_watchlist(
                    name, [s.strip().upper() for s in syms]
                )
                console.print(f"[green]Created: {wl.name}[/green]")
            elif action == "3":
                wid = Prompt.ask("Watchlist ID")
                sym = Prompt.ask("Symbol").upper()
                self.watchlist.add_to_watchlist(wid, sym)
                console.print(f"[green]Added {sym} to {wid}[/green]")
            elif action == "4":
                wid = Prompt.ask("Watchlist ID to delete")
                self.watchlist.delete_watchlist(wid)
                console.print(f"[red]Deleted watchlist {wid}[/red]")
        except Exception as e:
            console.print(f"[red]Watchlist error: {e}[/red]")

    def get_trading_advice(self):
        """Query GPT-based advisor for market input."""
        from llm.gpt_client import ask_gpt

        prompt = Prompt.ask("Enter trading question")
        try:
            response = ask_gpt(prompt)
            console.print(
                Panel.fit(
                    response or "No response.", title="[bold red]Advice[/bold red]"
                )
            )
        except Exception as e:
            console.print(f"[red]LLM error: {e}[/red]")

    def run_trading_bot(self):
        """Launch the standard trading bot."""
        syms = Prompt.ask("Symbols (comma-separated)", default="AAPL,TSLA")
        symbols = [s.strip().upper() for s in syms.split(",")]
        try:
            asyncio.run(self.bot.run(symbols if symbols else None))
        except Exception as e:
            console.print(f"[red]Bot error: {e}[/red]")

    def run_options_session(self):
        """Run the options trading bot logic."""
        try:
            asyncio.run(run_options_analysis())
        except Exception as e:
            console.print(f"[red]Options error: {e}[/red]")

    def launch_watchlist_view(self):
        """Start the rich UI for live watchlist data."""
        try:
            watchlist_view_main()
        except Exception as e:
            console.print(f"[red]Watchlist view error: {e}[/red]")

    def run(self):
        """Main CLI application loop."""
        while True:
            self.print_menu()
            choice = Prompt.ask("Select", choices=[str(i) for i in range(10)])
            if choice == "1":
                self.view_account_info()
            elif choice == "2":
                self.view_positions()
            elif choice == "3":
                self.enter_trade()
            elif choice == "4":
                self.view_open_orders()
            elif choice == "5":
                self.manage_watchlist()
            elif choice == "6":
                self.get_trading_advice()
            elif choice == "7":
                self.run_trading_bot()
            elif choice == "8":
                self.launch_watchlist_view()
            elif choice == "9":
                self.run_options_session()
            elif choice == "0":
                console.print("[red]Exiting.[/red]")
                sys.exit(0)
            Prompt.ask("Press Enter to return to menu")


if __name__ == "__main__":
    FundRunnerCLI().run()
