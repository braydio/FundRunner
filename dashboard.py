def display_open_orders(self):
    """Re-display all open orders."""
    try:
        orders = self.trader.list_open_orders()
        if not orders:
            console.print("[dim]No open orders.[/dim]")
            return
        table = Table(title="Open Orders", header_style="bold blue")
        table.add_column("ID")
        table.add_column("Symbol")
        table.add_column("Side")
        table.add_column("Qty", justify="right")
        table.add_column("Status")
        for o in orders:
            table.add_row(o.id, o.symbol, o.side, str(o.qty), o.status)
        console.print(table)
    except Exception as e:
        console.print(f"[red]Failed to fetch open orders: {e}[/red]")


def display_order_history(self):
    """Stub for future historical order log access."""
    console.print("[yellow]Order history integration coming soon.[/yellow]")


def view_account_info_menu(self):
    """Full Account Info panel with balance, orders, and submenu routing."""
    self.save_snapshot()
    try:
        # Account details
        acct = self.portfolio.view_account()
        cash = self.extract(acct, "cash")
        bp = self.extract(acct, "buying_power")
        eq = self.extract(acct, "equity")
        pv = self.extract(acct, "portfolio_value")
        pl = float(cash) - SIMULATED_STARTING_CASH if SIMULATION_MODE else 0.0

        # Display balance panel
        balance_panel = (
            f"[green]Cash:[/green] {cash}\n"
            f"[cyan]Buying Power:[/cyan] {bp}\n"
            f"[magenta]Equity:[/magenta] {eq}\n"
            f"[yellow]Portfolio Value:[/yellow] {pv}\n"
            f"[red]Overall P/L:[/red] {pl:.2f}"
        )
        console.print(
            Panel.fit(
                balance_panel,
                title="[bold]Balance Summary[/bold]",
                border_style="green",
            )
        )

        # Display open orders summary
        open_orders = self.trader.list_open_orders()
        if open_orders:
            table = Table(title="Open Orders", header_style="bold magenta")
            table.add_column("ID")
            table.add_column("Symbol")
            table.add_column("Side")
            table.add_column("Qty", justify="right")
            table.add_column("Status")
            for order in open_orders[:5]:  # Limit preview
                table.add_row(
                    getattr(order, "id", "n/a"),
                    getattr(order, "symbol", "n/a"),
                    getattr(order, "side", "n/a"),
                    str(getattr(order, "qty", "n/a")),
                    getattr(order, "status", "n/a"),
                )
            console.print(table)
        else:
            console.print("[dim]No open orders found.[/dim]")

        # Submenu
        while True:
            console.print("\n[bold cyan]Account Info Menu[/bold cyan]")
            console.print("[1] View Balance Only")
            console.print("[2] View Order History")
            console.print("[3] View Open Orders")
            console.print("[0] Return to Main Menu")
            choice = Prompt.ask("Select", choices=["0", "1", "2", "3"], default="0")
            if choice == "1":
                console.print(
                    Panel.fit(
                        balance_panel,
                        title="[bold]Balance Summary[/bold]",
                        border_style="green",
                    )
                )
            elif choice == "2":
                self.display_order_history()
            elif choice == "3":
                self.display_open_orders()
            elif choice == "0":
                break
    except Exception as e:
        console.print(f"[red]Account info error: {e}[/red]")


