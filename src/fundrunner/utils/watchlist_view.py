"""Interactive watchlist viewer using Rich tables."""

from __future__ import annotations

from typing import Sequence

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt

from fundrunner.alpaca.watchlist_manager import WatchlistManager
from fundrunner.alpaca.api_client import AlpacaClient


def _select_watchlist(manager: WatchlistManager, console: Console):
    """Return a watchlist object chosen by the user or ``None`` if unavailable."""
    try:
        watchlists = manager.list_watchlists()
    except Exception as e:  # pragma: no cover - API errors
        console.print(f"[red]Error retrieving watchlists: {e}[/red]")
        return None
    if not watchlists:
        console.print("[red]No watchlists available.[/red]")
        return None
    console.print("[bold blue]Available Watchlists[/bold blue]")
    for idx, wl in enumerate(watchlists, start=1):
        console.print(f"[{idx}] {getattr(wl, 'name', wl.id)} ({wl.id})")
    choice = Prompt.ask(
        "Select watchlist number",
        choices=[str(i) for i in range(1, len(watchlists) + 1)],
    )
    return watchlists[int(choice) - 1]


def _extract_symbols(watchlist) -> Sequence[str]:
    if hasattr(watchlist, "assets"):
        return [getattr(a, "symbol", str(a)) for a in watchlist.assets]
    if hasattr(watchlist, "symbols"):
        return list(watchlist.symbols)
    return []


def main() -> None:
    """Launch the watchlist viewer CLI."""
    console = Console()
    manager = WatchlistManager()
    client = AlpacaClient()

    wl = _select_watchlist(manager, console)
    if wl is None:
        return

    try:
        watchlist = manager.get_watchlist(wl.id)
    except Exception as e:  # pragma: no cover - API errors
        console.print(f"[red]Error retrieving watchlist: {e}[/red]")
        return

    symbols = _extract_symbols(watchlist)
    if not symbols:
        console.print("[red]Watchlist contains no symbols.[/red]")
        return

    table = Table(title=f"Watchlist: {getattr(watchlist, 'name', wl.id)}")
    table.add_column("Symbol")
    table.add_column("Latest Price", justify="right")

    for sym in symbols:
        price = client.get_latest_price(sym)
        price_str = f"${price:.2f}" if price is not None else "N/A"
        table.add_row(sym, price_str)

    console.print(table)
    Prompt.ask("Press Enter to return", default="")


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
