.
├── __pycache__
│   ├── api_client.cpython-313.pyc
│   ├── chatgpt_advisor.cpython-313.pyc
│   ├── chatgpt_trading_controller.cpython-313.pyc
│   ├── code.cpython-313.pyc
│   ├── config.cpython-313.pyc
│   ├── dashboard.cpython-313.pyc
│   ├── gpt_api.cpython-313.pyc
│   ├── gpt_client.cpython-313.pyc
│   ├── live_options_api.cpython-313.pyc
│   ├── options_integration.cpython-313.pyc
│   ├── options_order_executor.cpython-313.pyc
│   ├── options_trading_bot.cpython-313.pyc
│   ├── transaction_logger.cpython-313.pyc
│   └── watchlist_view.cpython-313.pyc
├── AGENTS.md
├── alpaca
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   ├── api_client.cpython-313.pyc
│   │   ├── chatgpt_advisor.cpython-313.pyc
│   │   ├── gamma_scalper.cpython-313.pyc
│   │   ├── llm_vetter.cpython-313.pyc
│   │   ├── portfolio_manager.cpython-313.pyc
│   │   ├── risk_manager.cpython-313.pyc
│   │   ├── trade_manager.cpython-313.pyc
│   │   ├── trading_bot.cpython-313.pyc
│   │   ├── watchlist_manager.cpython-313.pyc
│   │   └── yield_farming.cpython-313.pyc
│   └── gpt_requests.log
├── bot.log
├── CODEX
│   ├── CODEX_CHECKLIST.md
│   └── CODEX_REPORT.md
├── dashboards
│   └── __pycache__
│       ├── __init__.cpython-313.pyc
│       └── textual_dashboard.cpython-313.pyc
├── dev-requirements.txt
├── docs
│   ├── api
│   │   ├── alpaca_market_data.md
│   │   ├── openai_chat_api.md
│   │   └── README.md
│   ├── assistants
│   │   ├── ArchUx_01_Summary.md
│   │   ├── ArchUx_02_RefactorCLI.md
│   │   ├── DASHBOARD_MOCK.md
│   │   └── README.md
│   ├── develop_api.md
│   ├── multi_metric_analysis.md
│   ├── research
│   ├── textual_dashboard.md
│   └── trading_daemon.md
├── FileTreeMap.md
├── fundrunner
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   └── main.cpython-313.pyc
│   ├── alpaca
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   ├── api_client.cpython-313.pyc
│   │   │   ├── chatgpt_advisor.cpython-313.pyc
│   │   │   ├── llm_vetter.cpython-313.pyc
│   │   │   ├── portfolio_manager.cpython-313.pyc
│   │   │   ├── portfolio_manager_active.cpython-313.pyc
│   │   │   ├── risk_manager.cpython-313.pyc
│   │   │   ├── trade_manager.cpython-313.pyc
│   │   │   ├── trading_bot.cpython-313.pyc
│   │   │   ├── watchlist_manager.cpython-313.pyc
│   │   │   └── yield_farming.cpython-313.pyc
│   │   ├── api_client.py
│   │   ├── chatgpt_advisor.py
│   │   ├── llm_vetter.py
│   │   ├── portfolio_manager.py
│   │   ├── risk_manager.py
│   │   ├── trade_manager.py
│   │   ├── trading_bot.py
│   │   ├── watchlist_manager.py
│   │   └── yield_farming.py
│   ├── backtester.py
│   ├── bots
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   └── options_trading_bot.cpython-313.pyc
│   │   ├── chatgpt_advisor.py
│   │   ├── chatgpt_trading_controller.py
│   │   ├── options_order_executor.py
│   │   ├── options_trading_bot.py
│   │   ├── yield_farming.py
│   │   └── yield_trading_bot.py
│   ├── dashboards
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   ├── dashboard.cpython-313.pyc
│   │   │   └── textual_dashboard.cpython-313.pyc
│   │   ├── dashboard.py
│   │   └── textual_dashboard.py
│   ├── main.py
│   ├── options
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   ├── live_options_api.cpython-313.pyc
│   │   │   └── options_integration.cpython-313.pyc
│   │   ├── live_options_api.py
│   │   └── options_integration.py
│   ├── plugins
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   └── multi_metric_analysis.cpython-313.pyc
│   │   ├── multi_metric_analysis.py
│   │   ├── plot_trades.py
│   │   ├── plugin_tools_menu.py
│   │   ├── portfolio_optimizer.py
│   │   └── sentiment_finbert.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   └── news.cpython-313.pyc
│   │   ├── news.py
│   │   └── trading_daemon.py
│   └── utils
│       ├── __init__.py
│       ├── __pycache__
│       │   ├── __init__.cpython-313.pyc
│       │   ├── config.cpython-313.pyc
│       │   ├── gpt_client.cpython-313.pyc
│       │   └── watchlist_view.cpython-313.pyc
│       ├── config.py
│       ├── gpt_client.py
│       ├── logger_config.py
│       ├── transaction_logger.py
│       └── watchlist_view.py
├── info
│   ├── active_checklist.md
│   ├── directory_map.md
│   ├── module_summary.md
│   └── reference_gpt_url.txt
├── Notes
├── old-fundrunner
│   ├── alpaca
│   ├── bots
│   ├── dashboards
│   ├── options
│   ├── plugins
│   ├── services
│   └── utils
├── plugins
│   └── __pycache__
│       ├── multi_metric_analysis.cpython-313.pyc
│       ├── plot_trades.cpython-313.pyc
│       ├── portfolio_optimizer.cpython-313.pyc
│       └── sentiment_finbert.cpython-313.pyc
├── portfolio_snapshot.json
├── PortfolioManager
│   ├── AlgoTradingV1.md
│   ├── Bot-PortfolioManager-DeepResearch
│   ├── DeepResearch_AlgoTrading
│   ├── Index.md
│   ├── PortfolioManager
│   ├── README.md
│   ├── scripts
│   └── sections
│       ├── additional_notes.md
│       ├── backtesting_validation.md
│       ├── quantitative_methods.md
│       ├── README.md
│       ├── risk_management.md
│       └── trading_bot_implementation.md
├── README.md
├── requirements-core.txt
├── requirements-plugins.txt
├── requirements.txt
├── scripts
│   ├── chroma_index.py
│   ├── lint.sh
│   ├── query_chroma.py
│   └── setup.sh
├── src
│   ├── bot.log
│   ├── fundrunner
│   │   ├── __init__.py
│   │   ├── alpaca
│   │   │   ├── __init__.py
│   │   │   ├── api_client.py
│   │   │   ├── chatgpt_advisor.py
│   │   │   ├── llm_vetter.py
│   │   │   ├── portfolio_manager.py
│   │   │   ├── portfolio_manager_active.py
│   │   │   ├── risk_manager.py
│   │   │   ├── trade_manager.py
│   │   │   ├── trading_bot.py
│   │   │   ├── watchlist_manager.py
│   │   │   └── yield_farming.py
│   │   ├── backtester.py
│   │   ├── bots
│   │   │   ├── __init__.py
│   │   │   ├── chatgpt_advisor.py
│   │   │   ├── chatgpt_trading_controller.py
│   │   │   ├── options_order_executor.py
│   │   │   ├── options_trading_bot.py
│   │   │   ├── yield_farming.py
│   │   │   └── yield_trading_bot.py
│   │   ├── dashboards
│   │   │   ├── __init__.py
│   │   │   ├── dashboard.py
│   │   │   └── textual_dashboard.py
│   │   ├── main.py
│   │   ├── options
│   │   │   ├── __init__.py
│   │   │   ├── live_options_api.py
│   │   │   └── options_integration.py
│   │   ├── plugins
│   │   │   ├── __init__.py
│   │   │   ├── multi_metric_analysis.py
│   │   │   ├── plot_trades.py
│   │   │   ├── plugin_tools_menu.py
│   │   │   ├── portfolio_optimizer.py
│   │   │   └── sentiment_finbert.py
│   │   ├── services
│   │   │   ├── __init__.py
│   │   │   └── trading_daemon.py
│   │   └── utils
│   │       ├── __init__.py
│   │       ├── config.py
│   │       ├── gpt_client.py
│   │       ├── logger_config.py
│   │       ├── transaction_logger.py
│   │       └── watchlist_view.py
│   └── portfolio_snapshot.json
├── tests
│   ├── __pycache__
│   │   ├── test_api_client_positions.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_api_client_time_format.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_backtester.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_chatgpt_trading_controller.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_cli_config_menu.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_cli_menu.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_config_portfolio_mode.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_dashboard.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_metrics_format.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_plugins.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_portfolio_manager_active.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_summary_update.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_textual_dashboard.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_trading_bot.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_trading_daemon.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_transaction_logger.cpython-313-pytest-8.4.1.pyc
│   │   ├── test_watchlist_view.cpython-313-pytest-8.4.1.pyc
│   │   └── test_yield_farming.cpython-313-pytest-8.4.1.pyc
│   ├── test_api_client_positions.py
│   ├── test_api_client_time_format.py
│   ├── test_backtester.py
│   ├── test_chatgpt_trading_controller.py
│   ├── test_cli_config_menu.py
│   ├── test_cli_menu.py
│   ├── test_config_portfolio_mode.py
│   ├── test_dashboard.py
│   ├── test_metrics_format.py
│   ├── test_plugins.py
│   ├── test_portfolio_manager_active.py
│   ├── test_summary_update.py
│   ├── test_textual_dashboard.py
│   ├── test_trading_bot.py
│   ├── test_trading_daemon.py
│   ├── test_transaction_logger.py
│   ├── test_watchlist_view.py
│   └── test_yield_farming.py
├── ToDo.md
└── transactions.log
