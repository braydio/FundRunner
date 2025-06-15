"""HTTP daemon for controlling the trading bot.

This module exposes a small Flask application used to run the
:class:`TradingBot` in the background.  It supports starting and stopping
the bot and submitting orders over HTTP.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Optional

from flask import Flask, jsonify, request

from alpaca.trade_manager import TradeManager
from alpaca.trading_bot import TradingBot
from config import MICRO_MODE

app = Flask(__name__)

_bot_thread: Optional[threading.Thread] = None
_bot_loop: Optional[asyncio.AbstractEventLoop] = None
_bot_running = False
_current_mode = MICRO_MODE


def _run_bot(tickers: Optional[list[str]] = None) -> None:
    """Run the trading bot inside its own event loop."""
    global _bot_loop, _bot_running
    _bot_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_bot_loop)
    bot = TradingBot(micro_mode=_current_mode)
    _bot_loop.run_until_complete(bot.run(tickers))
    _bot_running = False


@app.route("/start", methods=["POST"])
def start():
    """Start the trading bot if not already running."""
    global _bot_thread, _bot_running
    if _bot_running:
        return jsonify({"status": "running"})
    _bot_running = True
    _bot_thread = threading.Thread(target=_run_bot, daemon=True)
    _bot_thread.start()
    return jsonify({"status": "started"})


@app.route("/stop", methods=["POST"])
def stop():
    """Stop the trading bot by stopping its event loop."""
    global _bot_running, _bot_loop
    if not _bot_running:
        return jsonify({"status": "stopped"})
    if _bot_loop:
        _bot_loop.call_soon_threadsafe(_bot_loop.stop)
    _bot_running = False
    return jsonify({"status": "stopping"})


@app.route("/status", methods=["GET"])
def status():
    """Return current running status."""
    return jsonify({"running": _bot_running, "mode": "micro" if _current_mode else "standard"})


@app.route("/mode", methods=["POST"])
def set_mode():
    """Switch trading mode ("micro" or "standard")."""
    global _current_mode
    mode = (request.json or {}).get("mode")
    if isinstance(mode, str) and mode.lower() == "micro":
        _current_mode = True
    elif isinstance(mode, str) and mode.lower() == "standard":
        _current_mode = False
    return jsonify({"mode": "micro" if _current_mode else "standard"})


@app.route("/order", methods=["POST"])
def submit_order():
    """Submit a simple order via :class:`TradeManager`."""
    data = request.json or {}
    symbol = data.get("symbol")
    qty = int(data.get("qty", 1))
    side = data.get("side", "buy").lower()
    order_type = data.get("order_type", "market")
    tif = data.get("time_in_force", "gtc")
    tm = TradeManager()
    if side == "buy":
        order = tm.buy(symbol, qty, order_type, tif)
    else:
        order = tm.sell(symbol, qty, order_type, tif)
    return jsonify(order if order else {})


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Entry point to launch the daemon."""
    app.run(host=host, port=port)


if __name__ == "__main__":
    run_server()
