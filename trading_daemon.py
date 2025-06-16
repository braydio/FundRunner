"""HTTP trading daemon for FundRunner.

This module exposes a minimal FastAPI application with endpoints
for checking daemon status, switching trading modes, and submitting
orders through the :class:`alpaca.trade_manager.TradeManager`.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from alpaca.trade_manager import TradeManager
from config import MICRO_MODE, SIMULATION_MODE

app = FastAPI(title="FundRunner Trading Daemon")

trade_manager = TradeManager()

class OrderRequest(BaseModel):
    """Payload for submitting trade orders."""

    symbol: str
    qty: int
    side: str  # buy or sell
    order_type: str = "market"
    time_in_force: str = "gtc"

@app.get("/status")
async def status():
    """Return basic health information."""

    return {
        "message": "daemon running",
        "micro_mode": MICRO_MODE,
        "simulation_mode": SIMULATION_MODE,
    }

@app.post("/orders")
async def submit_order(order: OrderRequest):
    """Submit a trade order via :class:`TradeManager`."""

    side = order.side.lower()
    if side not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail="side must be 'buy' or 'sell'")

    if side == "buy":
        result = trade_manager.buy(
            order.symbol, order.qty, order.order_type, order.time_in_force
        )
    else:
        result = trade_manager.sell(
            order.symbol, order.qty, order.order_type, order.time_in_force
        )
    return {"status": "submitted", "order_id": getattr(result, "id", None)}

