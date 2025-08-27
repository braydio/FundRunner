# Alpaca Market Data Endpoints

Summary of commonly used market data endpoints. Links point to the official Alpaca Markets documentation, which may require a browser and can block direct CLI requests.

## Stocks
- `GET /v2/stocks/{symbol}/bars` – Historical price bars. [Docs](https://docs.alpaca.markets/reference/get-stock-bars)
- `GET /v2/stocks/{symbol}/trades/latest` – Latest trade. [Docs](https://docs.alpaca.markets/reference/get-stock-trades-latest)
- `GET /v2/stocks/{symbol}/trades` – Historical trades. [Docs](https://docs.alpaca.markets/reference/get-stock-trades)
- `GET /v2/stocks/{symbol}/quotes/latest` – Latest quote. [Docs](https://docs.alpaca.markets/reference/get-stock-quotes-latest)
- `GET /v2/stocks/{symbol}/quotes` – Historical quotes. [Docs](https://docs.alpaca.markets/reference/get-stock-quotes)

## Options
- `GET /v2/options/contracts` – Option contract listings. [Docs](https://docs.alpaca.markets/reference/options-contracts)
- `GET /v2/options/{symbol}/chain` – Option chain for an underlying. [Docs](https://docs.alpaca.markets/reference/get-options-chain)

## Crypto
- `GET /v2/crypto/{symbol}/bars` – Historical crypto bars. [Docs](https://docs.alpaca.markets/reference/get-crypto-bars)
- `GET /v2/crypto/{symbol}/trades/latest` – Latest crypto trade. [Docs](https://docs.alpaca.markets/reference/get-crypto-trades-latest)
- `GET /v2/crypto/{symbol}/quotes/latest` – Latest crypto quote. [Docs](https://docs.alpaca.markets/reference/get-crypto-quotes-latest)

## Reference Data
- `GET /v2/calendar` – Trading calendar. [Docs](https://docs.alpaca.markets/reference/get-calendar)
- `GET /v2/clock` – Market clock. [Docs](https://docs.alpaca.markets/reference/get-clock)

Official documentation may require browser access and can return `403 Forbidden` when retrieved from a headless environment.