def manage_watchlist_menu(self):
    """Full-featured Watchlist Manager interface."""
    while True:
        console.print("\n[bold cyan]WATCHLIST MANAGER[/bold cyan]")
        console.print("[1] List All Watchlists")
        console.print("[2] Create New Watchlist")
        console.print("[3] Add Symbol to Watchlist")
        console.print("[4] Remove Symbol from Watchlist")
        console.print("[5] Delete Watchlist")
        console.print("[6] View Watchlist by ID")
        console.print("[0] Return to Main Menu")
        choice = Prompt.ask(
            "Select an option", choices=["0", "1", "2", "3", "4", "5", "6"]
        )

        try:
            if choice == "1":
                watchlists = self.watchlist.list_watchlists()
                if not watchlists:
                    console.print("[dim]No watchlists found.[/dim]")
                else:
                    for wl in watchlists:
                        console.print(
                            f"[green]{wl.name}[/green] ({wl.id}): {', '.join(getattr(wl, 'symbols', []))}"
                        )

            elif choice == "2":
                name = Prompt.ask("Enter new watchlist name")
                syms = Prompt.ask("Enter symbols (comma-separated)").split(",")
                wl = self.watchlist.create_watchlist(
                    name, [s.strip().upper() for s in syms]
                )
                console.print(f"[green]Created watchlist '{wl.name}'[/green]")

            elif choice == "3":
                wid = Prompt.ask("Enter Watchlist ID or name")
                sym = Prompt.ask("Enter symbol to add").strip().upper()
                self.watchlist.add_to_watchlist(wid, sym)
                console.print(f"[green]Added {sym} to {wid}[/green]")

            elif choice == "4":
                wid = Prompt.ask("Enter Watchlist ID or name")
                sym = Prompt.ask("Enter symbol to remove").strip().upper()
                self.watchlist.remove_from_watchlist(wid, sym)
                console.print(f"[yellow]Removed {sym} from {wid}[/yellow]")

            elif choice == "5":
                wid = Prompt.ask("Enter Watchlist ID to delete")
                self.watchlist.delete_watchlist(wid)
                console.print(f"[red]Deleted watchlist {wid}[/red]")

            elif choice == "6":
                wid = Prompt.ask("Enter Watchlist ID to view")
                wl = self.watchlist.get_watchlist(wid)
                symbols = getattr(wl, "symbols", [])
                console.print(f"[cyan]Watchlist: {wl.name}[/cyan]")
                console.print(", ".join(symbols) if symbols else "[dim]Empty[/dim]")

            elif choice == "0":
                break

        except Exception as e:
            console.print(f"[red]Watchlist error: {e}[/red]")


def trading_bot_menu(self):
    """Trading Bot Configuration & Launch Menu."""
    # Default settings
    symbols = ["AAPL", "TSLA"]
    auto_confirm = self.bot.auto_confirm
    vetting_enabled = self.bot.vet_trade_logic
    vetter_source = self.bot.vetter_vendor

    while True:
        console.print("\n[bold cyan]TRADING BOT MENU[/bold cyan]")
        console.print(f"[1] Set Target Symbols      (Current: {', '.join(symbols)})")
        console.print(
            f"[2] Toggle Auto-Confirm     (Current: {'On' if auto_confirm else 'Off'})"
        )
        console.print(f"[3] Set Vetting Source      (Current: {vetter_source})")
        console.print("[4] Review Strategy Settings")
        console.print("[5] Launch Trading Bot")
        console.print("[0] Return to Main Menu")

        choice = Prompt.ask("Select an option", choices=["0", "1", "2", "3", "4", "5"])

        if choice == "1":
            syms_input = Prompt.ask(
                "Enter symbols (comma-separated)", default="AAPL,TSLA"
            )
            symbols = [s.strip().upper() for s in syms_input.split(",")]

        elif choice == "2":
            auto_confirm = not auto_confirm
            console.print(
                f"[yellow]Auto-confirm now {'enabled' if auto_confirm else 'disabled'}.[/yellow]"
            )

        elif choice == "3":
            vetter_source = Prompt.ask(
                "Select vetter source",
                choices=["local", "openai", "none"],
                default="local",
            )
            vetting_enabled = vetter_source != "none"

        elif choice == "4":
            panel = Panel.fit(
                f"Symbols: [green]{', '.join(symbols)}[/green]\n"
                f"Auto-Confirm: [cyan]{'Enabled' if auto_confirm else 'Disabled'}[/cyan]\n"
                f"Vetting: [magenta]{vetter_source}[/magenta]",
                title="[bold blue]Bot Settings[/bold blue]",
                border_style="blue",
            )
            console.print(panel)

        elif choice == "5":
            try:
                bot = TradingBot(
                    auto_confirm=auto_confirm,
                    vet_trade_logic=vetting_enabled,
                    vetter_vendor=vetter_source,
                )
                console.print(
                    f"[green]Launching bot with: {', '.join(symbols)}[/green]"
                )
                asyncio.run(bot.run(symbols))
            except Exception as e:
                console.print(f"[red]Bot launch failed: {e}[/red]")

        elif choice == "0":
            break


