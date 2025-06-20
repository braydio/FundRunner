"""ChatGPT-driven trading controller."""

import json
import logging
from typing import Any, Dict, List

from alpaca.portfolio_manager import PortfolioManager
from alpaca.trade_manager import TradeManager
from gpt_client import ask_gpt

logger = logging.getLogger(__name__)


def expected_value(win_prob: float, avg_win: float, avg_loss: float) -> float:
    """Compute expected value using probability-weighted outcomes."""
    loss_prob = 1 - win_prob
    return (win_prob * avg_win) - (loss_prob * avg_loss)


def kelly_fraction(win_prob: float, win_loss_ratio: float) -> float:
    """Return the Kelly fraction for a trade."""
    if win_loss_ratio == 0:
        return 0.0
    return win_prob - (1 - win_prob) / win_loss_ratio


def compute_risk_metrics(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    """Derive simple risk metrics from current positions."""
    if not positions:
        return {"expected_value": 0.0, "kelly_fraction": 0.0}

    winners: List[float] = []
    losers: List[float] = []
    for pos in positions:
        pct = pos.get("unrealized_pl_percent", 0)
        value = pos.get("market_value", 0)
        profit = value * (pct / 100)
        if profit >= 0:
            winners.append(profit)
        else:
            losers.append(abs(profit))

    win_prob = len(winners) / len(positions)
    avg_win = sum(winners) / len(winners) if winners else 0.0
    avg_loss = sum(losers) / len(losers) if losers else 0.0
    ev = expected_value(win_prob, avg_win, avg_loss) if (avg_win or avg_loss) else 0.0
    win_loss_ratio = avg_win / avg_loss if avg_loss else 0.0
    kelly = kelly_fraction(win_prob, win_loss_ratio) if win_loss_ratio else 0.0
    return {"expected_value": ev, "kelly_fraction": kelly}


def run_chatgpt_controller(max_cycles: int = 3) -> None:
    """Control trading via ChatGPT-provided actions."""

    portfolio = PortfolioManager()
    trader = TradeManager()

    request = "more_data"
    cycles = 0

    while cycles < max_cycles and request == "more_data":
        account = portfolio.view_account()
        positions = portfolio.view_positions()
        metrics = compute_risk_metrics(positions)

        prompt = (
            "You are a trading assistant.\n"
            f"Account: {account}\n"
            f"Positions: {positions}\n"
            f"Risk metrics: {metrics}\n"
            "Respond with JSON {\"actions\": [{...}], \"request\": \"more_data\" or \"done\"}."
        )

        response = ask_gpt(prompt)
        if not response:
            logger.error("No response from GPT")
            break
        try:
            data = json.loads(response)
        except json.JSONDecodeError:
            logger.error("Failed to parse GPT response: %s", response)
            break

        actions = data.get("actions", [])
        for action in actions:
            act_type = action.get("action")
            symbol = action.get("symbol")
            qty = action.get("quantity") or action.get("qty")
            if not symbol or qty is None:
                continue
            if act_type == "buy":
                trader.buy(symbol, qty)
            elif act_type == "sell":
                trader.sell(symbol, qty)
        request = data.get("request", "done")
        cycles += 1
