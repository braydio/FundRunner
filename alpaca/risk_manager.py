
# risk_manager.py
"""Utilities for adjusting risk parameters based on recent market data."""

from datetime import datetime, timedelta

from alpaca.api_client import AlpacaClient

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

    def adjust_parameters(self, symbol):
        """
        Adjusts allocation and risk threshold parameters based on recent volatility and volume.
        Args:
            symbol (str): The ticker symbol for which to compute adjustments.
        Returns:
            (tuple): (adjusted_allocation_limit, adjusted_risk_threshold)
        """
        try:
            end = datetime.utcnow().isoformat()
            start = (datetime.utcnow() - timedelta(days=30)).isoformat()
            data = self.client.get_bars(symbol, start=start, end=end)
            if data.empty:
                return self.base_allocation_limit, self.base_risk_threshold

            # Compute volatility as the standard deviation of daily returns.
            data["Return"] = data["close"].pct_change()
            volatility = data['Return'].std()

            if volatility > 0:
                # Instead of scaling allocation upward when volatility is low,
                # we cap the multiplier at 1 so that allocation never exceeds the base allocation.
                multiplier = min(0.02 / volatility, 1)
                adjusted_allocation = self.base_allocation_limit * multiplier
            else:
                adjusted_allocation = self.base_allocation_limit

            # Clamp to a minimum allocation floor.
            adjusted_allocation = max(adjusted_allocation, self.minimum_allocation)

            # Incorporate volume: if average volume is low, reduce allocation further.
            avg_volume = data['volume'].mean()
            if avg_volume < 1e6:
                adjusted_allocation *= 0.8  # reduce allocation by 20%

            # Adjust risk threshold: higher volatility demands a higher probability of profit.
            adjusted_risk_threshold = self.base_risk_threshold + (volatility * 10)
            adjusted_risk_threshold = min(adjusted_risk_threshold, 0.9)

            return adjusted_allocation, adjusted_risk_threshold
        except Exception:
            # In case of any error, return the base parameters.
            return self.base_allocation_limit, self.base_risk_threshold

