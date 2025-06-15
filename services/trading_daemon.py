"""Asynchronous trading daemon exposing simple Flask endpoints."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from threading import Thread, Lock

from flask import Flask, jsonify, request

from alpaca.trade_manager import TradeManager
from alpaca.portfolio_manager import PortfolioManager
from alpaca.trading_bot import TradingBot
from options_trading_bot import run_options_analysis


@dataclass
class DaemonState:
    """Shared daemon state for runtime control."""

    mode: str = "stock"
    paused: bool = False
    trade_count: int = 0
    daily_pl: float = 0.0
    start_value: float = 0.0


state = DaemonState()
state_lock = Lock()
trade_manager = TradeManager()
portfolio = PortfolioManager()

app = Flask(__name__)


async def trading_loop() -> None:
    """Main trading loop that delegates to the appropriate bot."""

    while True:
        with state_lock:
            paused = state.paused
            mode = state.mode
        if paused:
            await asyncio.sleep(1)
            continue

        try:
            if mode == "options":
                await run_options_analysis()
            else:
                bot = TradingBot(auto_confirm=True, vet_trade_logic=False)
                await bot.run()
                del bot
            with state_lock:
                state.trade_count += 1
        except Exception:
            # Swallow exceptions so the loop keeps running
            await asyncio.sleep(1)
            continue

        # Update P/L
        try:
            account = portfolio.view_account()
            with state_lock:
                if state.start_value == 0.0:
                    state.start_value = float(
                        account.get("portfolio_value", 0.0)
                    )
                current_value = float(account.get("portfolio_value", 0.0))
                state.daily_pl = current_value - state.start_value
        except Exception:
            pass

        await asyncio.sleep(1)


@app.route("/status", methods=["GET"])
def status() -> tuple:
    """Return current daemon status."""

    with state_lock:
        data = {
            "mode": state.mode,
            "paused": state.paused,
            "trade_count": state.trade_count,
            "daily_pl": state.daily_pl,
        }
    return jsonify(data)


@app.route("/order", methods=["POST"])
def order() -> tuple:
    """Submit a simple market order."""

    data = request.get_json(force=True)
    symbol = data.get("symbol")
    side = data.get("side", "buy").lower()
    qty = int(data.get("qty", 1))
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    try:
        if side == "sell":
            trade_manager.sell(symbol, qty)
        else:
            trade_manager.buy(symbol, qty)
        with state_lock:
            state.trade_count += 1
        return jsonify({"status": "submitted"})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/pause", methods=["POST"])
def pause() -> tuple:
    """Pause the trading loop."""

    with state_lock:
        state.paused = True
    return jsonify({"status": "paused"})


@app.route("/resume", methods=["POST"])
def resume() -> tuple:
    """Resume the trading loop."""

    with state_lock:
        state.paused = False
    return jsonify({"status": "running"})


@app.route("/mode", methods=["POST"])
def set_mode() -> tuple:
    """Set active trading mode."""

    data = request.get_json(force=True)
    mode = data.get("mode", "stock")
    if mode not in {"stock", "options"}:
        return jsonify({"error": "mode must be 'stock' or 'options'"}), 400
    with state_lock:
        state.mode = mode
    return jsonify({"status": "mode updated", "mode": mode})


def _run_flask() -> None:
    app.run(host="0.0.0.0", port=8000)


def main() -> None:
    loop = asyncio.get_event_loop()
    loop.create_task(trading_loop())
    server_thread = Thread(target=_run_flask, daemon=True)
    server_thread.start()
    loop.run_forever()


if __name__ == "__main__":
    main()
