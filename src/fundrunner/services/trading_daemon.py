"""Asynchronous trading daemon with Flask control endpoints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, asdict
from threading import Thread

from flask import Flask, jsonify, request

from fundrunner.alpaca.trading_bot import TradingBot
from fundrunner.alpaca.portfolio_manager import PortfolioManager
from fundrunner.bots.options_trading_bot import run_options_analysis
from fundrunner.utils.config import MICRO_MODE


@dataclass
class DaemonState:
    """Shared runtime state for the trading daemon."""

    mode: str = "stock"
    paused: bool = False
    trade_count: int = 0
    daily_pl: float = 0.0
    portfolio_active: bool = False


state = DaemonState()
app = Flask(__name__)
portfolio = PortfolioManager()
portfolio_task: asyncio.Task | None = None


@app.route("/status")
def get_status():
    """Return current daemon status."""
    return jsonify(asdict(state))


@app.route("/pause", methods=["POST"])
def pause_trading():
    """Pause the trading loop."""
    state.paused = True
    return jsonify({"message": "paused"})


@app.route("/resume", methods=["POST"])
def resume_trading():
    """Resume the trading loop."""
    state.paused = False
    return jsonify({"message": "resumed"})


@app.route("/mode", methods=["POST"])
def set_mode():
    """Switch trading mode between stock and options."""
    data = request.get_json(force=True) or {}
    mode = data.get("mode")
    if mode not in {"stock", "options"}:
        return jsonify({"error": "invalid mode"}), 400
    state.mode = mode
    return jsonify({"message": f"mode set to {mode}"})


@app.route("/order", methods=["POST"])
def submit_order():
    """Placeholder manual order endpoint."""
    details = request.get_json(force=True) or {}
    state.trade_count += 1
    return jsonify({"message": "order received", "details": details})


@app.route("/portfolio/start", methods=["POST"])
def start_portfolio_management():
    """Activate background portfolio management."""
    state.portfolio_active = True
    return jsonify({"message": "portfolio management started"})


@app.route("/portfolio/stop", methods=["POST"])
def stop_portfolio_management():
    """Stop background portfolio management."""
    state.portfolio_active = False
    return jsonify({"message": "portfolio management stopped"})


async def trading_loop() -> None:
    """Main asynchronous loop calling the active trading bot."""
    global portfolio_task
    while True:
        if state.portfolio_active and portfolio_task is None:
            portfolio_task = asyncio.create_task(portfolio.run_active_management())
        elif not state.portfolio_active and portfolio_task:
            portfolio_task.cancel()
            try:
                await portfolio_task
            except asyncio.CancelledError:
                pass
            portfolio_task = None

        if not state.paused:
            if state.mode == "stock":
                bot = TradingBot(auto_confirm=True, vet_trade_logic=False, micro_mode=MICRO_MODE)
                await bot.run()
                state.trade_count += len(bot.session_summary)
            else:
                await run_options_analysis()
                state.trade_count += 1
        await asyncio.sleep(5)


def _run_flask():
    app.run(port=8000, use_reloader=False)


def start() -> None:
    """Start Flask server and trading loop."""
    thread = Thread(target=_run_flask, daemon=True)
    thread.start()
    asyncio.run(trading_loop())


if __name__ == "__main__":
    start()
