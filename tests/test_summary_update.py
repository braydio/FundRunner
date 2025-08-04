import asyncio

from alpaca.trading_bot import TradingBot
from dashboards.textual_dashboard import DashboardApp


def test_update_summary_row_does_not_add_rows():
    bot = TradingBot()
    bot.eval_queue = asyncio.Queue()
    bot.trade_queue = asyncio.Queue()
    bot.portfolio_queue = asyncio.Queue()
    bot.calc_queue = asyncio.Queue()
    bot.dashboard_app = DashboardApp(
        bot.eval_queue,
        bot.trade_queue,
        bot.portfolio_queue,
        calc_queue=bot.calc_queue,
    )

    async def _run():
        async with bot.dashboard_app.run_test():
            bot.init_summary_table(["AAPL"])
            await asyncio.sleep(0.1)
            assert bot.dashboard_app.eval_table.row_count == 1
            before = bot.dashboard_app.eval_table.row_count
            bot.update_summary_row("AAPL", "100", "0.6", "0.1", "Buy")
            await asyncio.sleep(0.1)
            assert bot.dashboard_app.eval_table.row_count == before
            col_key = list(bot.dashboard_app.eval_table.columns.keys())[4]
            cell = bot.dashboard_app.eval_table.get_cell(
                bot.summary_row_keys["AAPL"], col_key
            )
            assert str(cell) == "Buy"
            # Update again to ensure row replacement not addition
            bot.update_summary_row("AAPL", "101", "0.7", "0.2", "Hold")
            await asyncio.sleep(0.1)
            assert bot.dashboard_app.eval_table.row_count == before
            cell = bot.dashboard_app.eval_table.get_cell(
                bot.summary_row_keys["AAPL"], col_key
            )
            assert str(cell) == "Hold"

    asyncio.run(_run())
