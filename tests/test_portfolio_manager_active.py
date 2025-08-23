"""Tests for :mod:`fundrunner.alpaca.portfolio_manager_active`."""

import pytest

from fundrunner.alpaca.portfolio_manager_active import (
    calculate_weights,
    parse_target_weights,
    rebalance_decisions,
)


def test_calculate_weights_even_split():
    positions = [
        {"symbol": "AAPL", "qty": 10, "price": 100},
        {"symbol": "MSFT", "qty": 5, "price": 200},
    ]
    weights = calculate_weights(positions)
    assert weights["AAPL"] == pytest.approx(0.5)
    assert weights["MSFT"] == pytest.approx(0.5)


def test_parse_target_weights_percentages():
    spec = "AAPL:60%,MSFT:40%"
    weights = parse_target_weights(spec)
    assert weights == {"AAPL": 0.6, "MSFT": 0.4}


def test_rebalance_decisions_generates_actions():
    positions = [
        {"symbol": "AAPL", "qty": 10},
        {"symbol": "MSFT", "qty": 10},
    ]
    target = {"AAPL": 0.7, "MSFT": 0.3}
    prices = {"AAPL": 100, "MSFT": 100}
    actions = rebalance_decisions(positions, target, prices)
    assert actions["AAPL"] == 4
    assert actions["MSFT"] == -4
