
"""Utility functions for writing trade executions to a log file."""

import json
import os
import datetime

TRANSACTION_LOG_FILE = os.path.join(os.path.dirname(__file__), "transactions.log")

def log_transaction(trade_details, order):
    log_entry = {
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trade_details": trade_details,
        "order": order,
    }
    with open(TRANSACTION_LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")
