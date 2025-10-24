# Plaid Transfer API Notes

FundRunner uses Plaid's Transfer and Liabilities products to display credit card
balances, payment metadata, and to initiate ACH repayments from the dashboard.
The public documentation is available from Plaid, but the HTML requires a
browser to render. Direct `curl` requests returned no content in this
environment, so the links below point to the canonical docs for manual review.

- [Plaid Transfer API](https://plaid.com/docs/api/products/transfer/)
- [Plaid Liabilities API](https://plaid.com/docs/api/products/liabilities/)

## Endpoints utilised

The `PlaidTransferService` currently relies on the following endpoints:

- `POST /liabilities/get` – Retrieves credit card liabilities for the
  configured `access_token`. Used to derive balance, APR, and due date values.
- `POST /transfer/authorization/create` – Creates an authorization for an ACH
  debit prior to submitting the repayment.
- `POST /transfer/create` – Submits an authorized transfer to move funds for a
  credit card payment.
- `POST /transfer/list` – Lists historical transfers for display in the CLI.

## Authentication and configuration

Each request embeds the Plaid `client_id` and `secret` along with the target
`access_token`. Environment variables expected by FundRunner are defined in
`fundrunner.utils.config` and include:

- `PLAID_CLIENT_ID`
- `PLAID_SECRET`
- `PLAID_TRANSFER_ACCESS_TOKEN`
- `PLAID_TRANSFER_ACCOUNT_ID`
- Optional user metadata (`PLAID_TRANSFER_USER_*`) used when creating
  transfers.

Configure `PLAID_ENVIRONMENT` to switch between `sandbox`, `development`, or
`production` API hosts. A manual `PLAID_BASE_URL` override is also supported for
advanced testing scenarios.
