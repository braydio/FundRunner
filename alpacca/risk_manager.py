
# risk_manager.py
import yfinance as yf

class RiskManager:
    def __init__(self, base_allocation_limit=0.05, base_risk_threshold=0.6, minimum_allocation=0.01):
        """
        Args:
            base_allocation_limit (float): Default fraction of buying power to allocate per trade.
            base_risk_threshold (float): Default minimum simulated probability of profit required.
            minimum_allocation (float): Minimum allocation floor.
        """
        self.base_allocation_limit = base_allocation_limit
        self.base_risk_threshold = base_risk_threshold
        self.minimum_allocation = minimum_allocation

    def adjust_parameters(self, symbol):
        """
        Adjusts allocation and risk threshold parameters based on recent volatility and volume.
        Args:
            symbol (str): The ticker symbol for which to compute adjustments.
        Returns:
            (tuple): (adjusted_allocation_limit, adjusted_risk_threshold)
        """
        try:
            data = yf.download(symbol, period="1mo", interval="1d")
            if data.empty:
                return self.base_allocation_limit, self.base_risk_threshold

            # Compute volatility as the standard deviation of daily returns.
            data['Return'] = data['Close'].pct_change()
            volatility = data['Return'].std()

            # Adjust allocation: higher volatility reduces allocation.
            # Using a base ratio of 0.02 as a typical volatility level.
            adjusted_allocation = self.base_allocation_limit * (0.02 / volatility) if volatility > 0 else self.base_allocation_limit
            # Clamp to a minimum allocation floor.
            adjusted_allocation = max(adjusted_allocation, self.minimum_allocation)

            # Incorporate volume: if average volume is low, reduce allocation further.
            avg_volume = data['Volume'].mean()
            if avg_volume < 1e6:
                adjusted_allocation *= 0.8  # reduce allocation by 20%

            # Adjust risk threshold: higher volatility demands a higher probability of profit.
            adjusted_risk_threshold = self.base_risk_threshold + (volatility * 10)
            adjusted_risk_threshold = min(adjusted_risk_threshold, 0.9)

            return adjusted_allocation, adjusted_risk_threshold
        except Exception:
            # In case of any error, return the base parameters.
            return self.base_allocation_limit, self.base_risk_threshold

