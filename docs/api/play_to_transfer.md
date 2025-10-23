# Play-to-Transfer API Notes

The Play-to-Transfer integration powers credit card payments and transfer
visibility inside the FundRunner dashboard. The service is treated as an
external REST API that exposes the following resources:

- `GET /credit-cards` – returns the available credit card accounts, including
  balance, minimum payment, payment due date, APR and currency metadata.
- `POST /credit-cards/{card_id}/payments` – submits a credit card payment for
  the given account.
- `GET /transfers` – lists recent transfer activity such as completed or
  pending payments. Optional query parameters `status` and `limit` mirror the
  functionality exposed by :class:`~fundrunner.services.play_to_transfer.PlayToTransferService`.

All requests are authenticated with a `Bearer` token supplied through the
`PLAY_TO_TRANSFER_API_KEY` environment variable. The base URL is configured via
`PLAY_TO_TRANSFER_BASE_URL`.

Responses are expected to follow the JSON shapes used within the new
`PlayToTransferService`; if the API responds with different payloads a
`FundRunnerError` will be raised and displayed to the operator.
