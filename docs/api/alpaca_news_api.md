# Alpaca News API

FundRunner uses Alpaca's news endpoint to supply headlines to the LLM when
suggesting portfolio weights.

Environment variables:

- `ALPACA_API_KEY` and `ALPACA_API_SECRET` – credentials for Alpaca.
- `ALPACA_NEWS_URL` – optional override for the news endpoint. Defaults to
  `${ALPACA_DATA_URL}/v1beta1/news`.

See the [official Alpaca documentation](https://docs.alpaca.markets/docs/news-api)
for full details on available query parameters and response formats.
