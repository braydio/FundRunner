
"""Portfolio utilities built on top of :class:`AlpacaClient`.

This module now exposes lightweight helpers for inspecting current
positions as well as performing rudimentary portfolio management such as
calculating weights, determining targets and rebalancing when allocations
drift beyond a threshold.  The last set of target weights is persisted to
``portfolio_state.json`` so subsequent sessions can resume from the same
targets.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.utils.gpt_client import ask_gpt


class PortfolioManager:
    """High-level portfolio inspection and management helpers."""

    STATE_FILE = Path("portfolio_state.json")

    def __init__(self) -> None:
        self.client = AlpacaClient()

    def view_account(self) -> Dict:
        """Return sanitized account information from Alpaca."""

        return self.client.get_account()

    def view_positions(self) -> Iterable[Dict]:
        """Return the list of open positions with pricing fields."""

        return self.client.list_positions()

    def view_position(self, symbol: str) -> Optional[Dict]:
        """Return position information for ``symbol`` if it exists."""

        return self.client.get_position(symbol)

    # ------------------------------------------------------------------
    # Allocation helpers
    # ------------------------------------------------------------------
    def calculate_current_weights(self) -> Dict[str, float]:
        """Return the current portfolio weights for each position."""

        positions = self.view_positions()
        total = sum(p.get("market_value", 0.0) for p in positions)
        if total == 0:
            return {}
        return {
            p["symbol"]: p.get("market_value", 0.0) / total for p in positions
        }

    def determine_target_weights(
        self,
        symbols: Optional[Iterable[str]] = None,
        use_llm: bool = False,
        prompt: str | None = None,
    ) -> Dict[str, float]:
        """Determine and persist target weights for the portfolio.

        Parameters
        ----------
        symbols:
            Iterable of symbols to allocate.  If omitted the current
            position symbols are used.
        use_llm:
            When ``True`` an LLM is queried for weight suggestions using
            :func:`ask_gpt`.  The LLM should return a JSON mapping of
            symbol to target weight.  If parsing fails we fall back to an
            equal-weight allocation.
        prompt:
            Optional prompt to send to the LLM when ``use_llm`` is true.
        """

        if symbols is None:
            symbols = [p["symbol"] for p in self.view_positions()]

        symbols = list(symbols)
        if not symbols:
            targets: Dict[str, float] = {}
        elif use_llm:
            response = ask_gpt(prompt or "Provide target weights as JSON")
            try:
                targets = json.loads(response) if response else {}
            except Exception:
                targets = {s: 1 / len(symbols) for s in symbols}
        else:
            targets = {s: 1 / len(symbols) for s in symbols}

        # Persist the targets for later sessions
        try:
            self.STATE_FILE.write_text(json.dumps(targets))
        except Exception:
            pass
        return targets

    def load_target_weights(self) -> Optional[Dict[str, float]]:
        """Load persisted target weights from :data:`STATE_FILE`."""

        if self.STATE_FILE.exists():
            try:
                return json.loads(self.STATE_FILE.read_text())
            except Exception:
                return None
        return None

    def rebalance_portfolio(
        self, target_weights: Dict[str, float], threshold: float = 0.05
    ) -> None:
        """Issue orders to rebalance the portfolio towards ``target_weights``.

        Orders are submitted whenever the absolute difference between the
        current weight and the target weight exceeds ``threshold``.  Order
        quantities are computed based on the difference in market value
        using current prices from :func:`view_positions`.
        """

        positions = {p["symbol"]: p for p in self.view_positions()}
        current_weights = self.calculate_current_weights()
        total_value = sum(p.get("market_value", 0.0) for p in positions.values())

        for symbol, target_weight in target_weights.items():
            current_weight = current_weights.get(symbol, 0.0)
            drift = current_weight - target_weight
            if abs(drift) <= threshold:
                continue

            position = positions.get(symbol)
            price = position.get("current_price", 0.0) if position else 0.0
            current_value = position.get("market_value", 0.0) if position else 0.0
            target_value = target_weight * total_value
            diff_value = target_value - current_value
            if price == 0:
                continue
            qty = diff_value / price
            side = "buy" if qty > 0 else "sell"
            self.client.submit_order(symbol, abs(qty), side, "market", "day")

    def run_active_management(
        self, interval_seconds: int = 60, threshold: float = 0.05
    ) -> None:
        """Continuously rebalance the portfolio at ``interval_seconds``.

        The method loads previously saved target weights or generates an
        equal-weight allocation if none exist.  It then rebalances the
        portfolio every ``interval_seconds`` seconds until interrupted.
        """

        while True:
            targets = self.load_target_weights()
            if targets is None:
                targets = self.determine_target_weights()
            self.rebalance_portfolio(targets, threshold)
            time.sleep(interval_seconds)


