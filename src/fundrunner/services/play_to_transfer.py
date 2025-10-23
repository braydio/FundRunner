"""Client for interacting with the Play-to-Transfer API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Iterable, List, Optional

import requests

from fundrunner.utils.config import (
    PLAY_TO_TRANSFER_API_KEY,
    PLAY_TO_TRANSFER_BASE_URL,
)
from fundrunner.utils.error_handling import ErrorType, FundRunnerError

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> Optional[float]:
    """Return ``value`` converted to ``float`` when possible."""

    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_datetime(raw_value: Any) -> Optional[datetime]:
    """Parse ISO-8601 timestamps and gracefully handle invalid inputs."""

    if not raw_value or not isinstance(raw_value, str):
        return None
    try:
        normalized = raw_value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        logger.debug("Unable to parse datetime value: %s", raw_value)
        return None


@dataclass
class TransferRecord:
    """Normalized representation of a Play-to-Transfer transfer entry."""

    id: str
    status: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    created_at: Optional[datetime]
    transfer_type: Optional[str]
    description: Optional[str]


class PlayToTransferService:
    """High level wrapper around the Play-to-Transfer REST API."""

    def __init__(
        self,
        base_url: str = PLAY_TO_TRANSFER_BASE_URL,
        api_key: str = PLAY_TO_TRANSFER_API_KEY,
        *,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.session = session or requests.Session()
        self.timeout = timeout
        self._config_error: Optional[FundRunnerError] = None
        self.enabled = True

        if (
            not self.base_url
            or not self.api_key
            or self.base_url.startswith("your_")
            or self.api_key.startswith("your_")
        ):
            self.enabled = False


        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise FundRunnerError(
                "Play-to-Transfer integration is not configured.",
                error_type=ErrorType.CONFIG_MISSING,
                details={
                    "base_url": self.base_url or None,
                    "api_key_configured": bool(self.api_key),
                },
                original_exception=self._config_error,
            )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute an HTTP request against the Play-to-Transfer API."""

        self._ensure_enabled()
        url = f"{self.base_url}{path}"

        try:
            response = self.session.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=payload,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise FundRunnerError(
                f"Failed to contact Play-to-Transfer API: {exc}",
                ErrorType.API_CONNECTION,
                {"url": url},
                exc,
            ) from exc

        if response.status_code >= 400:
            try:
                error_payload = response.json()
            except ValueError:
                error_payload = {"message": response.text}

            error_type = (
                ErrorType.API_INVALID_REQUEST
                if response.status_code < 500
                else ErrorType.UNEXPECTED
            )
            raise FundRunnerError(
                "Play-to-Transfer API request failed",
                error_type,
                {
                    "url": url,
                    "status_code": response.status_code,
                    "response": error_payload,
                },
            )

        try:
            return response.json()
        except ValueError as exc:
            raise FundRunnerError(
                "Invalid JSON payload received from Play-to-Transfer API.",
                ErrorType.DATA_PARSING,
                {"url": url},
                exc,
            ) from exc

    def list_credit_cards(self) -> List[Dict[str, Any]]:
        """Return normalized credit card entries."""

        payload = self._request("GET", "/credit-cards")
        raw_cards: Iterable[Dict[str, Any]]
        if isinstance(payload, dict):
            raw_cards = payload.get("cards") or payload.get("data") or []
        else:
            raw_cards = payload  # type: ignore[assignment]

        normalized: List[Dict[str, Any]] = []
        for card in raw_cards:
            due_date = _parse_datetime(card.get("payment_due_date"))
            normalized.append(
                {
                    "id": str(card.get("id") or card.get("card_id") or ""),
                    "last4": card.get("last4"),
                    "nickname": card.get("nickname"),
                    "balance": _safe_float(card.get("balance")),
                    "available_credit": _safe_float(card.get("available_credit")),
                    "minimum_payment_due": _safe_float(
                        card.get("minimum_payment_due")
                    ),
                    "payment_due_date": due_date,
                    "raw_payment_due_date": card.get("payment_due_date"),
                    "apr": _safe_float(card.get("apr")),
                    "currency": card.get("currency", "USD"),
                    "status": card.get("status"),
                }
            )
        return normalized

    def list_transfers(
        self, *, status: Optional[str] = None, limit: Optional[int] = None
    ) -> List[TransferRecord]:
        """Return transfers filtered by ``status`` when provided."""

        params: Dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit

        payload = self._request("GET", "/transfers", params=params or None)
        raw_transfers: Iterable[Dict[str, Any]]
        if isinstance(payload, dict):
            raw_transfers = payload.get("transfers") or payload.get("data") or []
        else:
            raw_transfers = payload  # type: ignore[assignment]

        return [self._normalize_transfer(entry) for entry in raw_transfers]

    def submit_credit_card_payment(
        self,
        card_id: str,
        amount: float,
        *,
        currency: str = "USD",
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a credit card payment via the Play-to-Transfer API."""

        if amount <= 0:
            raise FundRunnerError(
                "Payment amount must be greater than zero.",
                ErrorType.VALIDATION,
                {"amount": amount},
            )

        payload = {
            "amount": round(float(amount), 2),
            "currency": currency,
        }
        if memo:
            payload["memo"] = memo

        response = self._request(
            "POST",
            f"/credit-cards/{card_id}/payments",
            payload=payload,
        )
        payment = response.get("payment") if isinstance(response, dict) else response

        created_at = None
        if isinstance(payment, dict):
            created_at = _parse_datetime(
                payment.get("created_at") or payment.get("submitted_at")
            )

        normalized_payment = {
            "id": str(
                (payment or {}).get("id")
                or (payment or {}).get("payment_id")
                or ""
            ),
            "status": (payment or {}).get("status"),
            "amount": _safe_float((payment or {}).get("amount")) or payload["amount"],
            "currency": (payment or {}).get("currency", currency),
            "created_at": created_at,
            "card_id": card_id,
        }
        if memo:
            normalized_payment["memo"] = memo
        return normalized_payment

    def _normalize_transfer(self, transfer: Dict[str, Any]) -> TransferRecord:
        """Convert transfer payloads into :class:`TransferRecord` instances."""

        return TransferRecord(
            id=str(transfer.get("id") or transfer.get("transfer_id") or ""),
            status=transfer.get("status"),
            amount=_safe_float(transfer.get("amount")),
            currency=transfer.get("currency", "USD"),
            created_at=_parse_datetime(
                transfer.get("created_at") or transfer.get("submitted_at")
            ),
            transfer_type=transfer.get("type"),
            description=transfer.get("description") or transfer.get("memo"),
        )

