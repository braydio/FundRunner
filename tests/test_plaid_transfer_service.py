"""Tests for the Plaid Transfer service integration."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from fundrunner.services.plaid_transfer import PlaidTransferService
from fundrunner.utils.error_handling import FundRunnerError


class DummyResponse:
    """Simple stand-in for :class:`requests.Response`."""

    def __init__(self, payload=None, status_code: int = 200):
        self._payload = payload if payload is not None else {}
        self.status_code = status_code
        self.text = json.dumps(self._payload)

    def json(self):
        return self._payload


class DummySession:
    """Session that returns queued responses and records requests."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def post(
        self, url, json=None, timeout=None
    ):  # noqa: A003 - align with requests API
        if not self._responses:
            raise AssertionError("No responses queued for DummySession")
        self.requests.append(
            {
                "url": url,
                "json": json,
                "timeout": timeout,
            }
        )
        return self._responses.pop(0)


def test_service_disabled_without_config():
    """Service reports disabled state when configuration is missing."""

    service = PlaidTransferService(
        base_url="",
        client_id="",
        secret="",
        access_token="",
        account_id="",
        session=DummySession([]),
    )
    assert not service.enabled
    with pytest.raises(FundRunnerError):
        service.list_credit_cards()


def test_list_credit_cards_normalizes_payload():
    """Credit card responses are sanitized and parsed from Plaid data."""

    payload = {
        "accounts": [
            {
                "account_id": "acc_1",
                "name": "Plaid Visa",
                "mask": "1111",
                "balances": {
                    "current": 1250.55,
                    "available": 2750.45,
                    "iso_currency_code": "USD",
                },
                "subtype": "credit card",
            }
        ],
        "liabilities": {
            "credit": [
                {
                    "account_id": "acc_1",
                    "minimum_payment_amount": 25.5,
                    "next_payment_due_date": "2024-07-15",
                    "aprs": [
                        {
                            "apr_type": "purchase_apr",
                            "apr_percentage": 15.75,
                        }
                    ],
                }
            ]
        },
    }
    session = DummySession([DummyResponse(payload=payload)])
    service = PlaidTransferService(
        base_url="https://plaid.example.com",
        client_id="client",
        secret="secret",
        access_token="token",
        account_id="acc_1",
        session=session,
    )

    cards = service.list_credit_cards()

    request = session.requests[0]
    assert request["url"] == "https://plaid.example.com/liabilities/get"
    assert request["json"]["client_id"] == "client"
    assert request["json"]["secret"] == "secret"
    assert request["json"]["access_token"] == "token"

    card = cards[0]
    assert card["id"] == "acc_1"
    assert card["last4"] == "1111"
    assert card["balance"] == 1250.55
    assert card["minimum_payment_due"] == 25.5
    assert isinstance(card["payment_due_date"], datetime)
    assert card["payment_due_date"].isoformat() == "2024-07-15T00:00:00"
    assert card["apr"] == 15.75
    assert card["currency"] == "USD"


def test_submit_credit_card_payment_posts_payload():
    """Submitting a payment hits Plaid transfer authorization and creation endpoints."""

    responses = [
        DummyResponse(payload={"authorization": {"id": "auth_1"}}),
        DummyResponse(
            payload={
                "transfer": {
                    "id": "tr_1",
                    "status": "pending",
                    "amount": "42.00",
                    "iso_currency_code": "USD",
                    "created": "2024-06-01T12:30:00Z",
                    "type": "debit",
                    "network": "ach",
                    "ach_class": "ppd",
                    "description": "Credit card payment",
                }
            }
        ),
    ]
    session = DummySession(responses)
    service = PlaidTransferService(
        base_url="https://plaid.example.com",
        client_id="client",
        secret="secret",
        access_token="token",
        account_id="acc_1",
        user_legal_name="Test User",
        user_email="test@example.com",
        session=session,
    )

    payment = service.submit_credit_card_payment("acc_1", 42.0, memo="Test")

    auth_request = session.requests[0]
    assert (
        auth_request["url"] == "https://plaid.example.com/transfer/authorization/create"
    )
    assert auth_request["json"]["amount"] == "42.00"
    assert auth_request["json"]["account_id"] == "acc_1"
    assert auth_request["json"]["user"]["legal_name"] == "Test User"

    create_request = session.requests[1]
    assert create_request["url"] == "https://plaid.example.com/transfer/create"
    assert create_request["json"]["authorization_id"] == "auth_1"
    assert create_request["json"]["amount"] == "42.00"
    assert create_request["json"]["description"] == "Test"
    assert len(create_request["json"]["idempotency_key"]) == 32

    assert payment["status"] == "pending"
    assert payment["amount"] == 42.0
    assert payment["currency"] == "USD"
    assert payment["memo"] == "Test"
    assert isinstance(payment["created_at"], datetime)
    assert payment["created_at"].isoformat() == "2024-06-01T12:30:00+00:00"


def test_list_transfers_applies_filters():
    """Transfer listings honour query parameters and normalize fields."""

    payload = {
        "transfers": [
            {
                "id": "tr_pending",
                "status": "pending",
                "amount": "100",
                "iso_currency_code": "USD",
                "created": "2024-05-01T10:00:00Z",
                "type": "debit",
                "description": "Pending payment",
            },
            {
                "id": "tr_completed",
                "status": "completed",
                "amount": "200",
                "iso_currency_code": "USD",
                "created": "2024-05-02T10:00:00Z",
                "type": "debit",
                "description": "Completed payment",
            },
        ]
    }
    session = DummySession([DummyResponse(payload=payload)])
    service = PlaidTransferService(
        base_url="https://plaid.example.com",
        client_id="client",
        secret="secret",
        access_token="token",
        account_id="acc_1",
        session=session,
    )

    transfers = service.list_transfers(status="pending", limit=10)

    request = session.requests[0]
    assert request["json"]["count"] == 10
    assert request["json"]["offset"] == 0

    assert len(transfers) == 1
    transfer = transfers[0]
    assert transfer.amount == 100.0
    assert transfer.transfer_type == "debit"
    assert transfer.created_at.isoformat() == "2024-05-01T10:00:00+00:00"


def test_http_errors_raise_fundrunner_error():
    """HTTP errors surface as :class:`FundRunnerError`."""

    session = DummySession([DummyResponse(payload={"error": "bad"}, status_code=400)])
    service = PlaidTransferService(
        base_url="https://plaid.example.com",
        client_id="client",
        secret="secret",
        access_token="token",
        account_id="acc_1",
        session=session,
    )

    with pytest.raises(FundRunnerError):
        service.list_credit_cards()
