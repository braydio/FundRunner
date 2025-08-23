"""Tests for :mod:`fundrunner.alpaca.trading_bot`."""

import asyncio

from fundrunner.alpaca.trading_bot import TradingBot


def test_confirm_trade_timeout(monkeypatch):
    bot = TradingBot(auto_confirm=False, micro_mode=True, confirm_timeout=0.1)

    async def slow_call(func, *args, **kwargs):
        await asyncio.sleep(0.2)
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", slow_call)
    monkeypatch.setattr("builtins.input", lambda prompt="": "y")

    result = asyncio.run(bot.confirm_trade({"symbol": "AAPL"}))
    assert result is True
