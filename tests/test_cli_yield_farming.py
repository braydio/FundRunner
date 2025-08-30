"""CLI tests covering yield farming option and error handling."""

import io
import sys

import pytest
from rich.prompt import Prompt
from rich.console import Console

from fundrunner.main import CLI
from fundrunner.services.lending_rates import LendingRateService
from fundrunner.utils.error_handling import FundRunnerError


def _setup_cli():
    cli = CLI.__new__(CLI)
    cli.console = Console(file=io.StringIO())
    return cli


def test_run_yield_farming_displays_rates(monkeypatch):
    cli = _setup_cli()
    responses = iter(["lending", "AAPL,MSFT", "0.5", "2"])
    monkeypatch.setattr(Prompt, "ask", lambda *a, **k: next(responses))
    monkeypatch.setattr(
        LendingRateService,
        "get_rates",
        lambda self, symbols: {"AAPL": 0.02, "MSFT": 0.015},
    )
    called = {}

    def fake_success(symbols, rates):
        called["success"] = (symbols, rates)

    monkeypatch.setattr("fundrunner.main.log_lending_rate_success", fake_success)

    cli.run_yield_farming()
    output = cli.console.file.getvalue()
    assert "AAPL" in output and "0.020" in output
    assert called["success"] == (["AAPL", "MSFT"], {"AAPL": 0.02, "MSFT": 0.015})


def test_run_yield_farming_handles_service_error(monkeypatch):
    cli = _setup_cli()
    responses = iter(["lending", "AAPL", "0.5", "1"])
    monkeypatch.setattr(Prompt, "ask", lambda *a, **k: next(responses))

    def boom(self, symbols):
        raise FundRunnerError("boom")

    monkeypatch.setattr(LendingRateService, "get_rates", boom)
    called = {}

    def fake_failure(symbols, error):
        called["failure"] = (symbols, str(error))

    monkeypatch.setattr("fundrunner.main.log_lending_rate_failure", fake_failure)

    cli.run_yield_farming()
    output = cli.console.file.getvalue()
    assert "Failed to fetch lending rates" in output
    assert called["failure"] == (["AAPL"], "boom")


def test_menu_option_9_displays_rates(monkeypatch):
    """Selecting option 9 from the main menu shows lending rates."""

    cli = _setup_cli()
    monkeypatch.setattr(CLI, "show_portfolio_status", lambda self: None)
    monkeypatch.setattr(CLI, "print_menu", lambda self: None)

    responses = iter([
        "",  # open main menu
        "9",
        "lending",
        "AAPL",
        "0.5",
        "1",
        "",
        "0",
    ])
    monkeypatch.setattr(Prompt, "ask", lambda *a, **k: next(responses))
    monkeypatch.setattr(
        LendingRateService, "get_rates", lambda self, symbols: {"AAPL": 0.02}
    )
    monkeypatch.setattr(sys, "exit", lambda *a, **k: (_ for _ in ()).throw(SystemExit()))

    with pytest.raises(SystemExit):
        cli.run()

    output = cli.console.file.getvalue()
    assert "AAPL" in output and "0.020" in output


def test_menu_option_9_handles_service_error(monkeypatch):
    """Main menu option 9 surfaces lending rate errors to the user."""

    cli = _setup_cli()
    monkeypatch.setattr(CLI, "show_portfolio_status", lambda self: None)
    monkeypatch.setattr(CLI, "print_menu", lambda self: None)

    responses = iter([
        "",
        "9",
        "lending",
        "AAPL",
        "0.5",
        "1",
        "",
        "0",
    ])
    monkeypatch.setattr(Prompt, "ask", lambda *a, **k: next(responses))

    def boom(self, symbols):
        raise FundRunnerError("boom")

    monkeypatch.setattr(LendingRateService, "get_rates", boom)
    monkeypatch.setattr(sys, "exit", lambda *a, **k: (_ for _ in ()).throw(SystemExit()))

    with pytest.raises(SystemExit):
        cli.run()

    output = cli.console.file.getvalue()
    assert "Failed to fetch lending rates" in output
