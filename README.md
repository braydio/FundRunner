```
project/
├── alpaca/
│   ├── __init__.py
│   ├── api_client.py
│   ├── portfolio_manager.py
│   ├── trade_manager.py
│   └── watchlist_manager.py
├── options/
│   ├── __init__.py
│   └── options_integration.py
├── llm_integration.py
├── logger_config.py
├── cli.py
├── main.py
├── backtester.py
├── transaction_logger.py
├── config.py
```

## Micro Mode

Set `MICRO_MODE=true` in your `.env` file to run the bot assuming a small
simulated account balance.  `MICRO_ACCOUNT_SIZE` controls the starting cash
when micro mode is enabled (defaults to `$100`).  This mode automatically
increases trade allocation limits so the bot can purchase at least one share
when funds allow.

## Dependencies

The project relies on a small set of third-party libraries. After auditing the source code and tests, the following packages remain in `requirements.txt`:

- alpaca-trade-api
- python-dotenv
- requests
- rich
- pandas
- numpy
- transformers
- torch
- tiktoken
- openai
- PyPortfolioOpt
- mplfinance

All packages are actively imported somewhere in the codebase or the accompanying tests.
