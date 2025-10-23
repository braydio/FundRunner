"""Client for interacting with Plaid Transfer and Liabilities endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Dict, Iterable, List, Optional
import uuid

import requests

from fundrunner.utils.config import (
    PLAID_BASE_URL,
    PLAID_CLIENT_ID,
    PLAID_SECRET,
    PLAID_TRANSFER_ACCESS_TOKEN,
    PLAID_TRANSFER_ACCOUNT_ID,
    PLAID_TRANSFER_ORIGINATION_ACCOUNT_ID,
    PLAID_TRANSFER_USER_ADDRESS_CITY,
    PLAID_TRANSFER_USER_ADDRESS_COUNTRY,
    PLAID_TRANSFER_USER_ADDRESS_POSTAL_CODE,
    PLAID_TRANSFER_USER_ADDRESS_REGION,
    PLAID_TRANSFER_USER_ADDRESS_STREET,
    PLAID_TRANSFER_USER_EMAIL,
    PLAID_TRANSFER_USER_LEGAL_NAME,
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


def _parse_iso_datetime(raw_value: Any) -> Optional[datetime]:
    """Parse ISO-8601 timestamps and gracefully handle invalid inputs."""

    if not raw_value or not isinstance(raw_value, str):
        return None
    try:
        normalized = raw_value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError:
        logger.debug("Unable to parse datetime value: %s", raw_value)
        return None


def _parse_iso_date(raw_value: Any) -> Optional[datetime]:
    """Parse date strings (``YYYY-MM-DD``) to midnight :class:`datetime` objects."""

    if not raw_value or not isinstance(raw_value, str):
        return None
    try:
        return datetime.strptime(raw_value, "%Y-%m-%d")
    except ValueError:
        logger.debug("Unable to parse date value: %s", raw_value)
        return None


def _extract_apr(aprs: Any) -> Optional[float]:
    """Return the most relevant APR percentage from Plaid liabilities data."""

    if not isinstance(aprs, Iterable):
        return None
    selected: Optional[float] = None
    for entry in aprs:
        if not isinstance(entry, dict):
            continue
        value = _safe_float(entry.get("apr_percentage"))
        if value is None:
            continue
        apr_type = str(entry.get("apr_type") or "").lower()
        if apr_type == "purchase_apr":
            return value
        if selected is None:
            selected = value
    return selected


def _format_amount(amount: float) -> str:
    """Format numeric amount to Plaid's expected string representation."""

    return f"{float(amount):.2f}"


@dataclass
class TransferRecord:
    """Normalized representation of a Plaid transfer entry."""

    id: str
    status: Optional[str]
    amount: Optional[float]
    currency: Optional[str]
    created_at: Optional[datetime]
    transfer_type: Optional[str]
    description: Optional[str]


