
# trading_bot.py
import asyncio
import logging
import math
import sys
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel

from alpaca.api_client import AlpacaClient
from alpaca.portfolio_manager import PortfolioManager
from alpaca.trade_manager import TradeManager
from alpaca.chatgpt_advisor import get_account_overview
from alpaca.llm_vetter import LLMVetter
from alpaca.risk_manager import RiskManager
from config import DEFAULT_TICKERS, EXCLUDE_TICKERS, DEFAULT_TICKERS_FROM_GPT, SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, NOTIFICATION_EMAIL

class TradingBot:
    def __init__(self, auto_confirm=False, vet_trade_logic=True, vetter_vendor="local",
                 risk_threshold=0.6, allocation_limit=0.05, notify_on_trade=False):
        """
        Initialize the TradingBot and all its components.
        """
        self.auto_confirm = auto_confirm
        self.vet_trade_logic = vet_trade_logic
        self.risk_threshold = risk_threshold
        self.allocation_limit = allocation_limit
        self.notify_on_trade = notify_on_trade

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        file_handler = logging.FileHandler("bot.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("Initializing TradingBot components.")
        self.client = AlpacaClient()
        self.portfolio = PortfolioManager()
        self.trader = TradeManager()
        self.vetter = LLMVetter(vendor=vetter_vendor)
        self.risk_manager = RiskManager(base_allocation_limit=allocation_limit, base_risk_threshold=risk_threshold)
        self.session_summary = []  # List of dicts with evaluation/execution info

        self.console = Console()
        self.summary_table = None  # Table for trade evaluations

        self.logger.info("TradingBot initialized with auto_confirm=%s, vet_trade_logic=%s, risk_threshold=%.2f, allocation_limit=%.2f, notify_on_trade=%s",
                         auto_confirm, vet_trade_logic, risk_threshold, allocation_limit, notify_on_trade)

    def get_account_field(self, account, field):
        return account.get(field) if isinstance(account, dict) else getattr(account, field, None)

    def _log_account_details(self, account):
        details = {
            "buying_power": self.get_account_field(account, 'buying_power'),
            "cash": self.get_account_field(account, 'cash'),
            "equity": self.get_account_field(account, 'equity'),
            "portfolio_value": self.get_account_field(account, 'portfolio_value')
        }
        self.logger.info("Account details: %s", details)

    def init_summary_table(self, ticker_list):
        self.summary_table = Table(title="Trade Evaluation Summary")
        self.summary_table.add_column("Ticker", style="bold green")
        self.summary_table.add_column("Current Price", justify="right", style="cyan")
        self.summary_table.add_column("Probability", justify="right", style="magenta")
        self.summary_table.add_column("Expected Net", justify="right", style="yellow")
        self.summary_table.add_column("Decision", style="bold red")
        for ticker in ticker_list:
            self.summary_table.add_row(ticker, "-", "-", "-", "Pending")

    def update_summary_row(self, ticker, current_price, probability, expected_net, decision):
        # Helper to safely format values
        def safe_format(val, fmt):
            try:
                return fmt.format(float(val))
            except (ValueError, TypeError):
                return str(val)
        tickers = {row["ticker"]: row for row in self.session_summary}
        tickers[ticker] = {
            "ticker": ticker,
            "current_price": str(current_price),
            "probability": safe_format(probability, "{:.2f}"),
            "expected_net": safe_format(expected_net, "{:.4f}"),
            "decision": decision
        }
        self.session_summary = list(tickers.values())
        new_table = Table(title="Trade Evaluation Summary")
        new_table.add_column("Ticker", style="bold green")
        new_table.add_column("Current Price", justify="right", style="cyan")
        new_table.add_column("Probability", justify="right", style="magenta")
        new_table.add_column("Expected Net", justify="right", style="yellow")
        new_table.add_column("Decision", style="bold red")
        for t in sorted(tickers.keys()):
            row = tickers[t]
            new_table.add_row(row["ticker"], row["current_price"], row["probability"], row["expected_net"], row["decision"])
        self.summary_table = new_table

    def generate_portfolio_table(self):
        positions = self.portfolio.view_positions()
        table = Table(title="Live Portfolio Positions", style="bold blue")
        table.add_column("Symbol", justify="center", style="green")
        table.add_column("Qty", justify="right", style="cyan")
        table.add_column("Avg Entry", justify="right", style="magenta")
        table.add_column("Current Price", justify="right", style="yellow")
        table.add_column("$ P/L", justify="right", style="red")
        for pos in positions:
            symbol = str(pos.get('symbol', 'N/A'))
            qty = pos.get('qty', 0)
            avg_entry = pos.get('avg_entry_price', None)
            current_price = pos.get('current_price', None)
            if avg_entry is not None and current_price is not None:
                dollar_pl = (current_price - avg_entry) * qty
                avg_entry_str = f"{avg_entry:.2f}"
                current_price_str = f"{current_price:.2f}"
                dollar_pl_str = f"{dollar_pl:.2f}"
            else:
                avg_entry_str = "N/A"
                current_price_str = "N/A"
                dollar_pl_str = "N/A"
            table.add_row(symbol, str(qty), avg_entry_str, current_price_str, dollar_pl_str)
        return table

    def get_ticker_list(self, symbols=None):
        self.logger.info("Getting ticker list. Provided symbols: %s", symbols)
        if symbols and len(symbols) > 0:
            self.logger.info("Using provided ticker list: %s", symbols)
            return symbols
        if DEFAULT_TICKERS_FROM_GPT:
            prompt = ("Return only a comma-separated list of 5 to 10 stock ticker symbols "
                      "suitable for short- to mid-term swing trading for a small/medium account. "
                      "Respond in the format: 'TICKERS: AAPL, MSFT, RIVN'")
            self.logger.info("Querying LLM for default tickers with prompt: %s", prompt)
            response = get_account_overview(prompt)
            self.logger.debug("LLM default tickers response: %s", response)
            import re
            tickers = re.findall(r'\b[A-Z]{2,5}\b', response) if response else []
            if tickers:
                self.logger.info("Using default tickers from LLM: %s", tickers)
                return tickers
            else:
                self.logger.warning("LLM response did not contain valid tickers; falling back to config DEFAULT_TICKERS.")
        default_list = [ticker.strip().upper() for ticker in DEFAULT_TICKERS.split(',')]
        exclude_list = [ticker.strip().upper() for ticker in EXCLUDE_TICKERS.split(',') if ticker.strip()]
        final_list = [ticker for ticker in default_list if ticker not in exclude_list]
        self.logger.info("Final ticker list from config: %s", final_list)
        return final_list

    def evaluate_trade(self, symbol):
        self.logger.info("Evaluating trade for %s", symbol)
        adjusted_allocation, adjusted_risk_threshold = self.risk_manager.adjust_parameters(symbol)
        self.logger.info("Adjusted allocation: %.4f, Adjusted risk threshold: %.4f", adjusted_allocation, adjusted_risk_threshold)
        try:
            account = self.portfolio.view_account()
            self._log_account_details(account)
        except Exception as e:
            self.logger.error("Could not fetch account details for %s: %s", symbol, e)
            return None
        try:
            buying_power = self.get_account_field(account, 'buying_power')
            self.logger.info("Buying power: %s", f"{buying_power:.2f}" if isinstance(buying_power, (float, int)) else "N/A")
            if buying_power is None:
                self.logger.error("Buying power is None, skipping trade evaluation.")
                return None
        except Exception as e:
            self.logger.error("Error parsing buying power for %s: %s", symbol, e)
            return None
        try:
            hist = yf.download(symbol, period="1mo", interval="1d", auto_adjust=False)
            if hist.empty:
                self.logger.warning("No historical data for %s", symbol)
                probability_of_profit = 0.55
                expected_net_value = 0.02
            else:
                returns = hist['Close'].pct_change().dropna()
                mean_return = returns.mean().item() if hasattr(returns.mean(), 'item') else float(returns.mean())
                volatility = returns.std().item() if hasattr(returns.std(), 'item') else float(returns.std())
                if volatility > 0:
                    risk_adjusted = mean_return / volatility
                    probability_of_profit = 1 / (1 + math.exp(-5 * risk_adjusted))
                else:
                    probability_of_profit = 0.5
                expected_net_value = max(mean_return, 0)
            self.logger.info("For %s: probability=%.2f, expected_net=%.4f", symbol, probability_of_profit, expected_net_value)
        except Exception as e:
            self.logger.error("Error computing metrics for %s: %s", symbol, e)
            probability_of_profit = 0.55
            expected_net_value = 0.02
        if probability_of_profit < adjusted_risk_threshold or expected_net_value <= 0:
            self.logger.info("Trade for %s rejected: probability=%.2f, expected_net=%.4f", symbol, probability_of_profit, expected_net_value)
            return None
        try:
            ticker_data = yf.Ticker(symbol)
            current_price = ticker_data.info['regularMarketPrice']
        except Exception as e:
            self.logger.error("Error fetching price for %s: %s", symbol, e)
            return None
        max_allocation = buying_power * self.allocation_limit
        max_qty = max_allocation / current_price
        qty = int(max_qty * 0.5)
        if qty < 1:
            self.logger.info("Insufficient buying power for %s", symbol)
            return None
        stop_loss = current_price * 0.95
        profit_target = current_price * 1.10
        trade_details = {
            "symbol": symbol,
            "qty": qty,
            "side": "buy",
            "order_type": "market",
            "time_in_force": "gtc",
            "probability_of_profit": probability_of_profit,
            "expected_net_value": expected_net_value,
            "current_price": current_price,
            "stop_loss": stop_loss,
            "profit_target": profit_target
        }
        self.logger.info("Trade evaluated for %s: %s", symbol, trade_details)
        return trade_details

    async def confirm_trade(self, trade_details):
        if self.auto_confirm:
            self.logger.info("Auto-confirm enabled.")
            return True
        self.logger.info("Awaiting user confirmation for trade: %s", trade_details)
        print("Proposed trade details:")
        for key, value in trade_details.items():
            print(f"{key}: {value}")
        response = input("Confirm trade execution? (y/n): ")
        self.logger.info("User response: %s", response)
        return response.lower() == 'y'

    def send_trade_notification(self, trade_details, order):
        subject = f"Trade Executed: {trade_details['symbol']}"
        body = f"Trade Details:\n{trade_details}\n\nOrder Info:\n{order}"
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = NOTIFICATION_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        self.logger.info("Sending email for trade %s", trade_details['symbol'])
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)
            self.logger.info("Email sent successfully.")
        except Exception as e:
            self.logger.error("Email send failed: %s", e)

    async def execute_trade(self, trade_details):
        self.logger.info("Executing trade for %s", trade_details["symbol"])
        try:
            symbol = trade_details["symbol"]
            qty = trade_details["qty"]
            side = trade_details["side"]
            order_type = trade_details["order_type"]
            time_in_force = trade_details["time_in_force"]
            if side == "buy":
                order = self.trader.buy(symbol, qty, order_type, time_in_force)
            else:
                order = self.trader.sell(symbol, qty, order_type, time_in_force)
            self.logger.info("Trade executed for %s: %s", symbol, order)
            from transaction_logger import log_transaction
            log_transaction(trade_details, order)
            self.session_summary.append({"ticker": symbol, "action": "Executed", "details": str(trade_details)})
            if self.notify_on_trade:
                self.send_trade_notification(trade_details, order)
            return order
        except Exception as e:
            self.logger.error("Error executing trade for %s: %s", trade_details.get("symbol"), e, exc_info=True)
            return None

    async def monitor_positions(self):
        self.logger.info("Monitoring positions for stop loss/profit target.")
        while True:
            positions = self.portfolio.view_positions()
            for pos in positions:
                try:
                    symbol = pos.get('symbol') if isinstance(pos, dict) else getattr(pos, 'symbol', None)
                    qty = pos.get('qty') if isinstance(pos, dict) else getattr(pos, 'qty', None)
                    pl_percent = pos.get('unrealized_pl_percent', 0) if isinstance(pos, dict) else getattr(pos, 'unrealized_pl_percent', 0)
                    self.logger.info("Position %s: Qty=%s, Unrealized P/L%%=%.2f", symbol, qty, pl_percent)
                    if pl_percent <= -5 or pl_percent >= 10:
                        self.logger.info("Closing %s due to target: %.2f%%", symbol, pl_percent)
                        try:
                            order = self.trader.sell(symbol, qty, 'market', 'gtc')
                            self.logger.info("Closed position for %s: %s", symbol, order)
                            self.session_summary.append({"ticker": symbol, "action": "Closed", "pl_percent": pl_percent})
                        except Exception as e:
                            self.logger.error("Error closing %s: %s", symbol, e)
                except Exception as e:
                    self.logger.error("Error processing position %s: %s", pos, e)
            await asyncio.sleep(60)

    @staticmethod
    def safe_float(val, default=0.0):
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def print_summary(self):
        console = Console()
        table = Table(title="Session Summary")
        table.add_column("Ticker", style="bold green")
        table.add_column("Action", style="cyan")
        table.add_column("Details", style="magenta")
        for trade in self.session_summary:
            details = trade.get("details", "")
            pl = str(trade.get("pl_percent", ""))
            table.add_row(str(trade.get("ticker")), str(trade.get("action")), details if details else pl)
        console.print(table)

    def generate_layout(self):
        layout = Layout()
        layout.split_row(
            Layout(Panel(self.summary_table, title="Trade Evaluations"), name="left"),
            Layout(Panel(self.generate_portfolio_table(), title="Portfolio Positions"), name="right")
        )
        return layout

    async def run(self, symbols=None):
        self.logger.info("Trading bot started.")
        ticker_list = self.get_ticker_list(symbols)
        self.logger.info("Tickers to evaluate: %s", ticker_list)
        self.init_summary_table(ticker_list)

        monitor_task = asyncio.create_task(self.monitor_positions())
        # Use Live with a dynamic layout that shows both evaluation summary and portfolio positions.
        from rich.live import Live
        live = Live(self.generate_layout(), refresh_per_second=2, console=self.console)
        live.start()
        try:
            for symbol in ticker_list:
                self.logger.info("Processing %s", symbol)
                trade_details = self.evaluate_trade(symbol)
                if trade_details:
                    decision = ""
                    if self.vet_trade_logic:
                        approved = self.vetter.vet_trade_logic(trade_details)
                        decision = "Approved" if approved else "Rejected by LLM"
                        if not approved:
                            self.update_summary_row(symbol, trade_details["current_price"],
                                                    trade_details["probability_of_profit"],
                                                    trade_details["expected_net_value"],
                                                    decision)
                            continue
                    confirmed = await self.confirm_trade(trade_details)
                    if confirmed:
                        await self.execute_trade(trade_details)
                        decision = "Executed"
                    else:
                        decision = "User Skipped"
                    self.update_summary_row(symbol, trade_details["current_price"],
                                            trade_details["probability_of_profit"],
                                            trade_details["expected_net_value"],
                                            decision)
                else:
                    self.update_summary_row(symbol, "-", "-", "-", "No Trade")
                # Update live layout with refreshed tables.
                live.update(self.generate_layout())
                await asyncio.sleep(5)
        finally:
            self.logger.info("Trading bot run completed.")
            monitor_task.cancel()
            live.stop()
            self.print_summary()

    def get_chatgpt_advice(self, prompt):
        self.logger.info("Requesting trading advice with prompt: %s", prompt)
        advice = get_account_overview(prompt)
        self.logger.info("Received trading advice: %s", advice)
        return advice


