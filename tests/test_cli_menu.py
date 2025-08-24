"""CLI navigation tests."""

from unittest.mock import patch

from fundrunner.main import CLI


def test_launch_watchlist_view_calls_main():
    cli = CLI()
    with patch("fundrunner.utils.watchlist_view.main") as mock_view:
        cli.launch_watchlist_view()
        assert mock_view.called


def test_run_menu_triggers_watchlist_view():
    cli = CLI()
    with (
        patch.object(cli, "launch_watchlist_view") as launch_mock,
        patch("fundrunner.main.Prompt.ask", side_effect=["8", "", "0", ""]),
    ):
        try:
            cli.run()
        except SystemExit:
            pass
        launch_mock.assert_called_once()
