def show_dashboard(self):
    """Display portfolio summary as live dashboard on app start."""
    try:
        positions = self.portfolio.view_positions()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        console.clear()
        console.print(f"[bold blue]FUND RUNNER — LIVE DASHBOARD[/bold blue]")
        console.print(f"[dim]As of: {timestamp}[/dim]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Symbol", justify="center")
        table.add_column("Qty", justify="right")
        table.add_column("Avg Entry", justify="right")
        table.add_column("Price", justify="right")
        table.add_column("$ P/L", justify="right")

        for pos in positions:
            try:
                sym = pos.get("symbol", "n/a")
                qty = float(pos.get("qty", 0))
                ae = float(pos.get("avg_entry_price", 0))
                cp = float(pos.get("current_price", 0))
                pl = (cp - ae) * qty
                table.add_row(
                    sym, str(int(qty)), f"{ae:.2f}", f"{cp:.2f}", f"{pl:+.2f}"
                )
            except:
                continue

        console.print(table)
        console.print("\n🔁 [T] Launch Ticker (real-time view)\n")
    except Exception as e:
        console.print(f"[red]Error showing dashboard: {e}[/red]")


def show_main_menu(self):
    menu_text = """
[bold cyan]Main Menu[/bold cyan]

[1] View Account Info
[2] Enter Trade
[3] Manage Watchlists
[4] Run Trading Bot
[5] Run Options Bot
[6] Ask Trading Advisor (LLM)
[7] View Logs & History
[8] Utilities
[0] Exit
"""
    console.print(Panel.fit(menu_text, border_style="blue"))


def run(self):
    """Primary CLI loop with dashboard and full menu integration."""
    while True:
        self.show_dashboard()
        self.show_main_menu()
        choice = Prompt.ask(
            "Select an option",
            choices=["T", "1", "2", "3", "4", "5", "6", "7", "8", "0"],
            default="0",
        )
        if choice == "T":
            self.launch_live_ticker()
        elif choice == "1":
            self.view_account_info()
        elif choice == "2":
            self.enter_trade()
        elif choice == "3":
            self.manage_watchlist()
        elif choice == "4":
            self.run_trading_bot()
        elif choice == "5":
            self.run_options_session()
        elif choice == "6":
            self.get_trading_advice()
        elif choice == "7":
            self.view_logs_menu()
        elif choice == "8":
            self.view_utilities_menu()
        elif choice == "0":
            console.print("[red]Exiting FundRunner.[/red]")
            sys.exit(0)
        Prompt.ask("Press Enter to return to main dashboard")
