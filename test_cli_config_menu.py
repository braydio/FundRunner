import builtins
from unittest.mock import patch

from main import CLI


def test_config_menu_prints_table():
    with patch("main.Console") as ConsoleMock, patch("main.Prompt.ask", return_value=""):
        cli = CLI()
        cli.view_config_menu()
        assert ConsoleMock.return_value.print.called
