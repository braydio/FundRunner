### 📋 Actionable Checklist for Today - 5-20-25

#### ✅ Environment & Config Review

- [ ] Review `.env.example` and sync secrets securely
- [ ] Confirm `config.py` structure and mutability

#### 🔄 Modular Audit

- [ ] Confirm independence and testability of:

  - [ ] `trading_bot.py`
  - [ ] `options_trading_bot.py`
  - [ ] `chatgpt_advisor.py`

#### 🧪 Testing & Validation

- [ ] Execute `test_metrics_format.py` and evaluate test coverage
- [ ] Add unit tests if gaps are detected in any trading or GPT module

#### 🔁 Live/Backtest Flow Sync

- [ ] Map flow from CLI > Strategy > Execution
- [ ] Validate `backtester.py`'s compatibility with current execution modules

#### 🤖 LLM Pipeline Sanity Check

- [ ] Trace flow from `cli.py` or `main.py` to GPT outputs
- [ ] Validate `llm_integration.py` correctness and logging

#### 📚 Documentation Update

- [ ] Add descriptions for new/updated scripts (especially GPT and trading logic)
- [ ] Update `README.md` if behavior or entrypoints changed

#### 🗂️ Structure & Cleanliness

- [ ] Review unused scripts, refactor if needed
- [ ] Identify repetitive patterns for abstraction
