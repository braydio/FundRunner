
"""Utilities for managing trade risk based on recent market data.

The module exposes :class:`RiskManager`, which can derive allocation limits
from historical volatility and volume.  These limits are used by
``PortfolioManager`` to cap position sizes during rebalancing.
"""

from datetime import datetime, timedelta

from fundrunner.alpaca.api_client import AlpacaClient

class RiskManager:
    def __init__(
        self,
        base_allocation_limit: float = 0.05,
        base_risk_threshold: float = 0.6,
        minimum_allocation: float = 0.01,
        client: AlpacaClient | None = None,
    ) -> None:
        """Initialize risk parameters and API client.

        Args:
            base_allocation_limit: Default fraction of buying power to allocate per trade.
            base_risk_threshold: Default minimum simulated probability of profit required.
            minimum_allocation: Minimum allocation floor.
            client: Optional ``AlpacaClient`` used to fetch historical bars.
        """
        self.base_allocation_limit = base_allocation_limit
        self.base_risk_threshold = base_risk_threshold
        self.minimum_allocation = minimum_allocation
        self.client = client or AlpacaClient()

    def _recent_bars(self, symbol: str):
        """Return the last 30 days of bars for ``symbol``."""

        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=30)
        start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return self.client.get_bars(symbol, start=start, end=end)

    def _allocation_from_data(self, data):
        """Compute allocation limit and volatility from historical ``data``."""

        if data.empty:
            return self.base_allocation_limit, 0.0

        data["Return"] = data["close"].pct_change()
        volatility = data["Return"].std()

        if volatility > 0:
            multiplier = min(0.02 / volatility, 1)
            adjusted_allocation = self.base_allocation_limit * multiplier
        else:
            adjusted_allocation = self.base_allocation_limit

        adjusted_allocation = max(adjusted_allocation, self.minimum_allocation)

        avg_volume = data["volume"].mean()
        if avg_volume < 1e6:
            adjusted_allocation *= 0.8  # reduce allocation by 20%

        return adjusted_allocation, volatility

    def allocation_limit(self, symbol: str) -> float:
        """Return the volatility- and volume-adjusted allocation limit for ``symbol``."""

        try:
            data = self._recent_bars(symbol)
            adjusted_allocation, _ = self._allocation_from_data(data)
            return adjusted_allocation
        except Exception:
            return self.base_allocation_limit

    def adjust_parameters(self, symbol):
        """Return allocation and risk threshold for ``symbol`` based on market data."""

        try:
            data = self._recent_bars(symbol)
            adjusted_allocation, volatility = self._allocation_from_data(data)
            adjusted_risk_threshold = self.base_risk_threshold + (volatility * 10)
            adjusted_risk_threshold = min(adjusted_risk_threshold, 0.9)
            return adjusted_allocation, adjusted_risk_threshold
        except Exception:
            return self.base_allocation_limit, self.base_risk_threshold

