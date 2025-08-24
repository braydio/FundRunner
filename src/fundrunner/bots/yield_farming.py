"""Utilities for building yield‐oriented portfolios.

This module exposes classes and functions to construct portfolios aimed at
generating yield either through securities lending (stock lending) or via
dividend capture strategies.  It sits on top of the existing Alpaca
client and trading abstractions to fetch account information, market data
and execute trades.  The implementation uses public data sources where
possible (e.g. Yahoo Finance) to gather dividend yields and ex‐dividend
dates.  When no reliable API exists for stock lending rates, a stub
function is provided that can be overridden by users.

Key classes
-----------

``YieldFarmingMode``
    Enumeration of supported yield strategies: ``LENDING`` and ``DIVIDEND``.

``YieldFarmer``
    High level orchestrator for building and executing yield portfolios.  It
    fetches necessary data, calculates risk metrics, ranks instruments by
    risk–adjusted yield and delegates order placement to the provided
    ``TradeManager``.

Example
-------

```python
from fundrunner.alpaca.yield_farming import YieldFarmer, YieldFarmingMode
from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.alpaca.trade_manager import TradeManager
from fundrunner.alpaca.risk_manager import RiskManager

# Instantiate dependencies
client = AlpacaClient()
trade_mgr = TradeManager()
risk_mgr = RiskManager()

# Create the yield farmer
farmer = YieldFarmer(client=client, trader=trade_mgr, risk_manager=risk_mgr)

# Build a dividend portfolio using 30% of available cash
farmer.build_dividend_portfolio(["T", "VZ", "XOM"], percent_funds=0.3)

# Build a lending portfolio on a set of tickers
farmer.build_lending_portfolio(["AAPL", "MSFT", "TSLA"], percent_funds=0.2)
```"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.alpaca.risk_manager import RiskManager
from fundrunner.alpaca.trade_manager import TradeManager


class YieldFarmingMode:
    """Enumeration of yield farming strategies."""

    LENDING = "lending"
    DIVIDEND = "dividend"

    @staticmethod
    def from_str(mode: str) -> str:
        m = (mode or "").lower().strip()
        if m in (YieldFarmingMode.LENDING, YieldFarmingMode.DIVIDEND):
            return m
        raise ValueError(f"Unknown yield farming mode '{mode}'")


class YieldFarmer:
    """Construct portfolios optimised for yield generation.

    The farmer combines data from Alpaca (account balance, historical price
    volatility) with public market data (dividend yields, ex‐dividend dates)
    to select securities that maximise yield relative to risk.  Once
    selections have been made it uses the provided ``TradeManager`` to
    execute purchases.
    """

    USER_AGENT = os.getenv(
        "YF_USER_AGENT",
        # Default to a generic browser user agent to avoid being blocked by
        # finance data providers such as Yahoo Finance.
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
    )

    def __init__(
        self,
        client: Optional[AlpacaClient] = None,
        trader: Optional[TradeManager] = None,
        risk_manager: Optional[RiskManager] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.client: AlpacaClient = client or AlpacaClient()
        self.trader: TradeManager = trader or TradeManager()
        self.risk_manager: RiskManager = risk_manager or RiskManager(client=self.client)
        self.logger = logger or logging.getLogger(__name__)

    # ---------------------------------------------------------------------
    # Data retrieval helpers
    # ---------------------------------------------------------------------
    def _fetch_yahoo_quote(self, symbols: List[str]) -> Dict[str, dict]:
        """Fetch summary quote information from Yahoo Finance.

        Returns a mapping from symbol to quote dictionary.  The function
        requests the ``quote`` endpoint of Yahoo Finance which contains
        dividend metrics such as ``trailingAnnualDividendYield`` and
        ``trailingAnnualDividendRate``.  If the call fails or the result is
        missing fields the defaults of ``0.0`` are used.

        Parameters
        ----------
        symbols : list[str]
            Ticker symbols to fetch.

        Returns
        -------
        Dict[str, dict]
            A mapping of ticker to the raw quote data returned from Yahoo.
        """
        # Compose request
        joined = ",".join(symbols)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={joined}"
        headers = {"User-Agent": self.USER_AGENT}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("quoteResponse", {}).get("result", [])
            return {item["symbol"]: item for item in results}
        except Exception as e:
            self.logger.warning(
                "Failed to fetch Yahoo Finance quote for %s: %s", symbols, e
            )
            return {sym: {} for sym in symbols}

    def _fetch_yahoo_calendar(
        self, symbol: str
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Fetch ex‐dividend and earnings dates from Yahoo Finance.

        The ``quoteSummary`` endpoint exposes company events such as the
        upcoming ex‐dividend date and earnings date.  This helper returns
        both fields as ``datetime`` objects if available.

        Parameters
        ----------
        symbol : str
            Ticker symbol.

        Returns
        -------
        tuple(datetime | None, datetime | None)
            A tuple of (ex_dividend_date, earnings_date) or (None, None).
        """
        url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{symbol}?modules=calendarEvents"
        headers = {"User-Agent": self.USER_AGENT}
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            raw = resp.json()
            result = raw.get("quoteSummary", {}).get("result", [])
            if not result:
                return None, None
            cal = result[0].get("calendarEvents", {})
            ex_raw = cal.get("exDividendDate", {}).get("raw")
            earn_raw = None
            # earnings events can be a list of dictionaries with raw timestamp
            if isinstance(cal.get("earnings", {}), dict):
                earn_dates = cal["earnings"].get("earningsDate", [])
                if earn_dates:
                    earn_raw = earn_dates[0].get("raw")
            ex_date = datetime.fromtimestamp(ex_raw) if ex_raw else None
            earn_date = datetime.fromtimestamp(earn_raw) if earn_raw else None
            return ex_date, earn_date
        except Exception as e:
            self.logger.warning(
                "Failed to fetch Yahoo Finance calendar for %s: %s", symbol, e
            )
            return None, None

    def get_dividend_info(self, symbols: Iterable[str]) -> Dict[str, dict]:
        """Return dividend yield and next ex‐dividend date for each symbol.

        Parameters
        ----------
        symbols : Iterable[str]
            Symbols to query.

        Returns
        -------
        dict
            Mapping from symbol to a dictionary with keys:

            ``dividend_yield`` : float
                Annual dividend yield as a fraction (e.g. 0.05 for 5%).

            ``dividend_rate`` : float
                Annual dividend amount per share.

            ``ex_dividend_date`` : datetime | None
                The next ex‐dividend date, or ``None`` if not available.
        """
        symbols = list(symbols)
        quotes = self._fetch_yahoo_quote(symbols)
        info: Dict[str, dict] = {}
        for sym in symbols:
            q = quotes.get(sym, {}) or {}
            rate = q.get("trailingAnnualDividendRate", 0) or 0.0
            # trailingAnnualDividendYield is expressed as a fraction (e.g. 0.02 -> 2%)
            yield_frac = q.get("trailingAnnualDividendYield", 0) or 0.0
            ex_date, _ = self._fetch_yahoo_calendar(sym)
            info[sym] = {
                "dividend_yield": float(yield_frac) if yield_frac else 0.0,
                "dividend_rate": float(rate) if rate else 0.0,
                "ex_dividend_date": ex_date,
            }
        return info

    def get_lending_rates(self, symbols: Iterable[str]) -> Dict[str, float]:
        """Retrieve securities lending rebate rates for the given symbols.

        Alpaca does not currently expose a public API for fully paid securities
        lending rebates.  This method is therefore implemented as a stub and
        returns a constant rate for each symbol by default.  Users can supply
        their own implementation by subclassing ``YieldFarmer`` and
        overriding this method or by patching it at runtime.

        Parameters
        ----------
        symbols : Iterable[str]
            Symbols for which to return lending rates.

        Returns
        -------
        Dict[str, float]
            Mapping from symbol to an annualised lending rate (fraction).  A
            typical range might be 0.005–0.10.  The default implementation
            returns 0.01 (1%) for all inputs.
        """
        default_rate = 0.01
        return {sym: default_rate for sym in symbols}

    # ---------------------------------------------------------------------
    # Risk estimation
    # ---------------------------------------------------------------------
    def compute_volatility(self, symbol: str, days: int = 30) -> float:
        """Compute recent price volatility for a symbol.

        Uses Alpaca's historical bar API via :class:`AlpacaClient.get_bars` to
        fetch daily bars for the last ``days`` days and returns the standard
        deviation of daily returns.  If data is unavailable or the result is
        empty, returns a small positive number to avoid division by zero.

        Parameters
        ----------
        symbol : str
            Ticker symbol.
        days : int, default 30
            Number of days of historical data to consider.

        Returns
        -------
        float
            Annualised volatility estimate (standard deviation of daily
            returns).  A value of 0.02 corresponds to approximately 2% daily
            standard deviation.
        """
        try:
            end_dt = datetime.utcnow()
            start_dt = end_dt - timedelta(days=days)
            start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            end = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            bars = self.client.get_bars(symbol, start=start, end=end)
            if bars.empty:
                return 0.01
            # Compute percentage returns on close prices
            bars = bars.copy()
            bars["Return"] = bars["close"].pct_change()
            vol = bars["Return"].std()
            # If NaN (only one bar) fallback to small value
            return float(vol) if (vol is not None and not np.isnan(vol)) else 0.01
        except Exception as e:
            self.logger.warning("Could not compute volatility for %s: %s", symbol, e)
            return 0.01

    # ---------------------------------------------------------------------
    # Portfolio construction
    # ---------------------------------------------------------------------
    def build_lending_portfolio(
        self,
        symbols: Iterable[str],
        percent_funds: float = 0.1,
        min_rate: float = 0.001,
    ) -> Dict[str, dict]:
        """Construct and execute a lending yield portfolio.

        Given a collection of ticker symbols this method retrieves the
        (possibly stubbed) lending rate for each, estimates recent price
        volatility and calculates a risk–adjusted score defined as
        ``rate / volatility``.  Positions are then sized proportionally to
        these scores such that the sum of notional allocations equals
        ``percent_funds`` of the bot's available cash.  Orders are placed
        through the provided ``TradeManager``.

        Parameters
        ----------
        symbols : Iterable[str]
            Candidate securities to consider.
        percent_funds : float, default 0.1
            Fraction of available cash to allocate (0.0–1.0).
        min_rate : float, default 0.001
            Minimum acceptable lending rate.  Securities with lower rates
            will be ignored.

        Returns
        -------
        dict
            A mapping of symbol to a dict summarising the rate, volatility and
            notional allocated.  This is returned for logging or testing.
        """
        symbols = list(symbols)
        if not symbols:
            self.logger.info("No symbols provided for lending portfolio.")
            return {}
        # Fetch account and compute cash available
        acct = self.client.get_account()
        cash = float(acct.get("cash", 0))
        budget = max(cash * float(percent_funds), 0)
        if budget <= 0:
            self.logger.warning(
                "Insufficient cash (%.2f) to allocate %.2f%% for lending portfolio.",
                cash,
                percent_funds * 100,
            )
            return {}
        # Retrieve rates and volatilities
        rates = self.get_lending_rates(symbols)
        scores: Dict[str, float] = {}
        vols: Dict[str, float] = {}
        for sym in symbols:
            rate = float(rates.get(sym, 0))
            if rate < min_rate:
                continue
            vol = self.compute_volatility(sym)
            vols[sym] = vol
            # Avoid division by zero; if volatility is extremely low assign small value
            vol_safe = vol if vol > 1e-6 else 1e-6
            scores[sym] = rate / vol_safe
        if not scores:
            self.logger.warning(
                "No securities meet the minimum lending rate %.3f", min_rate
            )
            return {}
        # Normalise scores to weights
        total_score = sum(scores.values())
        weights = {s: score / total_score for s, score in scores.items()}
        summary: Dict[str, dict] = {}
        for sym, w in weights.items():
            allocation = budget * w
            # Fetch current price to determine quantity; fallback to allocation if price unavailable
            price = None
            try:
                # Use Alpaca last trade price if available
                last_quote = self.client.get_last_trade(sym)
                price = float(last_quote.get("price")) if last_quote else None
            except Exception:
                price = None
            if not price or price <= 0:
                # As a fallback, use Yahoo Finance price
                q = self._fetch_yahoo_quote([sym]).get(sym, {})
                price = float(q.get("regularMarketPrice", 0) or 0)
            qty = 0
            if price and price > 0:
                qty = allocation / price
            summary[sym] = {
                "lending_rate": rates.get(sym, 0.0),
                "volatility": vols.get(sym, 0.01),
                "weight": w,
                "allocation": allocation,
                "price": price,
                "quantity": qty,
            }
            try:
                # Submit market order; fractional shares allowed only if price not integer; using day TIF
                if qty > 0:
                    self.logger.info(
                        "Placing buy order for %s: qty=%.4f (allocation=%.2f, price=%.2f)",
                        sym,
                        qty,
                        allocation,
                        price,
                    )
                    self.trader.buy(sym, qty, order_type="market", time_in_force="day")
            except Exception as e:
                self.logger.error(
                    "Failed to submit buy order for %s: %s", sym, e, exc_info=True
                )
        return summary

    def build_dividend_portfolio(
        self,
        symbols: Iterable[str],
        percent_funds: float = 0.1,
        active: bool = False,
        min_yield: float = 0.01,
    ) -> Dict[str, dict]:
        """Construct and execute a dividend yield portfolio.

        When ``active`` is ``False`` the method ranks securities by annual
        dividend yield and allocates capital across the top candidates.  When
        ``active`` is ``True`` it looks for the single security with the
        highest dividend yield *and* the nearest upcoming ex‐dividend date,
        allocates the entire ``percent_funds`` budget into it, and returns
        details about the trade.

        Parameters
        ----------
        symbols : Iterable[str]
            Candidate securities to consider.
        percent_funds : float, default 0.1
            Fraction of available cash to allocate (0.0–1.0).
        active : bool, default False
            If true, operate in active dividend capture mode.
        min_yield : float, default 0.01
            Minimum acceptable dividend yield (e.g. 0.01 for 1%).

        Returns
        -------
        dict
            When ``active`` is ``True`` a mapping with a single entry for the
            chosen security; otherwise a mapping of all selected securities to
            their allocation details.
        """
        symbols = list(symbols)
        if not symbols:
            self.logger.info("No symbols provided for dividend portfolio.")
            return {}
        acct = self.client.get_account()
        cash = float(acct.get("cash", 0))
        budget = max(cash * float(percent_funds), 0)
        if budget <= 0:
            self.logger.warning(
                "Insufficient cash (%.2f) to allocate %.2f%% for dividend portfolio.",
                cash,
                percent_funds * 100,
            )
            return {}
        # Retrieve dividend info
        div_info = self.get_dividend_info(symbols)
        # Filter by minimum yield
        candidates: Dict[str, dict] = {
            s: info
            for s, info in div_info.items()
            if info.get("dividend_yield", 0) >= min_yield
        }
        if not candidates:
            self.logger.warning(
                "No securities meet the minimum dividend yield %.3f", min_yield
            )
            return {}
        summary: Dict[str, dict] = {}
        if active:
            # Rank by yield and time until ex‐dividend
            best_sym = None
            best_score = -float("inf")
            now = datetime.utcnow()
            for sym, info in candidates.items():
                yield_val = info.get("dividend_yield", 0)
                ex_date = info.get("ex_dividend_date")
                days_until = (
                    (ex_date - now).total_seconds() / (24 * 3600) if ex_date else 365.0
                )
                # Score: prefer higher yields and sooner ex dates
                score = yield_val / (days_until + 1)
                if score > best_score:
                    best_score = score
                    best_sym = sym
            if not best_sym:
                return {}
            selected = best_sym
            info = candidates[selected]
            # Determine current price
            price = None
            try:
                last_quote = self.client.get_last_trade(selected)
                price = float(last_quote.get("price")) if last_quote else None
            except Exception:
                price = None
            if not price or price <= 0:
                q = self._fetch_yahoo_quote([selected]).get(selected, {})
                price = float(q.get("regularMarketPrice", 0) or 0)
            qty = 0
            if price and price > 0:
                qty = budget / price
            summary[selected] = {
                "dividend_yield": info.get("dividend_yield", 0.0),
                "ex_dividend_date": info.get("ex_dividend_date"),
                "allocation": budget,
                "price": price,
                "quantity": qty,
            }
            try:
                if qty > 0:
                    self.logger.info(
                        "Placing active dividend capture order for %s: qty=%.4f, allocation=%.2f",
                        selected,
                        qty,
                        budget,
                    )
                    self.trader.buy(
                        selected, qty, order_type="market", time_in_force="day"
                    )
            except Exception as e:
                self.logger.error(
                    "Failed to submit active dividend order for %s: %s",
                    selected,
                    e,
                    exc_info=True,
                )
            return summary
        # Passive dividend strategy: weight by yield / volatility
        scores: Dict[str, float] = {}
        vols: Dict[str, float] = {}
        for sym, info in candidates.items():
            yld = info.get("dividend_yield", 0)
            vol = self.compute_volatility(sym)
            vols[sym] = vol
            vol_safe = vol if vol > 1e-6 else 1e-6
            scores[sym] = yld / vol_safe
        total_score = sum(scores.values())
        weights = {s: sc / total_score for s, sc in scores.items()}
        for sym, w in weights.items():
            allocation = budget * w
            price = None
            try:
                last_quote = self.client.get_last_trade(sym)
                price = float(last_quote.get("price")) if last_quote else None
            except Exception:
                price = None
            if not price or price <= 0:
                q = self._fetch_yahoo_quote([sym]).get(sym, {})
                price = float(q.get("regularMarketPrice", 0) or 0)
            qty = 0
            if price and price > 0:
                qty = allocation / price
            summary[sym] = {
                "dividend_yield": candidates[sym].get("dividend_yield", 0.0),
                "ex_dividend_date": candidates[sym].get("ex_dividend_date"),
                "weight": w,
                "allocation": allocation,
                "price": price,
                "quantity": qty,
            }
            try:
                if qty > 0:
                    self.logger.info(
                        "Placing passive dividend order for %s: qty=%.4f (allocation=%.2f)",
                        sym,
                        qty,
                        allocation,
                    )
                    self.trader.buy(sym, qty, order_type="market", time_in_force="day")
            except Exception as e:
                self.logger.error(
                    "Failed to submit dividend order for %s: %s", sym, e, exc_info=True
                )
        return summary

    # ---------------------------------------------------------------------
    # High level execution interface
    # ---------------------------------------------------------------------
    def execute(
        self,
        mode: str,
        symbols: Iterable[str],
        percent_funds: float = 0.1,
        active: bool = False,
    ) -> Dict[str, dict]:
        """Entry point for yield farming strategies.

        Parameters
        ----------
        mode : str
            Either ``"lending"`` or ``"dividend"``.
        symbols : Iterable[str]
            Symbols to consider for the strategy.
        percent_funds : float, default 0.1
            Fraction of available cash to allocate.
        active : bool, default False
            Only used for dividend mode.  When ``True`` runs active capture
            mode.

        Returns
        -------
        dict
            Summary of executed trades and allocations.
        """
        mode_norm = YieldFarmingMode.from_str(mode)
        if mode_norm == YieldFarmingMode.LENDING:
            return self.build_lending_portfolio(symbols, percent_funds)
        elif mode_norm == YieldFarmingMode.DIVIDEND:
            return self.build_dividend_portfolio(symbols, percent_funds, active=active)
        raise AssertionError("Unreachable")
