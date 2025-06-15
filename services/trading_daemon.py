"""Automated trading scheduler and risk guardrails.

This daemon activates trading during market hours, enforces basic daily
limits and persists metrics between runs. Trade statistics are stored in a
JSON file and reset at the start of each trading day.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Optional

from alpaca.trading_bot import TradingBot


@dataclass
class TradingLimits:
    """Configuration for trading risk limits."""

    max_trades_per_hour: int = 10
    daily_stop_loss: float = 1000.0
    daily_profit_target: float = 1000.0


@dataclass
class TradingSchedule:
    """Configuration for trading start and end times in UTC."""

    start: time = time(8, 0)  # pre-market open
    end: time = time(20, 0)  # after extended hours


@dataclass
class TradingState:
    """Persistent metrics for a single trading day."""

    date: str = ""
    trade_count: int = 0
    profit: float = 0.0

    def reset(self, date: str) -> None:
        self.date = date
        self.trade_count = 0
        self.profit = 0.0


class TradingDaemon:
    """Schedules :class:`TradingBot` runs and tracks daily metrics."""

    def __init__(
        self,
        bot: TradingBot,
        limits: Optional[TradingLimits] = None,
        schedule: Optional[TradingSchedule] = None,
        state_path: str | Path = "trading_state.json",
    ) -> None:
        self.bot = bot
        self.limits = limits or TradingLimits()
        self.schedule = schedule or TradingSchedule()
        self.state_file = Path(state_path)
        self.state = TradingState()
        self._last_hour: Optional[datetime] = None
        self.load_state()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_time(value: str) -> time:
        hour, minute = (int(x) for x in value.split(":", 1))
        return time(hour, minute)

    @classmethod
    def from_config(cls, bot: TradingBot, cfg) -> "TradingDaemon":
        """Create a daemon using values from :mod:`config`."""
        limits = TradingLimits(
            max_trades_per_hour=cfg.MAX_TRADES_PER_HOUR,
            daily_stop_loss=cfg.DAILY_STOP_LOSS,
            daily_profit_target=cfg.DAILY_PROFIT_TARGET,
        )
        schedule = TradingSchedule(
            start=cls._parse_time(cfg.PRE_MARKET_START),
            end=cls._parse_time(cfg.EXTENDED_HOURS_END),
        )
        return cls(bot, limits=limits, schedule=schedule)

    def load_state(self) -> None:
        if self.state_file.exists():
            try:
                with self.state_file.open("r") as f:
                    data = json.load(f)
                self.state = TradingState(**data)
            except Exception:
                self.state = TradingState()
        today = datetime.now(timezone.utc).date().isoformat()
        if self.state.date != today:
            self.state.reset(today)
            self.save_state()

    def save_state(self) -> None:
        with self.state_file.open("w") as f:
            json.dump(self.state.__dict__, f)

    def record_trade(self, profit: float) -> None:
        """Record a trade and update persistent metrics."""
        self.load_state()
        self.state.trade_count += 1
        self.state.profit += profit
        self.save_state()

    def _within_schedule(self, now: datetime) -> bool:
        return self.schedule.start <= now.time() <= self.schedule.end

    def limits_hit(self) -> bool:
        """Return ``True`` if daily risk limits have been exceeded."""
        if self.state.profit <= -self.limits.daily_stop_loss:
            return True
        if self.state.profit >= self.limits.daily_profit_target:
            return True
        if self.state.trade_count >= self.limits.max_trades_per_hour:
            hour_start = datetime.now(timezone.utc).replace(
                minute=0, second=0, microsecond=0
            )
            if self._last_hour != hour_start:
                self._last_hour = hour_start
                self.state.trade_count = 0
                self.save_state()
            else:
                return True
        return False

    async def run(
        self, symbols: Optional[list[str]] = None, poll_interval: int = 300
    ) -> None:
        """Continuously run trading sessions when schedule allows."""
        while True:
            self.load_state()
            now = datetime.now(timezone.utc)
            if self._within_schedule(now) and not self.limits_hit():
                await self.bot.run(symbols)
            await asyncio.sleep(poll_interval)
