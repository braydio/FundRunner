"""SQLite-backed storage for portfolio yield history.

This module manages a local SQLite database used to record historical
yield data for tracked symbols.  It is designed as a lightweight
persistence layer for yield farming features.

Integration points
------------------
- :class:`~fundrunner.services.lending_rates.LendingRateService` should call
  :meth:`PortfolioDB.record_lending_rates` after fetching rates to persist
  daily lending yields.
- Portfolio tracking components, such as the portfolio manager, can query
  :meth:`PortfolioDB.get_yield_history` to analyse past returns and
  calculate performance metrics.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple

DB_NAME = "portfolio.db"
SCHEMA = """
CREATE TABLE IF NOT EXISTS yield_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    rate REAL NOT NULL,
    timestamp TEXT NOT NULL
);
"""


class PortfolioDB:
    """Simple SQLite wrapper for storing yield history."""

    def __init__(self, db_path: str | Path = DB_NAME) -> None:
        """Initialise the database connection and ensure schema exists."""

        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables if they do not already exist."""

        with self.conn:
            self.conn.executescript(SCHEMA)

    def record_lending_rates(self, rates: Dict[str, float], timestamp: str) -> None:
        """Insert a batch of lending rates.

        Args:
            rates: Mapping of ticker symbol to lending rate.
            timestamp: ISO 8601 timestamp representing when the rate was
                observed.

        This method is intended to be invoked by
        :class:`~fundrunner.services.lending_rates.LendingRateService` after
        successful rate retrieval.
        """

        with self.conn:
            self.conn.executemany(
                "INSERT INTO yield_history (symbol, rate, timestamp) VALUES (?, ?, ?)",
                [(symbol, rate, timestamp) for symbol, rate in rates.items()],
            )

    def get_yield_history(self, symbol: str) -> List[Tuple[str, float]]:
        """Return ordered list of ``(timestamp, rate)`` entries for a symbol."""

        cursor = self.conn.execute(
            "SELECT timestamp, rate FROM yield_history WHERE symbol = ? ORDER BY timestamp",
            (symbol,),
        )
        return cursor.fetchall()

    def close(self) -> None:
        """Close the underlying SQLite connection."""

        self.conn.close()
