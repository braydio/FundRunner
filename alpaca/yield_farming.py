"""Utilities for constructing yield-focused portfolios."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Tuple

import requests

from config import API_KEY, API_SECRET, BASE_URL
from .api_client import AlpacaClient

logger = logging.getLogger(__name__)


class YieldFarmer:
    """Automates basic stock lending and dividend yield strategies."""

    def __init__(self, client: AlpacaClient | None = None):
        self.client = client or AlpacaClient()

    # ----------------------------
    # Stock Lending Helpers
    # ----------------------------
    def fetch_lending_rates(self) -> Dict[str, float]:
        """Return stock lending rates keyed by symbol.

        Alpaca does not currently expose public stock lending endpoints. This
        method attempts to call a hypothetical ``/v2/portfolio/stock_lending``
        endpoint and falls back to stub data if the request fails.
        """
        endpoint = f"{BASE_URL}/v2/portfolio/stock_lending"
        headers = {
            "APCA-API-KEY-ID": API_KEY,
            "APCA-API-SECRET-KEY": API_SECRET,
        }
        try:
            resp = requests.get(endpoint, headers=headers, timeout=10)
            if resp.ok:
                data = resp.json()
                return {
                    item["symbol"]: float(item.get("rate", 0))
                    for item in data.get("rates", [])
                }
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("Failed to fetch lending rates: %s", exc)
        # Fallback stub
        return {"AAPL": 0.02, "MSFT": 0.015, "GOOGL": 0.012}

    def build_lending_portfolio(
        self, allocation_percent: float = 0.5, top_n: int = 3
    ) -> List[Dict[str, float]]:
        """Select high-rate lending stocks using available cash."""
        account = self.client.get_account()
        cash = float(account.get("cash", 0))
        invest = cash * allocation_percent
        rates = self.fetch_lending_rates()
        picks = sorted(rates.items(), key=lambda x: x[1], reverse=True)[:top_n]
        if not picks:
            return []
        total_rate = sum(r for _, r in picks)
        portfolio = []
        for sym, rate in picks:
            weight = rate / total_rate if total_rate else 1 / len(picks)
            alloc = invest * weight
            price = self.client.get_latest_price(sym) or 1
            qty = int(alloc / price)
            portfolio.append({"symbol": sym, "qty": qty, "lending_rate": rate})
        return portfolio

    # ----------------------------
    # Dividend Helpers
    # ----------------------------
    def fetch_dividend_info(self, symbol: str) -> Tuple[float, datetime | None]:
        """Return (dividend_yield, next_ex_dividend_date) for ``symbol``."""
        url = (
            "https://query2.finance.yahoo.com/v10/finance/quoteSummary/"
            f"{symbol}?modules=calendarEvents,summaryDetail"
        )
        try:
            resp = requests.get(url, timeout=10)
            if resp.ok:
                data = resp.json()["quoteSummary"]["result"][0]
                details = data.get("summaryDetail", {})
                cal = data.get("calendarEvents", {})
                yield_raw = details.get("dividendYield", {}).get("raw", 0)
                date_str = cal.get("exDividendDate", {}).get("fmt")
                next_date = (
                    datetime.strptime(date_str, "%Y-%m-%d") if date_str else None
                )
                return float(yield_raw or 0), next_date
        except Exception as exc:  # pragma: no cover - network failure
            logger.warning("Failed to fetch dividend info for %s: %s", symbol, exc)
        return 0.0, None

    def build_dividend_portfolio(
        self,
        symbols: List[str],
        allocation_percent: float = 0.5,
        active: bool = False,
    ) -> List[Dict[str, float]]:
        """Construct a portfolio focused on dividend yield."""
        account = self.client.get_account()
        cash = float(account.get("cash", 0))
        invest = cash * allocation_percent
        info = []
        for sym in symbols:
            yield_rate, next_date = self.fetch_dividend_info(sym)
            if yield_rate:
                info.append((sym, yield_rate, next_date))
        if not info:
            return []
        portfolio: List[Dict[str, float]] = []
        if active:
            info.sort(key=lambda x: (x[2] or datetime.max))
            sym, yld, nxt = info[0]
            price = self.client.get_latest_price(sym) or 1
            qty = int(invest / price)
            portfolio.append(
                {
                    "symbol": sym,
                    "qty": qty,
                    "dividend_yield": yld,
                    "next_ex_div": nxt.strftime("%Y-%m-%d") if nxt else None,
                }
            )
            return portfolio
        info.sort(key=lambda x: x[1], reverse=True)
        weight = invest / len(info)
        for sym, yld, nxt in info:
            price = self.client.get_latest_price(sym) or 1
            qty = int(weight / price)
            portfolio.append(
                {
                    "symbol": sym,
                    "qty": qty,
                    "dividend_yield": yld,
                    "next_ex_div": nxt.strftime("%Y-%m-%d") if nxt else None,
                }
            )
        return portfolio
