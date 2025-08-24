"""Asynchronous trading daemon with Flask control endpoints."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from threading import Thread

from flask import Flask, jsonify, request

from fundrunner.alpaca.trading_bot import TradingBot
from fundrunner.bots.options_trading_bot import run_options_analysis
from fundrunner.utils.config import MICRO_MODE
from fundrunner.utils.error_handling import (
    FundRunnerError,
    TradingError,
    format_user_error,
    safe_execute,
    safe_execute_async,
    setup_global_error_handler,
)


@dataclass
class DaemonState:
    """Shared runtime state for the trading daemon."""

    mode: str = "stock"
    paused: bool = False
    trade_count: int = 0
    daily_pl: float = 0.0


state = DaemonState()
app = Flask(__name__)


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


@app.route("/start", methods=["POST"])
def start_trading():
    """Start/resume the trading loop (alias for /resume)."""
    state.paused = False
    return jsonify({"message": "trading started"})


@app.route("/stop", methods=["POST"])
def stop_trading():
    """Stop/pause the trading loop (alias for /pause)."""
    state.paused = True
    return jsonify({"message": "trading stopped"})


@app.route("/order", methods=["POST"])
def submit_order():
    """Placeholder manual order endpoint."""
    details = request.get_json(force=True) or {}
    state.trade_count += 1
    return jsonify({"message": "order received", "details": details})


async def trading_loop() -> None:
    """Main asynchronous loop calling the active trading bot."""
    logger = logging.getLogger(__name__)

    while True:
        if not state.paused:

            async def _run_trading_cycle():
                if state.mode == "stock":
                    bot = TradingBot(
                        auto_confirm=True, vet_trade_logic=False, micro_mode=MICRO_MODE
                    )
                    await bot.run()
                    state.trade_count += len(bot.session_summary)
                else:
                    await run_options_analysis()
                    state.trade_count += 1

            success, result = await safe_execute_async(_run_trading_cycle)
            if not success:
                error_msg = format_user_error(result, "Trading cycle failed")
                logger.error(f"Trading daemon error: {error_msg}")
                # Continue running even after errors, but add backoff
                await asyncio.sleep(30)

        await asyncio.sleep(5)


def _run_flask():
    app.run(port=8000, use_reloader=False)


def start() -> None:
    """Start Flask server and trading loop."""
    thread = Thread(target=_run_flask, daemon=True)
    thread.start()
    asyncio.run(trading_loop())


def main():
    """Entry point for the FundRunner trading daemon."""
    # Setup global error handling
    setup_global_error_handler()

    start()


if __name__ == "__main__":
    main()
