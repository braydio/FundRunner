"""Optimize portfolios using ``PyPortfolioOpt``."""

from pypfopt import EfficientFrontier, expected_returns, risk_models


def optimize_portfolio(prices):
    """
    prices: pd.DataFrame of historical prices (columns = tickers)
    returns: dict of asset weights
    """
    mu = expected_returns.mean_historical_return(prices)
    S = risk_models.sample_cov(prices)
    ef = EfficientFrontier(mu, S)
    _ = ef.max_sharpe()
    return ef.clean_weights()
