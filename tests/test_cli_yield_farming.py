import io

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
        LendingRateService, "get_rates", lambda self, symbols: {"AAPL": 0.02, "MSFT": 0.015}
    )

    cli.run_yield_farming()
    output = cli.console.file.getvalue()
    assert "AAPL" in output and "0.020" in output


def test_run_yield_farming_handles_service_error(monkeypatch):
    cli = _setup_cli()
    responses = iter(["lending", "AAPL", "0.5", "1"])
    monkeypatch.setattr(Prompt, "ask", lambda *a, **k: next(responses))

    def boom(self, symbols):
        raise FundRunnerError("boom")

    monkeypatch.setattr(LendingRateService, "get_rates", boom)

    cli.run_yield_farming()
    output = cli.console.file.getvalue()
    assert "Failed to fetch lending rates" in output

