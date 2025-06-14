"""Asynchronous trading daemon with runtime control endpoints."""

import asyncio
from dataclasses import dataclass, asdict
from typing import Optional, Tuple

from flask import Flask, jsonify, request

from alpaca.trading_bot import TradingBot
from options_trading_bot import run_options_analysis


@dataclass
class DaemonState:
    """Shared state for :class:`TradingDaemon`."""

    mode: str = "stocks"
    paused: bool = False
    trade_count: int = 0
    daily_pl: float = 0.0


class TradingDaemon:
    """Background trading loop controller."""

    def __init__(self, state: DaemonState):
        self.state = state
        self.bot = TradingBot()
        self._task: Optional[asyncio.Task] = None
        self.start_equity: float = 0.0

    async def trading_loop(self) -> None:
        """Continuously run the selected trading mode."""
        account = self.bot.portfolio.view_account()
        self.start_equity = float(account.get("equity", 0.0) or 0.0)
        while True:
            if self.state.paused:
                await asyncio.sleep(1)
                continue
            if self.state.mode == "stocks":
                await self.bot.run()
                self.state.trade_count += len(self.bot.session_summary)
            else:
                await run_options_analysis()
            account = self.bot.portfolio.view_account()
            current_equity = float(account.get("equity", 0.0) or 0.0)
            self.state.daily_pl = current_equity - self.start_equity
            await asyncio.sleep(5)

    def start(self) -> None:
        """Launch the trading loop if not already running."""
        if not self._task:
            self._task = asyncio.create_task(self.trading_loop())

    def pause(self) -> None:
        self.state.paused = True

    def resume(self) -> None:
        self.state.paused = False

    def set_mode(self, mode: str) -> None:
        self.state.mode = mode


def create_app(state: DaemonState) -> Tuple[Flask, TradingDaemon]:
    """Create the Flask app and associated daemon."""
    app = Flask(__name__)
    daemon = TradingDaemon(state)

    @app.before_first_request
    def _start() -> None:
        daemon.start()

    @app.route("/status")
    def status() -> "flask.Response":
        return jsonify(asdict(state))

    @app.route("/order", methods=["POST"])
    def order():
        data = request.get_json(force=True)
        symbol = data.get("symbol")
        qty = int(data.get("qty", 1))
        side = data.get("side", "buy")
        if state.mode != "stocks":
            return jsonify({"error": "Orders only supported in stock mode"}), 400
        if side == "buy":
            order = daemon.bot.trader.buy(symbol, qty)
        else:
            order = daemon.bot.trader.sell(symbol, qty)
        state.trade_count += 1
        return jsonify({"id": getattr(order, "id", None)})

    @app.route("/pause", methods=["POST"])
    def pause():
        daemon.pause()
        return jsonify({"paused": True})

    @app.route("/resume", methods=["POST"])
    def resume():
        daemon.resume()
        return jsonify({"paused": False})

    @app.route("/mode", methods=["POST"])
    def mode():
        mode_val = request.get_json(force=True).get("mode", "stocks")
        daemon.set_mode(mode_val)
        return jsonify({"mode": state.mode})

    return app, daemon


if __name__ == "__main__":
    shared_state = DaemonState()
    app, _ = create_app(shared_state)
    app.run(host="0.0.0.0", port=8000)