class PlaidTransferService:
    """High level wrapper around Plaid Transfer and Liabilities APIs."""

    def __init__(
        self,
        base_url: str = PLAID_BASE_URL,
        client_id: str = PLAID_CLIENT_ID,
        secret: str = PLAID_SECRET,
        access_token: str = PLAID_TRANSFER_ACCESS_TOKEN,
        account_id: str = PLAID_TRANSFER_ACCOUNT_ID,
        *,
        origination_account_id: Optional[str] = None,
        user_legal_name: str = PLAID_TRANSFER_USER_LEGAL_NAME,
        user_email: str = PLAID_TRANSFER_USER_EMAIL,
        user_address: Optional[Dict[str, str]] = None,
        session: Optional[requests.Session] = None,
        timeout: float = 10.0,
    ) -> None:
        if origination_account_id is None and PLAID_TRANSFER_ORIGINATION_ACCOUNT_ID:
            origination_account_id = PLAID_TRANSFER_ORIGINATION_ACCOUNT_ID or None

        if user_address is None:
            address_fields = {
                "street": PLAID_TRANSFER_USER_ADDRESS_STREET,
                "city": PLAID_TRANSFER_USER_ADDRESS_CITY,
                "region": PLAID_TRANSFER_USER_ADDRESS_REGION,
                "postal_code": PLAID_TRANSFER_USER_ADDRESS_POSTAL_CODE,
                "country": PLAID_TRANSFER_USER_ADDRESS_COUNTRY,
            }
            if all(address_fields.values()):
                user_address = address_fields
            else:
                user_address = {
                    key: value for key, value in address_fields.items() if value
                }

        self.base_url = (base_url or "").rstrip("/")
        self.client_id = client_id or ""
        self.secret = secret or ""
        self.access_token = access_token or ""
        self.account_id = account_id or ""
        self.origination_account_id = origination_account_id or ""
        self.user_legal_name = user_legal_name or ""
        self.user_email = user_email or ""
        self.user_address = user_address or {}
        self.session = session or requests.Session()
        self.timeout = timeout
        self._config_error: Optional[FundRunnerError] = None
        self.enabled = True

        required_values = [
            self.base_url,
            self.client_id,
            self.secret,
            self.access_token,
            self.account_id,
        ]
        if any(not value for value in required_values) or any(
            str(value).startswith("your_") for value in required_values
        ):
            self.enabled = False

    def _ensure_enabled(self) -> None:
        if not self.enabled:
            raise FundRunnerError(
                "Plaid Transfer integration is not configured.",
                error_type=ErrorType.CONFIG_MISSING,
                details={
                    "base_url": self.base_url or None,
                    "client_id_configured": bool(self.client_id),
                    "secret_configured": bool(self.secret),
                    "access_token_configured": bool(self.access_token),
                    "account_id_configured": bool(self.account_id),
                },
                original_exception=self._config_error,
            )

    def _request(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a POST request against the Plaid API."""

        self._ensure_enabled()
        url = f"{self.base_url}/{path.lstrip('/')}"
        body = {
            "client_id": self.client_id,
            "secret": self.secret,
        }
        body.update(payload)

        try:
            response = self.session.post(url, json=body, timeout=self.timeout)
        except requests.RequestException as exc:  # pragma: no cover - network failure
            raise FundRunnerError(
                f"Failed to contact Plaid API: {exc}",
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
                "Plaid API request failed",
                error_type,
                {
                    "url": url,
                    "status_code": response.status_code,
                    "response": error_payload,
                },
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise FundRunnerError(
                "Invalid JSON payload received from Plaid API.",
                ErrorType.DATA_PARSING,
                {"url": url},
                exc,
            ) from exc

        if not isinstance(data, dict):
            raise FundRunnerError(
                "Unexpected payload received from Plaid API.",
                ErrorType.DATA_PARSING,
                {"url": url, "payload": data},
            )
        return data

    def _user_payload(self) -> Dict[str, Any]:
        """Construct the Plaid user payload if configuration is available."""

        payload: Dict[str, Any] = {}
        if self.user_legal_name:
            payload["legal_name"] = self.user_legal_name
        if self.user_email:
            payload["email_address"] = self.user_email
        if self.user_address:
            address = {
                key: value
                for key, value in {
                    "street": self.user_address.get("street"),
                    "city": self.user_address.get("city"),
                    "region": self.user_address.get("region"),
                    "postal_code": self.user_address.get("postal_code"),
                    "country": self.user_address.get("country"),
                }.items()
                if value
            }
            if address:
                payload["address"] = address
        return payload

    def list_credit_cards(self) -> List[Dict[str, Any]]:
        """Return normalized credit card liabilities."""

        payload = self._request(
            "liabilities/get",
            {"access_token": self.access_token},
        )

        accounts_lookup: Dict[str, Dict[str, Any]] = {}
        for account in payload.get("accounts", []):
            if isinstance(account, dict):
                account_id = account.get("account_id")
                if account_id:
                    accounts_lookup[str(account_id)] = account

        liabilities = payload.get("liabilities", {})
        credit_entries: Iterable[Dict[str, Any]] = (
            liabilities.get("credit", []) if isinstance(liabilities, dict) else []
        )

        normalized: List[Dict[str, Any]] = []
        for entry in credit_entries:
            if not isinstance(entry, dict):
                continue
            account_id = str(entry.get("account_id") or "")
            account_info = accounts_lookup.get(account_id, {})
            balances = (
                account_info.get("balances", {})
                if isinstance(account_info, dict)
                else {}
            )
            due_date = _parse_iso_date(entry.get("next_payment_due_date"))
            normalized.append(
                {
                    "id": account_id,
                    "last4": account_info.get("mask"),
                    "nickname": account_info.get("name")
                    or account_info.get("official_name"),
                    "balance": _safe_float(balances.get("current")),
                    "available_credit": _safe_float(balances.get("available")),
                    "minimum_payment_due": _safe_float(
                        entry.get("minimum_payment_amount")
                    ),
                    "payment_due_date": due_date,
                    "raw_payment_due_date": entry.get("next_payment_due_date"),
                    "apr": _extract_apr(entry.get("aprs")),
                    "currency": balances.get("iso_currency_code")
                    or balances.get("unofficial_currency_code"),
                    "status": entry.get("account_status")
                    or account_info.get("subtype")
                    or account_info.get("type"),
                }
            )
        return normalized

    def list_transfers(
        self, *, status: Optional[str] = None, limit: Optional[int] = None
    ) -> List[TransferRecord]:
        """Return Plaid transfers filtered by ``status`` when provided."""

        request_payload: Dict[str, Any] = {
            "count": limit if limit is not None else 20,
            "offset": 0,
        }
        if self.origination_account_id:
            request_payload["origination_account_id"] = self.origination_account_id

        payload = self._request("transfer/list", request_payload)
        raw_transfers: Iterable[Dict[str, Any]] = payload.get("transfers", [])

        records: List[TransferRecord] = []
        for transfer in raw_transfers:
            if not isinstance(transfer, dict):
                continue
            record = self._normalize_transfer(transfer)
            if status and record.status != status:
                continue
            records.append(record)
        return records

    def submit_credit_card_payment(
        self,
        card_id: str,
        amount: float,
        *,
        currency: str = "USD",
        memo: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a credit card payment by creating a Plaid transfer."""

        if amount <= 0:
            raise FundRunnerError(
                "Payment amount must be greater than zero.",
                ErrorType.VALIDATION,
                {"amount": amount},
            )

        account_id = card_id or self.account_id
        amount_str = _format_amount(amount)

        user_payload = self._user_payload()
        authorization_payload: Dict[str, Any] = {
            "access_token": self.access_token,
            "account_id": account_id,
            "type": "debit",
            "amount": amount_str,
            "ach_class": "ppd",
        }
        if user_payload:
            authorization_payload["user"] = user_payload

        authorization_response = self._request(
            "transfer/authorization/create", authorization_payload
        )
        authorization = authorization_response.get("authorization", {})
        authorization_id = authorization.get("id")
        if not authorization_id:
            raise FundRunnerError(
                "Plaid did not return an authorization id for the transfer.",
                ErrorType.DATA_PARSING,
                {"response": authorization_response},
            )

        create_payload: Dict[str, Any] = {
            "idempotency_key": uuid.uuid4().hex,
            "access_token": self.access_token,
            "account_id": account_id,
            "authorization_id": authorization_id,
            "type": "debit",
            "network": "ach",
            "amount": amount_str,
            "ach_class": "ppd",
            "iso_currency_code": currency,
            "description": memo or "Credit card payment",
        }
        if user_payload:
            create_payload["user"] = user_payload
        if self.origination_account_id:
            create_payload["origination_account_id"] = self.origination_account_id

        transfer_response = self._request("transfer/create", create_payload)
        transfer = transfer_response.get("transfer", {})
        created_at = _parse_iso_datetime(
            transfer.get("created")
        ) or _parse_iso_datetime(transfer.get("created_at"))

        normalized_payment = {
            "id": str(transfer.get("id") or transfer.get("transfer_id") or ""),
            "status": transfer.get("status"),
            "amount": _safe_float(transfer.get("amount")) or float(amount_str),
            "currency": transfer.get("iso_currency_code") or currency,
            "created_at": created_at,
            "card_id": account_id,
            "authorization_id": authorization_id,
            "network": transfer.get("network"),
            "ach_class": transfer.get("ach_class"),
            "type": transfer.get("type"),
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
            currency=transfer.get("iso_currency_code") or transfer.get("currency"),
            created_at=_parse_iso_datetime(
                transfer.get("created") or transfer.get("created_at")
            ),
            transfer_type=transfer.get("type"),
            description=transfer.get("description") or transfer.get("ach_class"),
        )
