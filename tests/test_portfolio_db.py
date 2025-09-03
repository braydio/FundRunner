import os
import tempfile

from fundrunner.services.portfolio_db import PortfolioDB


def test_record_and_fetch_yield_history():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "portfolio.db")
        db = PortfolioDB(db_path)
        db.record_lending_rates({"AAPL": 0.02, "MSFT": 0.03}, "2024-01-01T00:00:00Z")
        history = db.get_yield_history("AAPL")
        db.close()
        assert history == [("2024-01-01T00:00:00Z", 0.02)]
