# Lending Rate Service

Documentation for the Alpaca stock lending rates endpoint used by
`LendingRateService`.

## Endpoint

`GET /v1beta1/stock-lending/rates?symbols=AAPL,MSFT`

- **Base URL:** `https://paper-api.alpaca.markets`
- **Official Docs:** https://docs.alpaca.markets/reference/getstocklendingrates

### Query Parameters

| Name    | Description                                      |
|---------|--------------------------------------------------|
| symbols | Comma-separated list of ticker symbols to query. |

### Response

A successful request returns JSON containing rate information:

```json
{
  "rates": [
    {"symbol": "AAPL", "rate": 0.0123},
    {"symbol": "MSFT", "rate": 0.0101}
  ]
}
```

## Fallback Behaviour

`LendingRateService.get_rates` attempts to fetch live data. If
credentials are missing or the request fails, deterministic stub rates
starting at `0.01` and increasing by `0.005` per symbol are returned.
Failures and successes are logged via the notification helpers.
