# AGENTS.md – FundRunner Contributor Guide

## Project Structure
- `main.py` – central bot
- `cli.py` – command line interface
- `test_*.py` – unit tests
- `options__.py` – trading logic
- `backtester.py` – strategy benchmark evaluator


## Setup Steps
Codex/contributor instructions: 
```
bash scripts/setup.sh
source .venv/bin/activate
cp .env.example .env
edit .env with your API keys
pytest
```


## Testing & Contribution
- Run `pytest` after changes
- Use `efake8` for lnting (dev)
- Branching: `feature/fix-overview` setup
https://github.com/braydio/FundRunner/tree/main
```

## Prompting Codex
Agents: Use separate, precise prompts like:
```
write a function in `backtester.py` that logs trades exceeding $1000.
```
Always include file names and context when asking for code.

## .env Config
Data via `l.env` includes:
- Alpaca API Keys
Mode flags (e.g. `MICRO_MODE mode`)

Never commit .env to git.

## Todo List
- [] Refactor options_integration.py
- [] Add FLAKE8 check to all sources
- [] Expand test coverage with context tests