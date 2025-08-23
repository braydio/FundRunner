"""Unit tests for the :mod:`dashboard` module."""

from rich.console import Console

from fundrunner.dashboards.dashboard import Dashboard


def test_dashboard_tables_update():
    console = Console()
    dash = Dashboard(console)
    dash.start()
    dash.summary_table.add_row("AAPL", "100", "0.5", "0.1", "Pending")
    dash.refresh()
    dash.stop()
    assert len(dash.summary_table.rows) == 1
