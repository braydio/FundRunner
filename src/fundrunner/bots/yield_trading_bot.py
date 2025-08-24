"""Extension of the core TradingBot with yield farming capabilities.

This module defines :class:`YieldTradingBot`, a subclass of the existing
``TradingBot`` that integrates the :class:`YieldFarmer` helper.  It
introduces a new coroutine method ``run_yield_farming`` which can be
invoked to build lending or dividend portfolios on demand.  By
implementing yield farming in a derived class rather than directly
modifying ``TradingBot`` we preserve backwards compatibility with the
existing trading logic while offering an opt‐in path for yield strategies.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, Optional

from fundrunner.alpaca.trading_bot import TradingBot
from fundrunner.alpaca.yield_farming import YieldFarmer, YieldFarmingMode


class YieldTradingBot(TradingBot):
    """Augmented trading bot supporting yield farming modes.

    The constructor delegates to :class:`TradingBot` and then instantiates a
    :class:`YieldFarmer` using the same Alpaca client, trade manager,
    risk manager and logger.  The new coroutine ``run_yield_farming``
    exposes yield strategies in an asynchronous fashion by offloading the
    synchronous yield farming work onto a separate thread via
    ``asyncio.to_thread``.  The caller can await this coroutine without
    blocking the event loop.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        try:
            # Instantiate the farmer with shared dependencies
            self.yield_farmer = YieldFarmer(
                client=self.client,
                trader=self.trader,
                risk_manager=self.risk_manager,
                logger=self.logger,
            )
        except Exception as e:
            # On failure assign None so attribute access doesn't raise
            self.logger.error("Failed to initialise YieldFarmer: %s", e, exc_info=True)
            self.yield_farmer = None

    async def run_yield_farming(
        self,
        mode: str,
        symbols: Iterable[str],
        percent_funds: float = 0.1,
        active: bool = False,
    ) -> Dict[str, dict]:
        """Execute a yield farming strategy asynchronously.

        This coroutine simply calls :meth:`YieldFarmer.execute` in a
        background thread.  It is safe to await this method from within
        the bot's event loop; the heavy lifting of network requests and
        trade execution happens in a thread so as not to block the
        asynchronous runtime.

        Parameters
        ----------
        mode : str
            Either ``"lending"`` or ``"dividend"`` (case insensitive).
        symbols : Iterable[str]
            Candidate securities for the yield strategy.
        percent_funds : float, default 0.1
            Fraction of available cash to allocate to the strategy.
        active : bool, default False
            Only relevant for dividend mode.  When ``True`` uses the
            active dividend capture submode.

        Returns
        -------
        dict
            Summary of executed trades.  The contents of this dict are
            determined by the underlying ``YieldFarmer`` implementation.

        Raises
        ------
        RuntimeError
            If the farmer has not been initialised.
        """
        if not self.yield_farmer:
            raise RuntimeError("YieldFarmer not initialised")
        # Normalise the list of symbols up front
        sym_list = list(symbols)
        return await asyncio.to_thread(
            self.yield_farmer.execute,
            mode,
            sym_list,
            percent_funds,
            active,
        )
