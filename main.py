# v1.0.0
# cli.py
import sys
import asyncio
from alpacca.trade_manager import TradeManager
from alpacca.portfolio_manager import PortfolioManager
from alpacca.watchlist_manager import WatchlistManager
from alpacca.trading_bot import TradingBot

class CLI:
    def __init__(self):
        self.trade_manager = TradeManager()
        self.portfolio_manager = PortfolioManager()
        self.watchlist_manager = WatchlistManager()

    def print_menu(self):
        print("\n=== Unified Trading App ===")
        print("1. View Account Information")
        print("2. View Portfolio Positions & P/L")
        print("3. Enter a Trade (Buy/Sell)")
        print("4. View Open Orders")
        print("5. Manage Watchlist")
        print("6. RAG Agent - Ask Advisor")
        print("7. Run Trading Bot")
        print("8. Watchlist View")
        print("0. Exit")

    def manage_watchlist_menu(self):
        while True:
            print("\n--- Watchlist Management ---")
            print("1. List Watchlists")
            print("2. Create a Watchlist")
            print("3. Add Symbol to Watchlist")
            print("4. Remove Symbol from Watchlist")
            print("5. View a Watchlist")
            print("6. Delete a Watchlist")
            print("7. Back to Main Menu")
            choice = input("Select an option: ")

            if choice == "1":
                try:
                    watchlists = self.watchlist_manager.list_watchlists()
                    if not watchlists:
                        print("No watchlists found.")
                    else:
                        for wl in watchlists:
                            symbols = ', '.join(wl.symbols) if hasattr(wl, 'symbols') else "N/A"
                            print(f"ID: {wl.id}, Name: {wl.name}, Symbols: {symbols}")
                except Exception as e:
                    print(f"Error listing watchlists: {e}")
            elif choice == "2":
                name = input("Enter watchlist name: ")
                symbols = input("Enter symbols (comma separated): ").upper().split(',')
                symbols = [s.strip() for s in symbols]
                try:
                    wl = self.watchlist_manager.create_watchlist(name, symbols)
                    print(f"Created watchlist '{wl.name}' with ID: {wl.id}")
                except Exception as e:
                    print(f"Error creating watchlist: {e}")
            elif choice == "3":
                wl_id = input("Enter watchlist ID (or name): ")
                symbol = input("Enter symbol to add: ").upper().strip()
                try:
                    self.watchlist_manager.add_to_watchlist(wl_id, symbol)
                    print(f"Added {symbol} to watchlist {wl_id}")
                except Exception as e:
                    print(f"Error adding symbol: {e}")
            elif choice == "4":
                wl_id = input("Enter watchlist ID: ")
                symbol = input("Enter symbol to remove: ").upper().strip()
                try:
                    self.watchlist_manager.remove_from_watchlist(wl_id, symbol)
                    print(f"Removed {symbol} from watchlist {wl_id}")
                except Exception as e:
                    print(f"Error removing symbol: {e}")
            elif choice == "5":
                wl_id = input("Enter watchlist ID: ")
                try:
                    watchlist = self.watchlist_manager.get_watchlist(wl_id)
                    assets = watchlist.assets if hasattr(watchlist, 'assets') else "N/A"
                    print(f"Watchlist '{watchlist.name}': {assets}")
                except Exception as e:
                    print(f"Error retrieving watchlist: {e}")
            elif choice == "6":
                wl_id = input("Enter watchlist ID to delete: ")
                try:
                    self.watchlist_manager.delete_watchlist(wl_id)
                    print(f"Deleted watchlist with ID: {wl_id}")
                except Exception as e:
                    print(f"Error deleting watchlist: {e}")
            elif choice == "7":
                break
            else:
                print("Invalid option. Try again.")

    def enter_trade(self):
        symbol = input("Enter symbol: ").upper().strip()
        qty = input("Enter quantity: ").strip()
        try:
            qty = int(qty)
        except ValueError:
            print("Quantity must be an integer.")
            return
        side = input("Enter side (buy/sell): ").lower().strip()
        if side not in ['buy', 'sell']:
            print("Side must be either 'buy' or 'sell'.")
            return
        order_type = input("Enter order type (market/limit): ").lower().strip()
        time_in_force = input("Enter time in force (gtc, day, etc.): ").lower().strip()

        order = None
        try:
            if side == 'buy':
                order = self.trade_manager.buy(symbol, qty, order_type, time_in_force)
            elif side == 'sell':
                order = self.trade_manager.sell(symbol, qty, order_type, time_in_force)
            if order:
                print(f"Order submitted:\n{order}")
            else:
                print("Order submission failed.")
        except Exception as e:
            print(f"Error submitting trade: {e}")

    def view_open_orders(self):
        try:
            orders = self.trade_manager.list_open_orders()
            if not orders:
                print("No open orders.")
            else:
                print("\n--- Open Orders ---")
                for order in orders:
                    print(f"ID: {order.id}, Symbol: {order.symbol}, Side: {order.side}, "
                          f"Qty: {order.qty}, Status: {order.status}")
        except Exception as e:
            print(f"Error retrieving open orders: {e}")

    def view_account_info(self):
        try:
            account = self.portfolio_manager.view_account()
            print("\n--- Account Information ---")
            print(f"Cash: {account.cash}")
            print(f"Buying Power: {account.buying_power}")
            print(f"Equity: {account.equity}")
            print(f"Portfolio Value: {account.portfolio_value}")
        except Exception as e:
            print(f"Error retrieving account info: {e}")

    def view_positions(self):
        try:
            positions = self.portfolio_manager.view_positions()
            if not positions:
                print("No positions found.")
            else:
                print("\n--- Portfolio Positions & P/L ---")
                for pos in positions:
                    pl = getattr(pos, 'unrealized_pl', 'N/A')
                    print(f"Symbol: {pos.symbol}, Qty: {pos.qty}, Market Value: {pos.market_value}, P/L: {pl}")
        except Exception as e:
            print(f"Error retrieving positions: {e}")

    def get_trading_advice(self):
        prompt = input("Enter your prompt for trading advice: ")
        try:
            from chatgpt_advisor import get_account_overview
            advice = get_account_overview(prompt)
            print("\n--- Trading Advice ---")
            print(advice)
        except Exception as e:
            print(f"Error retrieving trading advice: {e}")

    def run_trading_bot(self):
        symbols = input("Enter symbols (comma separated) for the trading bot (or press Enter to use default): ").upper().split(',')
        symbols = [s.strip() for s in symbols if s.strip()]
        try:
            bot = TradingBot(auto_confirm=False, vet_trade_logic=True, vetter_vendor="local")
            asyncio.run(bot.run(symbols if symbols else None))
        except Exception as e:
            print(f"Error running trading bot: {e}")

    def launch_watchlist_view(self):
        try:
            from watchlist_view import main as watchlist_view_main
            watchlist_view_main()
        except Exception as e:
            print(f"Error launching watchlist view: {e}")

    def run(self):
        while True:
            self.print_menu()
            choice = input("Select an option: ")
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
            elif choice == "0":
                print("Exiting the app.")
                sys.exit(0)
            else:
                print("Invalid option. Please try again.")

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
from trading_bot import TradingBot

async def main():
    # Define the list of symbols to evaluate
    symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]
    # Initialize the bot (set auto_confirm=False for manual confirmation)
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
