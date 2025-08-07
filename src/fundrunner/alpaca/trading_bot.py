"""Interactive trading bot using Alpaca for market data and order routing.

This module defines :class:`TradingBot`, which drives trading logic and
optionally displays results via ``rich`` or ``textual`` dashboards. The bot
evaluates trades using live Alpaca data and optional LLM vetting, coordinates
account info retrieval, position monitoring and order execution.
"""

import asyncio
import logging
import math
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re

from rich.console import Console
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel

from fundrunner.dashboards.dashboard import Dashboard
from fundrunner.dashboards.textual_dashboard import DashboardApp

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.alpaca.portfolio_manager import PortfolioManager
from fundrunner.alpaca.trade_manager import TradeManager
from fundrunner.alpaca.chatgpt_advisor import get_account_overview
from fundrunner.alpaca.llm_vetter import LLMVetter
from fundrunner.alpaca.risk_manager import RiskManager
from fundrunner.alpaca.yield_farming import YieldFarmer
from fundrunner.utils.config import (
    DEFAULT_TICKERS,
    EXCLUDE_TICKERS,
    DEFAULT_TICKERS_FROM_GPT,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    NOTIFICATION_EMAIL,
    MICRO_MODE,
    PORTFOLIO_MANAGER_MODE,
)


class TradingBot:
    def __init__(
        self,
        auto_confirm=False,
        vet_trade_logic=False,
        vetter_vendor="local",
        risk_threshold=0.6,
        allocation_limit=0.05,
        notify_on_trade=False,
        micro_mode=MICRO_MODE,
        confirm_timeout: float | None = 10.0,
        portfolio_manager_mode=PORTFOLIO_MANAGER_MODE,
    ):
        """Initialize the :class:`TradingBot` and its components.

        Args:
            auto_confirm (bool): Automatically confirm trades if ``True``.
            vet_trade_logic (bool): Run trade logic through the LLM vetter. Defaults to ``False`` to avoid
                external API usage unless explicitly enabled.
            vetter_vendor (str): Backend used for vetting.
            risk_threshold (float): Minimum probability of profit.
            allocation_limit (float): Base fraction of buying power per trade.
            notify_on_trade (bool): Send email notifications when trades execute.
            micro_mode (bool): Enable small account mode with relaxed sizing.
            confirm_timeout (float | None): Seconds to wait for user input before
                auto-confirming a trade. ``None`` disables the timeout.
            portfolio_manager_mode (bool): Run in passive portfolio management mode.
        """
        self.auto_confirm = auto_confirm
        self.vet_trade_logic = vet_trade_logic
        self.risk_threshold = risk_threshold
        self.micro_mode = micro_mode
        self.portfolio_manager_mode = portfolio_manager_mode
        self.allocation_limit = (
            allocation_limit if not micro_mode else max(1.0, allocation_limit)
        )
        self.notify_on_trade = notify_on_trade
        self.confirm_timeout = confirm_timeout

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler("bot.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        self.logger.info("Initializing TradingBot components.")
        self.client = AlpacaClient()
        self.portfolio = PortfolioManager()
        self.trader = TradeManager()
        self.vetter = LLMVetter(vendor=vetter_vendor)
        self.risk_manager = RiskManager(
            base_allocation_limit=self.allocation_limit,
            base_risk_threshold=risk_threshold,
        )
        self.yield_farmer = YieldFarmer(self.client)
        self.session_summary = []  # List of dicts with evaluation/execution info
        self.trade_tracker = []  # New: list to track detailed trade info

        self.console = Console()
        self.dashboard: Dashboard | None = None
        self.dashboard_app: DashboardApp | None = None
        self.eval_queue: asyncio.Queue | None = None
        self.trade_queue: asyncio.Queue | None = None
        self.portfolio_queue: asyncio.Queue | None = None
        self.calc_queue: asyncio.Queue | None = None
        self.summary_row_keys: dict[str, str] = {}
        self.dashboard_task: asyncio.Task | None = None

        self.logger.info(
            "TradingBot initialized with auto_confirm=%s, vet_trade_logic=%s, risk_threshold=%.2f, allocation_limit=%.2f, notify_on_trade=%s, portfolio_mode=%s",
            auto_confirm,
            vet_trade_logic,
            risk_threshold,
            allocation_limit,
            notify_on_trade,
            portfolio_manager_mode,
        )

    def get_account_field(self, account, field):
        return (
            account.get(field)
            if isinstance(account, dict)
            else getattr(account, field, None)
        )

    def _log_account_details(self, account):
        details = {
            "buying_power": self.get_account_field(account, "buying_power"),
            "cash": self.get_account_field(account, "cash"),
            "equity": self.get_account_field(account, "equity"),
            "portfolio_value": self.get_account_field(account, "portfolio_value"),
        }
        self.logger.info("Account details: %s", details)

    def log_calc(self, message: str) -> None:
        """Log a calculation step and enqueue it for the dashboard."""

        self.logger.info(message)
        if self.calc_queue:
            self.calc_queue.put_nowait(message)

    def init_summary_table(self, ticker_list):
        if self.dashboard:
            table = self.dashboard.summary_table
            table.rows.clear()
            for ticker in ticker_list:
                table.add_row(ticker, "-", "-", "-", "Pending")
            self.dashboard.refresh()
        if self.dashboard_app:
            for ticker in ticker_list:
                key = self.dashboard_app.eval_table.add_row(
                    ticker, "-", "-", "-", "Pending", key=ticker
                )
                self.summary_row_keys[ticker] = key
        if self.eval_queue and not self.dashboard_app:
            for ticker in ticker_list:
                self.eval_queue.put_nowait((ticker, "-", "-", "-", "Pending"))

    def update_summary_row(
        self, ticker, current_price, probability, expected_net, decision
    ):
        """Update an existing row in the evaluation summary tables.

        If ``ticker`` doesn't exist yet in the textual dashboard table, a new
        row is inserted and its key cached for future updates.
        """

        # Helper to safely format values
        def safe_format(val, fmt):
            try:
                return fmt.format(float(val))
            except (ValueError, TypeError):
                return str(val)

        if not self.dashboard and not self.eval_queue:
            return
        tickers = {row["ticker"]: row for row in self.session_summary}
        tickers[ticker] = {
            "ticker": ticker,
            "current_price": str(current_price),
            "probability": safe_format(probability, "{:.2f}"),
            "expected_net": safe_format(expected_net, "{:.4f}"),
            "decision": decision,
        }
        self.session_summary = list(tickers.values())
        if self.dashboard:
            table = self.dashboard.summary_table
            table.rows.clear()
            for t in sorted(tickers.keys()):
                row = tickers[t]
                table.add_row(
                    row["ticker"],
                    row["current_price"],
                    row["probability"],
                    row["expected_net"],
                    row["decision"],
                )
            self.dashboard.refresh()
        if self.dashboard_app:
            table = self.dashboard_app.eval_table
            if ticker not in self.summary_row_keys:
                row_key = table.add_row(
                    ticker,
                    str(current_price),
                    safe_format(probability, "{:.2f}"),
                    safe_format(expected_net, "{:.4f}"),
                    decision,
                    key=ticker,
                )
                self.summary_row_keys[ticker] = row_key
            else:
                row_key = self.summary_row_keys[ticker]
                cols = list(table.columns.keys())
                table.update_cell(row_key, cols[1], str(current_price))
                table.update_cell(row_key, cols[2], safe_format(probability, "{:.2f}"))
                table.update_cell(row_key, cols[3], safe_format(expected_net, "{:.4f}"))
                table.update_cell(row_key, cols[4], decision)

    def generate_portfolio_table(self):
        if not self.dashboard and not self.portfolio_queue:
            return
        positions = self.portfolio.view_positions()
        if self.dashboard:
            table = self.dashboard.portfolio_table
            table.rows.clear()
        for pos in positions:
            symbol = str(pos.get("symbol", "N/A"))
            qty = pos.get("qty", 0)
            avg_entry = pos.get("avg_entry_price", None)
            current_price = pos.get("current_price", None)
            if avg_entry is not None and current_price is not None:
                dollar_pl = (current_price - avg_entry) * qty
                avg_entry_str = f"{avg_entry:.2f}"
                current_price_str = f"{current_price:.2f}"
                dollar_pl_str = f"{dollar_pl:.2f}"
            else:
                avg_entry_str = "N/A"
                current_price_str = "N/A"
                dollar_pl_str = "N/A"
            if self.dashboard:
                table.add_row(
                    symbol, str(qty), avg_entry_str, current_price_str, dollar_pl_str
                )
            if self.portfolio_queue:
                self.portfolio_queue.put_nowait(
                    (
                        symbol,
                        str(qty),
                        avg_entry_str,
                        current_price_str,
                        dollar_pl_str,
                    )
                )
        if self.dashboard:
            self.dashboard.refresh()

    def generate_trade_tracker_table(self):
        """Populate trade tracker table in dashboard(s)."""
        if not self.dashboard and not self.trade_queue:
            return
        if self.dashboard:
            table = self.dashboard.trade_tracker_table
            table.rows.clear()
        for trade in self.trade_tracker:
            entry = (
                f"{trade.get('entry_price', '-'):.2f}"
                if trade.get("entry_price") is not None
                else "-"
            )
            stop = (
                f"{trade.get('stop_loss', '-'):.2f}"
                if trade.get("stop_loss") is not None
                else "-"
            )
            target = (
                f"{trade.get('profit_target', '-'):.2f}"
                if trade.get("profit_target") is not None
                else "-"
            )
            es_val = (
                f"{trade.get('expected_shortfall', '-'):.4f}"
                if trade.get("expected_shortfall") is not None
                else "-"
            )
            status = trade.get("status", "Pending")
            if self.dashboard:
                table.add_row(trade["symbol"], entry, stop, target, es_val, status)
            if self.trade_queue:
                self.trade_queue.put_nowait(
                    (trade["symbol"], entry, stop, target, es_val, status)
                )
        if self.dashboard:
            self.dashboard.refresh()

    def generate_layout(self):
        """
        Creates a layout that includes:
          - Trade Evaluation Summary (left)
          - Trade Tracker (center)
          - Live Portfolio Positions (right)
        """
        if not self.dashboard:
            return Layout()
        layout = Layout()
        layout.split_row(
            Layout(
                Panel(self.dashboard.summary_table, title="Trade Evaluations"),
                name="left",
            ),
            Layout(
                Panel(self.dashboard.trade_tracker_table, title="Trade Tracker"),
                name="center",
            ),
            Layout(
                Panel(self.dashboard.portfolio_table, title="Portfolio Positions"),
                name="right",
            ),
        )
        return layout

    def get_ticker_list(self, symbols=None):
        self.logger.info("Getting ticker list. Provided symbols: %s", symbols)
        if symbols and len(symbols) > 0:
            self.logger.info("Using provided ticker list: %s", symbols)
            return symbols
        if DEFAULT_TICKERS_FROM_GPT:
            prompt = (
                "Return only a comma-separated list of 5 to 10 stock ticker symbols "
                "suitable for short- to mid-term swing trading for a small/medium account. "
                "Respond in the format: 'TICKERS: AAPL, MSFT, RIVN'"
            )
            self.logger.info("Querying LLM for default tickers with prompt: %s", prompt)
            response = get_account_overview(prompt)
            self.logger.debug("LLM default tickers response: %s", response)
            tickers = re.findall(r"\b[A-Z]{2,5}\b", response) if response else []
            if tickers:
                self.logger.info("Using default tickers from LLM: %s", tickers)
                return tickers
            else:
                self.logger.warning(
                    "LLM response did not contain valid tickers; falling back to config DEFAULT_TICKERS."
                )
        default_list = [ticker.strip().upper() for ticker in DEFAULT_TICKERS.split(",")]
        exclude_list = [
            ticker.strip().upper()
            for ticker in EXCLUDE_TICKERS.split(",")
            if ticker.strip()
        ]
        final_list = [ticker for ticker in default_list if ticker not in exclude_list]
        self.logger.info("Final ticker list from fundrunner.utils.config: %s", final_list)
        return final_list

    async def evaluate_trade(self, symbol):
        """Evaluate whether to trade ``symbol`` and return order details."""

        self.log_calc(f"Evaluating trade for {symbol}")
        adjusted_allocation, adjusted_risk_threshold = (
            self.risk_manager.adjust_parameters(symbol)
        )
        self.log_calc(
            f"Adjusted allocation: {adjusted_allocation:.4f}, risk threshold: {adjusted_risk_threshold:.4f}"
        )
        await asyncio.sleep(1)
        try:
            account = self.portfolio.view_account()
            self._log_account_details(account)
            self.log_calc("Fetched account information")
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.error("Could not fetch account details for %s: %s", symbol, e)
            return None
        try:
            buying_power = self.get_account_field(account, "buying_power")
            self.log_calc(
                "Buying power: "
                + (
                    f"{buying_power:.2f}"
                    if isinstance(buying_power, (float, int))
                    else "N/A"
                )
            )
            await asyncio.sleep(1)
            if buying_power is None:
                self.logger.error("Buying power is None, skipping trade evaluation.")
                return None
        except Exception as e:
            self.logger.error("Error parsing buying power for %s: %s", symbol, e)
            return None
        # Compute equity trade metrics using historical data
        try:
            hist = self.client.get_historical_bars(symbol, days=30)
            if hist is None or hist.empty:
                self.logger.warning("No historical data for %s", symbol)
                probability_of_profit = 0.55
                expected_net_value = 0.02
                es_metric = None
            else:
                close_col = "close" if "close" in hist.columns else "Close"
                returns = hist[close_col].pct_change().dropna()
                mean_return = (
                    returns.mean().item()
                    if hasattr(returns.mean(), "item")
                    else float(returns.mean())
                )
                volatility = (
                    returns.std().item()
                    if hasattr(returns.std(), "item")
                    else float(returns.std())
                )
                if volatility > 0:
                    risk_adjusted = mean_return / volatility
                    probability_of_profit = 1 / (1 + math.exp(-5 * risk_adjusted))
                else:
                    probability_of_profit = 0.5
                expected_net_value = max(mean_return, 0)
                # Calculate Value at Risk (VaR) at 5% level and Expected Shortfall (ES)
                var_5 = returns.quantile(0.05)
                es_metric = returns[
                    returns <= var_5
                ].mean()  # average of worst 5% losses
            self.logger.info(
                "For %s: probability=%.2f, expected_net=%.4f, ES=%.4f",
                symbol,
                probability_of_profit,
                expected_net_value,
                es_metric if es_metric is not None else -999,
            )
            self.log_calc(
                f"Metrics -> P: {probability_of_profit:.2f}, Net: {expected_net_value:.4f}"
            )
            await asyncio.sleep(1)
        except Exception as e:
            self.logger.error("Error computing metrics for %s: %s", symbol, e)
            probability_of_profit = 0.55
            expected_net_value = 0.02
            es_metric = None
        if probability_of_profit < adjusted_risk_threshold or expected_net_value <= 0:
            self.logger.info(
                "Trade for %s rejected: probability=%.2f, expected_net=%.4f",
                symbol,
                probability_of_profit,
                expected_net_value,
            )
            return None
        try:
            current_price = self.client.get_latest_price(symbol)
            if current_price is None:
                raise ValueError("Price not available")
        except Exception as e:
            self.logger.error("Error fetching price for %s: %s", symbol, e)
            return None
        max_allocation = buying_power * self.allocation_limit
        max_qty = max_allocation / current_price
        qty = int(max_qty * 0.5)
        if qty < 1:
            if self.micro_mode and buying_power >= current_price:
                qty = 1
            else:
                self.logger.info("Insufficient buying power for %s", symbol)
                return None
        self.log_calc(f"Alloc {max_allocation:.2f} -> qty {qty} at {current_price:.2f}")
        await asyncio.sleep(1)
        # Set stop loss and profit target values
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
            "profit_target": profit_target,
            "entry_price": current_price,  # Record the initial entry price
            "expected_shortfall": es_metric,  # New ES metric for trade evaluation
        }
        # Add trade to tracker with status pending
        trade_tracker_entry = trade_details.copy()
        trade_tracker_entry["status"] = "Pending"
        self.trade_tracker.append(trade_tracker_entry)
        self.log_calc("Trade evaluation complete")
        self.logger.info("Trade evaluated for %s: %s", symbol, trade_details)
        return trade_details

    async def confirm_trade(self, trade_details, timeout: float | None = None):
        """Prompt the user to confirm a trade with optional timeout."""

        if self.auto_confirm:
            self.logger.info("Auto-confirm enabled.")
            return True
        self.logger.info("Awaiting user confirmation for trade: %s", trade_details)
        print("Proposed trade details:")
        for key, value in trade_details.items():
            print(f"{key}: {value}")
        prompt = "Confirm trade execution? (y/n): "
        timeout = self.confirm_timeout if timeout is None else timeout
        try:
            if timeout is None:
                response = await asyncio.to_thread(input, prompt)
            else:
                response = await asyncio.wait_for(
                    asyncio.to_thread(input, prompt), timeout
                )
        except asyncio.TimeoutError:
            self.logger.info(
                "User input timeout after %.1f seconds, auto-confirming trade.",
                timeout,
            )
            return True
        self.logger.info("User response: %s", response)
        return str(response).lower().startswith("y")

    def send_trade_notification(self, trade_details, order):
        subject = f"Trade Executed: {trade_details['symbol']}"
        body = f"Trade Details:\n{trade_details}\n\nOrder Info:\n{order}"
        msg = MIMEMultipart()
        msg["From"] = SMTP_USERNAME
        msg["To"] = NOTIFICATION_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        self.logger.info("Sending email for trade %s", trade_details["symbol"])
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
            from fundrunner.utils.transaction_logger import log_transaction

            log_transaction(trade_details, order)
            self.session_summary.append(
                {"ticker": symbol, "action": "Executed", "details": str(trade_details)}
            )
            # Update trade tracker status to Executed
            for trade in self.trade_tracker:
                if trade["symbol"] == symbol and trade["status"] == "Pending":
                    trade["status"] = "Executed"
                    break
            self.generate_trade_tracker_table()
            self.generate_portfolio_table()
            if self.notify_on_trade:
                self.send_trade_notification(trade_details, order)
            return order
        except Exception as e:
            self.logger.error(
                "Error executing trade for %s: %s",
                trade_details.get("symbol"),
                e,
                exc_info=True,
            )
            return None

    async def monitor_positions(self):
        self.logger.info("Monitoring positions for stop loss/profit target.")
        while True:
            positions = self.portfolio.view_positions()
            for pos in positions:
                try:
                    symbol = (
                        pos.get("symbol")
                        if isinstance(pos, dict)
                        else getattr(pos, "symbol", None)
                    )
                    qty = (
                        pos.get("qty")
                        if isinstance(pos, dict)
                        else getattr(pos, "qty", None)
                    )
                    pl_percent = (
                        pos.get("unrealized_pl_percent", 0)
                        if isinstance(pos, dict)
                        else getattr(pos, "unrealized_pl_percent", 0)
                    )
                    self.logger.info(
                        "Position %s: Qty=%s, Unrealized P/L%%=%.2f",
                        symbol,
                        qty,
                        pl_percent,
                    )
                    if pl_percent <= -5 or pl_percent >= 10:
                        self.logger.info(
                            "Closing %s due to target: %.2f%%", symbol, pl_percent
                        )
                        try:
                            order = self.trader.sell(symbol, qty, "market", "gtc")
                            self.logger.info(
                                "Closed position for %s: %s", symbol, order
                            )
                            self.session_summary.append(
                                {
                                    "ticker": symbol,
                                    "action": "Closed",
                                    "pl_percent": pl_percent,
                                }
                            )
                        except Exception as e:
                            self.logger.error("Error closing %s: %s", symbol, e)
                except Exception as e:
                    self.logger.error("Error processing position %s: %s", pos, e)
            await asyncio.sleep(60)

    async def maintenance_mode(self, iterations: int = 5, delay: int = 60) -> None:
        """Review open positions and refresh dashboard for a set period.

        Args:
            iterations: Number of loops to perform.
            delay: Seconds to wait between loops.
        """

        self.logger.info("Entering maintenance mode for %d iterations", iterations)
        for _ in range(iterations):
            positions = self.portfolio.view_positions()
            for trade in self.trade_tracker:
                if trade.get("status") != "Executed":
                    continue
                symbol = trade["symbol"]
                pos = next((p for p in positions if p.get("symbol") == symbol), None)
                if not pos:
                    continue
                pl_percent = pos.get("unrealized_pl_percent", 0)
                message = f"P/L% {pl_percent:.2f} vs forecast {trade.get('expected_net_value', 0):.4f}"
                self.logger.info("Maintenance check %s: %s", symbol, message)
                self.session_summary.append(
                    {"ticker": symbol, "action": "Maint", "details": message}
                )
            self.generate_trade_tracker_table()
            self.generate_portfolio_table()
            await asyncio.sleep(delay)
        self.logger.info("Maintenance mode completed.")
        
    def rebalance_portfolio(self):
        """Rebalance holdings based on optimized portfolio weights."""
        positions = self.portfolio.view_positions()
        tickers = []
        for pos in positions:
            symbol = (
                pos.get("symbol")
                if isinstance(pos, dict)
                else getattr(pos, "symbol", None)
            )
            if symbol:
                tickers.append(symbol)
        if not tickers:
            return
        import pandas as pd
        from plugins import portfolio_optimizer

        price_data = {}
        for sym in tickers:
            bars = self.client.get_historical_bars(sym, days=30)
            if bars is not None and "close" in bars:
                price_data[sym] = bars["close"]
        if not price_data:
            return
        prices_df = pd.DataFrame(price_data)
        weights = portfolio_optimizer.optimize_portfolio(prices_df)
        account = self.portfolio.view_account()
        portfolio_value = self.safe_float(account.get("portfolio_value"))
        for sym, weight in weights.items():
            price = self.client.get_latest_price(sym)
            if price is None or portfolio_value == 0:
                continue
            target_qty = (portfolio_value * weight) / price
            current = next(
                (
                    p
                    for p in positions
                    if (
                        p.get("symbol")
                        if isinstance(p, dict)
                        else getattr(p, "symbol", None)
                    )
                    == sym
                ),
                None,
            )
            current_qty = self.safe_float(current.get("qty")) if current else 0
            diff = target_qty - current_qty
            if diff > 1:
                self.trader.buy(sym, int(diff))
            elif diff < -1:
                self.trader.sell(sym, int(abs(diff)))
            self.logger.info("Rebalanced %s to %.2f%%", sym, weight * 100)

    async def periodic_rebalance(self, interval_minutes: int = 60):
        """Periodically rebalance the portfolio."""
        while True:
            self.rebalance_portfolio()
            await asyncio.sleep(interval_minutes * 60)

    async def run_portfolio_manager(self):
        """Run in passive portfolio management mode."""
        self.eval_queue = asyncio.Queue()
        self.trade_queue = asyncio.Queue()
        self.portfolio_queue = asyncio.Queue()
        self.calc_queue = asyncio.Queue()
        self.dashboard_app = DashboardApp(
            self.eval_queue,
            self.trade_queue,
            self.portfolio_queue,
            calc_queue=self.calc_queue,
        )
        self.dashboard_task = asyncio.create_task(self.dashboard_app.run_async())
        self.generate_trade_tracker_table()
        self.generate_portfolio_table()
        monitor_task = asyncio.create_task(self.monitor_positions())
        rebalance_task = asyncio.create_task(self.periodic_rebalance())
        try:
            while True:
                await asyncio.sleep(60)
        finally:
            monitor_task.cancel()
            rebalance_task.cancel()
            if self.dashboard_app:
                await self.dashboard_app.action_quit()
            if self.dashboard_task:
                await self.dashboard_task

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
            table.add_row(
                str(trade.get("ticker")),
                str(trade.get("action")),
                details if details else pl,
            )
        console.print(table)

    async def run_yield_farming_mode(
        self,
        allocation_percent: float = 0.5,
        mode: str = "lending",
        symbols: list[str] | None = None,
        active: bool = False,
    ) -> list[dict[str, float]]:
        """Execute automated yield-farming strategies.

        Parameters
        ----------
        allocation_percent:
            Fraction of available cash to allocate.
        mode:
            ``"lending"`` for stock lending rates or ``"dividend"`` for dividend
            yields.
        symbols:
            Optional list of tickers used for dividend strategies.
        active:
            When ``True`` and ``mode='dividend'`` the stock with the nearest
            ex-dividend date is purchased exclusively.
        """
        if mode not in {"lending", "dividend"}:
            raise ValueError("mode must be 'lending' or 'dividend'")

        self.logger.info(
            "Running yield farming: mode=%s allocation=%.2f", mode, allocation_percent
        )
        if mode == "lending":
            portfolio = self.yield_farmer.build_lending_portfolio(
                allocation_percent=allocation_percent
            )
        else:
            if not symbols:
                symbols = self.get_ticker_list()
            portfolio = self.yield_farmer.build_dividend_portfolio(
                symbols,
                allocation_percent=allocation_percent,
                active=active,
            )
        for pick in portfolio:
            if pick.get("qty", 0) > 0:
                self.trader.buy(pick["symbol"], pick["qty"])
        return portfolio

    async def run(self, symbols=None):
        """Execute the trading loop and display the textual dashboard."""

        self.logger.info("Trading bot started.")
        if self.portfolio_manager_mode:
            await self.run_portfolio_manager()
            return
        ticker_list = self.get_ticker_list(symbols)
        self.logger.info("Tickers to evaluate: %s", ticker_list)
        self.eval_queue = asyncio.Queue()
        self.trade_queue = asyncio.Queue()
        self.portfolio_queue = asyncio.Queue()
        self.calc_queue = asyncio.Queue()
        self.dashboard_app = DashboardApp(
            self.eval_queue,
            self.trade_queue,
            self.portfolio_queue,
            calc_queue=self.calc_queue,
        )
        self.dashboard_task = asyncio.create_task(self.dashboard_app.run_async())
        self.generate_trade_tracker_table()
        self.generate_portfolio_table()
        self.init_summary_table(ticker_list)

        monitor_task = asyncio.create_task(self.monitor_positions())
        try:
            for symbol in ticker_list:
                self.logger.info("Processing %s", symbol)
                trade_details = await self.evaluate_trade(symbol)
                if trade_details:
                    decision = ""
                    if self.vet_trade_logic:
                        approved = self.vetter.vet_trade_logic(trade_details)
                        decision = "Approved" if approved else "Rejected by LLM"
                        if not approved:
                            self.update_summary_row(
                                symbol,
                                trade_details["current_price"],
                                trade_details["probability_of_profit"],
                                trade_details["expected_net_value"],
                                decision,
                            )
                            continue
                    confirmed = await self.confirm_trade(trade_details)
                    if confirmed:
                        await self.execute_trade(trade_details)
                        decision = "Executed"
                    else:
                        decision = "User Skipped"
                    self.update_summary_row(
                        symbol,
                        trade_details["current_price"],
                        trade_details["probability_of_profit"],
                        trade_details["expected_net_value"],
                        decision,
                    )
                else:
                    self.update_summary_row(symbol, "-", "-", "-", "No Trade")
                await asyncio.sleep(5)
        finally:
            self.logger.info("Trading bot run completed.")
            await self.maintenance_mode()
            monitor_task.cancel()
            if self.dashboard_app:
                await self.dashboard_app.action_quit()
            if self.dashboard_task:
                await self.dashboard_task
            self.print_summary()

    def get_chatgpt_advice(self, prompt):
        self.logger.info("Requesting trading advice with prompt: %s", prompt)
        advice = get_account_overview(prompt)
        self.logger.info("Received trading advice: %s", advice)
        return advice
