import asyncio
import pytest

from dashboards.textual_dashboard import DashboardApp


def test_dashboard_app_populates():
    eval_q = asyncio.Queue()
    trade_q = asyncio.Queue()
    port_q = asyncio.Queue()
    calc_q = asyncio.Queue()
    app = DashboardApp(eval_q, trade_q, port_q, calc_queue=calc_q)

    async def _run():
        async with app.run_test() as pilot:
            await eval_q.put(("AAPL", "100", "0.5", "0.1", "Pending"))
            await trade_q.put(("AAPL", "100", "95", "110", "0.1", "OPEN"))
            await port_q.put(("AAPL", "10", "99", "100", "1.0"))
            await calc_q.put("calc running")
            await asyncio.sleep(0.2)
            assert app.eval_table.row_count == 1
            assert app.trade_table.row_count == 1
            assert app.portfolio_table.row_count == 1
            assert app.calc_log.line_count == 1

    asyncio.run(_run())
