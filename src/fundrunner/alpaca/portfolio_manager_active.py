"""Active portfolio management utilities.

This module provides helper functions for computing portfolio weights,
parsing user supplied target weight specifications and determining
rebalance actions needed to reach those targets.
"""

from __future__ import annotations

from typing import Dict, Iterable


def calculate_weights(positions: Iterable[dict]) -> Dict[str, float]:
    """Calculate weights for each position.

    Args:
        positions: An iterable of dictionaries each containing ``symbol``,
            ``qty`` and ``price`` keys.

    Returns:
        Mapping of symbol to weight (0-1) based on market value.
    """
    market_values: Dict[str, float] = {}
    total_value = 0.0
    for pos in positions:
        qty = float(pos.get("qty", 0))
        price = float(pos.get("price", 0))
        value = qty * price
        market_values[pos["symbol"]] = value
        total_value += value
    if total_value == 0:
        return {sym: 0.0 for sym in market_values}
    return {sym: value / total_value for sym, value in market_values.items()}


def parse_target_weights(spec: str) -> Dict[str, float]:
    """Parse a target weight specification string.

    Supports forms like ``"AAPL:0.6,MSFT:0.4"`` or percentages such as
    ``"AAPL:60%,MSFT:40%"``.  The resulting weights are normalised so they
    sum to 1.

    Args:
        spec: Weight configuration string.

    Returns:
        Mapping of symbol to normalised weight.
    """
    weights: Dict[str, float] = {}
    if not spec:
        return weights
    parts = [p.strip() for p in spec.split(",") if p.strip()]
    for part in parts:
        if ":" in part:
            sym, val = part.split(":", 1)
        elif "=" in part:
            sym, val = part.split("=", 1)
        else:
            continue
        sym = sym.strip().upper()
        val = val.strip()
        if val.endswith("%"):
            weight = float(val.rstrip("%")) / 100
        else:
            weight = float(val)
        weights[sym] = weight
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    return weights


def rebalance_decisions(
    positions: Iterable[dict],
    target_weights: Dict[str, float],
    prices: Dict[str, float],
) -> Dict[str, int]:
    """Determine share adjustments required to hit target weights.

    Args:
        positions: Holdings with ``symbol`` and ``qty`` fields.
        target_weights: Desired portfolio weights for each symbol.
        prices: Latest price per symbol.

    Returns:
        Mapping of symbol to integer quantity difference. Positive values
        indicate shares to buy, negative values indicate shares to sell.
    """
    portfolio_value = sum(
        float(pos.get("qty", 0)) * float(prices.get(pos.get("symbol"), 0))
        for pos in positions
    )
    actions: Dict[str, int] = {}
    for sym, weight in target_weights.items():
        price = prices.get(sym)
        if price in (None, 0):
            continue
        current_qty = next(
            (float(p.get("qty", 0)) for p in positions if p.get("symbol") == sym),
            0.0,
        )
        target_qty = (portfolio_value * weight) / price
        diff = int(round(target_qty - current_qty))
        if diff:
            actions[sym] = diff
    return actions
