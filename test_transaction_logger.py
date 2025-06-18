import os
import tempfile
import json
import transaction_logger


def test_log_and_read_transactions(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        log_file = os.path.join(tmp, "transactions.log")
        monkeypatch.setattr(transaction_logger, "TRANSACTION_LOG_FILE", log_file)
        trade_details = {"symbol": "AAPL", "qty": 1, "side": "buy"}
        order = {"symbol": "AAPL", "qty": 1, "side": "buy", "status": "filled"}
        transaction_logger.log_transaction(trade_details, order)
        entries = transaction_logger.read_transactions()
        assert len(entries) == 1
        entry = entries[0]
        assert entry["trade_details"]["symbol"] == "AAPL"
        assert entry["order"]["status"] == "filled"
