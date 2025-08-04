import types
from unittest.mock import patch, MagicMock

import watchlist_view


def test_watchlist_main_displays_table():
    wl = types.SimpleNamespace(id="1", name="Test", symbols=["AAPL", "MSFT"])

    with patch("watchlist_view.WatchlistManager") as WM, \
         patch("watchlist_view.AlpacaClient") as AC, \
         patch("watchlist_view.Console") as ConsoleMock, \
         patch("watchlist_view.Prompt.ask", return_value="1"):
        wm_inst = WM.return_value
        wm_inst.list_watchlists.return_value = [wl]
        wm_inst.get_watchlist.return_value = wl

        ac_inst = AC.return_value
        ac_inst.get_latest_price.side_effect = [150.0, 300.0]

        console_inst = ConsoleMock.return_value

        watchlist_view.main()

        assert console_inst.print.called
