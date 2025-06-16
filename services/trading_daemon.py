"""Async trading daemon with Flask command API."""

import asyncio
import threading
from dataclasses import dataclass, asdict
from typing import Optional

from flask import Flask, jsonify, request

from alpaca.trading_bot import TradingBot
from options_trading_bot import run_options_analysis


@dataclass
class DaemonState:
    """Shared state for :mod:`trading_daemon`."""

    mode: str = "stocks"
    paused: bool = False
    trade_count: int = 0
    daily_pl: float = 0.0

    def to_dict(self) -> dict:
        """Return a JSON-serialisable view of the daemon state."""
        return asdict(self)


state = DaemonState()
app = Flask(__name__)

_loop: Optional[asyncio.AbstractEventLoop] = None
_loop_task: Optional[asyncio.Task] = None
_thread: Optional[threading.Thread] = None


async def trading_loop() -> None:
    """Main asynchronous trading loop."""
    global state
    while True:
        if not state.paused:
            if state.mode == "stocks":
                bot = TradingBot(auto_confirm=True)
                await bot.run()
                state.trade_count += len(bot.session_summary)
            elif state.mode == "options":
                await run_options_analysis()
            # Placeholder for P/L aggregation; depends on bot implementation
        await asyncio.sleep(5)


@app.route("/status", methods=["GET"])
def status() -> 'flask.Response':
    """Return current daemon status."""
    return jsonify(state.to_dict())


@app.route("/order", methods=["POST"])
def order() -> 'flask.Response':
    """Execute a simple market order via :class:`TradingBot`."""
    data = request.get_json(force=True) or {}
    details = {
        "symbol": data.get("symbol", "AAPL"),
        "qty": int(data.get("qty", 1)),
        "side": data.get("side", "buy"),
        "order_type": "market",
        "time_in_force": "gtc",
    }

    async def _trade():
        bot = TradingBot(auto_confirm=True)
        await bot.execute_trade(details)

    if _loop is not None:
        asyncio.run_coroutine_threadsafe(_trade(), _loop)
    else:
        asyncio.run(_trade())
    state.trade_count += 1
    return jsonify({"status": "submitted"})


@app.route("/pause", methods=["POST"])
def pause() -> 'flask.Response':
    """Pause the trading loop."""
    state.paused = True
    return jsonify({"paused": state.paused})


@app.route("/resume", methods=["POST"])
def resume() -> 'flask.Response':
    """Resume the trading loop."""
    state.paused = False
    return jsonify({"paused": state.paused})


@app.route("/mode", methods=["POST"])
def set_mode() -> 'flask.Response':
    """Update active trading mode."""
    data = request.get_json(force=True) or {}
    state.mode = data.get("mode", state.mode)
    return jsonify({"mode": state.mode})


def start() -> None:
    """Start trading loop and Flask app."""
    global _loop, _loop_task, _thread
    if _loop is None:
        _loop = asyncio.new_event_loop()
        _thread = threading.Thread(target=_loop.run_forever, daemon=True)
        _thread.start()
        _loop_task = asyncio.run_coroutine_threadsafe(trading_loop(), _loop)
    app.run(debug=False, use_reloader=False)


if __name__ == "__main__":
    start()
