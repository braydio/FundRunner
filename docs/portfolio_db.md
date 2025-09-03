# Portfolio Database Service

`PortfolioDB` provides a lightweight SQLite backend for recording yield
history. The service initialises a local database with a single
`yield_history` table capturing the symbol, yield rate, and timestamp of
each observation.

## Integration

- **LendingRateService** – after fetching rates, call
  `record_lending_rates` to persist the snapshot.
- **Portfolio tracking** – portfolio managers or analytics components can
  query `get_yield_history` to analyse historical returns.
