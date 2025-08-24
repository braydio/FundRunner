"""Thin wrapper around :mod:`gpt_client` for backward compatibility."""

from fundrunner.utils.gpt_client import ask_gpt


def get_account_overview(prompt: str) -> str:
    """Return GPT-generated trading advice."""
    return ask_gpt(prompt)
