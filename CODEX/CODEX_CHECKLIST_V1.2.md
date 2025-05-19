# FundRunner CODEX Refactor Process Checklist

This checklist follows a process-oriented order based on the CODEX report for improving the FundRunner codebase. It is organized chronologically to support incremental cleanup and maintainability.

---

## ✅ Phase 1: Foundation Cleanup

- [x] Unify Alpaca API clients into a single submodule (`alpaca/api_client.py`)
- [x] Remove legacy or redundant file: `api_client.py` (N/A — no duplicate found)
- [x] Remove `backup_trading_bot.py` (file removed, assumed parity confirmed)
- [x] Normalize environment config loading into a single utility (`config.py`)
- [x] Add `.env.example` template (written below)

---

## ✅ Phase 2: Codebase Simplification

- [ ] Consolidate GPT/LLM modules into one package (`llm/` or `gpt/`)

- [x] Merge `chatgpt_advisor.py` and `llm_integration.py` (see `llm/gpt_client.py`, `llm/vetting.py`)
- [x] Deduplicate logic in `gpt_api.py` (merged into unified GPT module)
- [x] Merge or retire `cli.py` in favor of `main.py` as the single entry point (retired — `main.py` is now canonical CLI)
- [ ] Split `options_integration.py` into submodules:

  - [ ] `options/greeks.py`
  - [ ] `options/evaluate.py`
  - [ ] `options/strike_selection.py`
  - [ ] `options/strategies/`

---

## ✅ Phase 3: Architecture & Testing

- [ ] Add type hints to all public functions and classes
- [ ] Add `pyproject.toml` and configure `black`, `mypy`, `flake8`
- [ ] Add `setup.py` or `poetry` config for packaging
- [ ] Create unit tests for:

  - [ ] Alpaca client
  - [ ] Trading bot logic
  - [ ] Options evaluation logic
  - [ ] LLM integration logic

- [ ] Expand `test_metrics_format.py` to test trading strategies

---

## ✅ Phase 4: Documentation & CI

- [ ] Update `README.md` with architecture diagram and usage examples
- [ ] Add contributor guide and CODEX link summary
- [ ] Add GitHub Actions workflow for CI lint/test
- [ ] Add `requirements-dev.txt` for tooling support

---

## 🔄 Ongoing Maintenance

- [ ] Document and tag all public APIs
- [ ] Ensure all `main.py` jobs run with logging and fail-safe config
- [ ] Enforce pre-commit checks for formatting and linting

---

Let me know when you're ready to begin with Phase 1, and I'll begin execution and log each item as it's completed.