def options_bot_menu(self):
    """Options Bot Configuration & Launch Menu."""
    mode = "Analysis"  # or Execution
    strategy = "Vertical Spreads"
    symbols = ["TSLA", "SPY"]

    while True:
        console.print("\n[bold cyan]OPTIONS BOT MENU[/bold cyan]")
        console.print(f"[1] Set Target Symbols       (Current: {', '.join(symbols)})")
        console.print(f"[2] Set Strategy Type        (Current: {strategy})")
        console.print(f"[3] Toggle Mode              (Current: {mode})")
        console.print("[4] Launch Options Bot")
        console.print("[0] Return to Main Menu")

        choice = Prompt.ask("Select an option", choices=["0", "1", "2", "3", "4"])

        if choice == "1":
            syms_input = Prompt.ask(
                "Enter symbols (comma-separated)", default="TSLA,SPY"
            )
            symbols = [s.strip().upper() for s in syms_input.split(",")]

        elif choice == "2":
            strategy = Prompt.ask(
                "Choose strategy",
                choices=["Vertical Spreads", "Iron Condors", "Covered Calls"],
                default="Vertical Spreads",
            )

        elif choice == "3":
            mode = "Execution" if mode == "Analysis" else "Analysis"
            console.print(f"[yellow]Mode switched to: {mode}[/yellow]")

        elif choice == "4":
            try:
                console.print(
                    f"[green]Launching Options Bot in {mode} mode for {', '.join(symbols)}...[/green]"
                )
                asyncio.run(run_options_analysis())
            except Exception as e:
                console.print(f"[red]Options bot error: {e}[/red]")

        elif choice == "0":
            break


def ask_trading_advisor(self):
    """LLM-based trading assistant."""
    from llm.gpt_client import ask_gpt

    console.print("\n[bold cyan]TRADING ADVISOR — GPT MODE[/bold cyan]")
    prompt = Prompt.ask("Ask your trading question")

    try:
        # Optional: inject portfolio summary
        context = self.view_positions(render=False)
        formatted = (
            "\n".join(f"{row[0]} - Qty: {row[1]}, P/L: {row[4]}" for row in context)
            if context
            else ""
        )

        console.print("[dim]Fetching response from GPT...[/dim]")
        response = ask_gpt(f"{prompt}\n\nPortfolio Snapshot:\n{formatted}")
        console.print(
            Panel.fit(
                response or "[dim]No response returned.[/dim]",
                title="[bold magenta]Advisor Response[/bold magenta]",
                border_style="blue",
            )
        )

    except Exception as e:
        console.print(f"[red]LLM advisory error: {e}[/red]")


def show_transaction_log(self):
    path = "logs/transactions.log"
    try:
        with open(path, "r") as f:
            lines = f.readlines()[-10:]  # Tail last 10
        console.print(Panel("".join(lines), title="Transaction Log"))
    except:
        console.print("[dim]No transaction log found.[/dim]")


def show_snapshot_files(self):
    try:
        with open("portfolio_snapshot.json", "r") as f:
            data = json.load(f)
        console.print(Panel.fit(json.dumps(data, indent=2), title="Last Snapshot"))
    except:
        console.print("[dim]No snapshot file available.[/dim]")


def show_advisor_history(self):
    path = "logs/advisor_history.log"
    try:
        with open(path, "r") as f:
            lines = f.readlines()[-5:]
        console.print(Panel("".join(lines), title="Advisor History"))
    except:
        console.print("[dim]No advisor history found.[/dim]")


def show_debug_logs(self):
    path = "logs/debug.log"
    try:
        with open(path, "r") as f:
            lines = f.readlines()[-10:]
        console.print(Panel("".join(lines), title="Debug Log"))
    except:
        console.print("[dim]No debug log found.[/dim]")


def view_utilities_menu(self):
    """Modular entry point for advanced tools under development."""
    while True:
        console.print("\n[bold cyan]UTILITIES MENU[/bold cyan]")
        console.print("[1] Metrics Formatter")
        console.print("[2] Run Backtester")
        console.print("[3] Import/Export Snapshots")
        console.print("[4] Launch Market Screener")
        console.print("[5] Configure Alerts")
        console.print("[0] Return to Main Menu")

        choice = Prompt.ask("Select", choices=["0", "1", "2", "3", "4", "5"])

        if choice == "1":
            self.launch_metrics_formatter()
        elif choice == "2":
            self.launch_backtester()
        elif choice == "3":
            self.handle_snapshot_io()
        elif choice == "4":
            self.launch_market_screener()
        elif choice == "5":
            self.configure_alerts()
        elif choice == "0":
            break


def launch_metrics_formatter(self):
    console.print("[yellow]Metrics Formatter module coming soon.[/yellow]")


def launch_backtester(self):
    try:
        from backtester import run_backtest

        asyncio.run(run_backtest())
    except Exception as e:
        console.print(f"[red]Backtester failed: {e}[/red]")


def handle_snapshot_io(self):
    console.print("[yellow]Import/export snapshot tools coming soon.[/yellow]")


def launch_market_screener(self):
    console.print("[yellow]Screener module under development.[/yellow]")


def configure_alerts(self):
    console.print("[yellow]Alert configuration UI not yet available.[/yellow]")
