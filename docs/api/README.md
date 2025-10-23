# FundRunner API Documentation

This folder contains documentation for all **external APIs** and **plugin interfaces** used in FundRunner.

## Current Integrations

- [Alpaca Markets API](https://alpaca.markets/docs/)
  - Used for trading, account data, and market data feeds.
- [Lending Rate Service](lending_rates.md)
  - Fetches stock lending rates from Alpaca with a stub fallback.
- [Play-to-Transfer API](play_to_transfer.md)
  - Powers dashboard credit card payments and transfer visibility.
- [Optional Plugins]
  - Document as added.

## Guidelines

- Each external API used in the codebase must be documented here.
- Add one Markdown file per API under `docs/api/` (e.g. `alpaca.md`).
- If official docs cannot be fetched, note that in the file.

---

### Todo

- [ ] Add `alpaca.md` with details of endpoints currently referenced in `src/fundrunner/alpaca/`.
- [ ] Add plugin-specific docs as plugins are enabled.
