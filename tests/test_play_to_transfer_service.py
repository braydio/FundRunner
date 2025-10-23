"""Tests for the Play-to-Transfer service integration."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from fundrunner.services.play_to_transfer import PlayToTransferService
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

    def request(self, method, url, headers=None, params=None, json=None, timeout=None):
        if not self._responses:
            raise AssertionError("No responses queued for DummySession")
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
                "timeout": timeout,
            }
        )
        return self._responses.pop(0)


def test_service_disabled_without_config():
    """Service reports disabled state when configuration is missing."""

    service = PlayToTransferService(base_url="", api_key="", session=DummySession([]))
    assert not service.enabled
    with pytest.raises(FundRunnerError):
        service.list_credit_cards()


def test_list_credit_cards_normalizes_payload():
    """Credit card responses are sanitized and parsed."""

    payload = {
        "cards": [
            {
                "id": "card_1",
                "last4": "1111",
                "nickname": "Primary",
                "balance": "1250.55",
                "minimum_payment_due": "25.50",
                "payment_due_date": "2024-07-15T00:00:00Z",
                "apr": "15.75",
                "currency": "usd",
                "status": "open",
            }
        ]
    }
    session = DummySession([DummyResponse(payload=payload)])
    service = PlayToTransferService(
        base_url="https://pt.example.com",
        api_key="secret",
        session=session,
    )

    cards = service.list_credit_cards()

    assert session.requests[0]["url"] == "https://pt.example.com/credit-cards"
    assert session.requests[0]["headers"]["Authorization"] == "Bearer secret"
    card = cards[0]
    assert card["id"] == "card_1"
    assert card["balance"] == 1250.55
    assert card["apr"] == 15.75
    assert isinstance(card["payment_due_date"], datetime)
    assert card["payment_due_date"].isoformat() == "2024-07-15T00:00:00+00:00"
    assert card["currency"] == "usd"


def test_submit_credit_card_payment_posts_payload():
    """Submitting a payment hits the correct endpoint with payload data."""

    payload = {
        "payment": {
            "id": "pay_1",
            "status": "submitted",
            "amount": "42.0",
            "currency": "USD",
            "created_at": "2024-06-01T12:30:00Z",
        }
    }
    session = DummySession([DummyResponse(payload=payload)])
    service = PlayToTransferService(
        base_url="https://pt.example.com",
        api_key="secret",
        session=session,
    )

    payment = service.submit_credit_card_payment("card_123", 42.0, memo="Test")

    request = session.requests[0]
    assert request["url"] == "https://pt.example.com/credit-cards/card_123/payments"
    assert request["json"] == {"amount": 42.0, "currency": "USD", "memo": "Test"}
    assert payment["status"] == "submitted"
    assert payment["amount"] == 42.0
    assert payment["memo"] == "Test"
    assert payment["created_at"].isoformat() == "2024-06-01T12:30:00+00:00"


def test_list_transfers_applies_filters():
    """Transfer listings honour query parameters and normalize fields."""

    payload = {
        "transfers": [
            {
                "id": "tr_1",
                "status": "pending",
                "amount": "100",
                "currency": "USD",
                "created_at": "2024-05-01T10:00:00Z",
                "type": "card_payment",
                "description": "Credit card payment",
            }
        ]
    }
    session = DummySession([DummyResponse(payload=payload)])
    service = PlayToTransferService(
        base_url="https://pt.example.com",
        api_key="secret",
        session=session,
    )

    transfers = service.list_transfers(status="pending", limit=5)

    request = session.requests[0]
    assert request["params"]["status"] == "pending"
    assert request["params"]["limit"] == 5
    transfer = transfers[0]
    assert transfer.amount == 100.0
    assert transfer.transfer_type == "card_payment"
    assert transfer.created_at.isoformat() == "2024-05-01T10:00:00+00:00"


def test_http_errors_raise_fundrunner_error():
    """HTTP errors surface as :class:`FundRunnerError`."""

    session = DummySession([DummyResponse(payload={"error": "bad"}, status_code=400)])
    service = PlayToTransferService(
        base_url="https://pt.example.com",
        api_key="secret",
        session=session,
    )

    with pytest.raises(FundRunnerError):
        service.list_credit_cards()
