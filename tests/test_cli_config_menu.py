import builtins
from unittest.mock import patch

from fundrunner.main import CLI


def test_config_menu_prints_table():
    with (
        patch("fundrunner.main.Console") as ConsoleMock,
        patch("fundrunner.main.Prompt.ask", return_value=""),
    ):
        cli = CLI()
        cli.view_config_menu()
        assert ConsoleMock.return_value.print.called
