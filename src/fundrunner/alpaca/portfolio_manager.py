
"""Simplified portfolio utilities and LLM-assisted weight suggestions."""

from __future__ import annotations

import json
import logging
from typing import Dict, Sequence

from fundrunner.alpaca.api_client import AlpacaClient
from fundrunner.services.news import fetch_news
from fundrunner.utils.gpt_client import ask_gpt

logger = logging.getLogger(__name__)


class PortfolioManager:
    def __init__(self):
        self.client = AlpacaClient()

    def view_account(self):
        return self.client.get_account()

    def view_positions(self):
        return self.client.list_positions()

    def view_position(self, symbol: str):
        return self.client.get_position(symbol)

    def determine_target_weights(
        self, symbols: Sequence[str]
    ) -> Dict[str, float]:
        """Return LLM-proposed portfolio weights for ``symbols``.

        News headlines for the provided symbols are fetched and included in the
        prompt so the model can weigh recent events. An empty dictionary is
        returned if the LLM call fails or the response cannot be parsed.
        """

        headlines = fetch_news(symbols)
        news_section = (
            "\n".join(f"- {h}" for h in headlines)
            if headlines
            else "No relevant news."
        )
        prompt = (
            f"Given the following news headlines:\n{news_section}\n\n"
            f"Provide recommended portfolio weights for: {', '.join(symbols)}."
            " Respond with a JSON object mapping symbols to weights."
        )
        response = ask_gpt(prompt)
        if not response:
            return {}
        try:
            return json.loads(response)
        except Exception as exc:
            logger.error(f"Failed to parse LLM response: {exc}")
            return {}
