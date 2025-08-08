"""Utilities for retrieving market news headlines."""

from __future__ import annotations

import logging
from typing import Sequence, List

import requests

from fundrunner.utils.config import API_KEY, API_SECRET, NEWS_API_URL

logger = logging.getLogger(__name__)


def fetch_news(symbols: Sequence[str]) -> List[str]:
    """Fetch recent news headlines for the given ticker symbols.

    Parameters
    ----------
    symbols:
        Iterable of ticker symbols.

    Returns
    -------
    list of str
        A list of headline strings. Returns an empty list if the API request
        fails or no headlines are available.
    """
    if not symbols:
        return []

    params = {"symbols": ",".join(symbols), "limit": 50}
    headers = {
        "APCA-API-KEY-ID": API_KEY,
        "APCA-API-SECRET-KEY": API_SECRET,
    }
    try:
        response = requests.get(
            NEWS_API_URL, params=params, headers=headers, timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return [item.get("headline", "") for item in data.get("news", [])]
    except Exception as exc:  # pragma: no cover - network failure
        logger.error(f"Failed to fetch news: {exc}")
        return []
