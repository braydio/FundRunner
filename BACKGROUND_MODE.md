# Background Trading Mode

Run the automated background trading mode that periodically evaluates and executes trades without manual confirmation. It allocates most available capital while keeping a buffer for rebalancing and prints a trade summary at the end of each day.

## Usage

```bash
python -m fundrunner.services.background_trader
```

The service runs continuously, performing evaluations and order executions every ten minutes.
