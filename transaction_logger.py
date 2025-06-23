
"""Transaction logging helpers.

This module provides small utilities for recording trade information to a
``transactions.log`` file and reading those records back for display.  Each
entry is stored as one JSON object per line with a UTC timestamp.
"""

import json
import os
import datetime

TRANSACTION_LOG_FILE = os.path.join(os.path.dirname(__file__), "transactions.log")

def log_transaction(trade_details, order):
    """Append a trade execution record to ``transactions.log``.

    Parameters
    ----------
    trade_details : dict
        Dictionary describing the trade parameters (symbol, qty, side, etc.).
    order : dict
        Order information returned from the broker API.
    """

    log_entry = {
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trade_details": trade_details,
        "order": order,
    }
    with open(TRANSACTION_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def read_transactions(limit=10):
    """Return the most recent transaction records.

    Parameters
    ----------
    limit : int, optional
        Maximum number of records to return. Defaults to 10.

    Returns
    -------
    list[dict]
        Parsed transaction log entries.
    """

    if not os.path.exists(TRANSACTION_LOG_FILE):
        return []
    with open(TRANSACTION_LOG_FILE, "r") as f:
        lines = f.readlines()
    lines = lines[-limit:]
    return [json.loads(l) for l in lines]
