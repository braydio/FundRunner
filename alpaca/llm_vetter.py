
# llm_vetter.py
import logging
from gpt_client import ask_gpt

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class LLMVetter:
    def __init__(self, vendor="local"):
        """
        Args:
            vendor (str): Vendor to use for LLM query.
                          (Note: This parameter is maintained for compatibility,
                           but the actual LLM query logic now uses the unified ask_gpt function.)
        """
        self.vendor = vendor.lower()

    def vet_trade_logic(self, trade_details: dict, prompt: str = None) -> bool:
        """
        Sends trade logic details to an LLM for review and returns whether the trade is approved.
        
        Args:
            trade_details (dict): A dictionary containing trade details.
            prompt (str, optional): A custom prompt. Defaults to a prompt that reviews the provided trade details.
        
        Returns:
            bool: True if the trade is approved by the LLM, otherwise False.
        """
        if prompt is None:
            prompt = f"Review the following trade statistics. What stands out about this trade? What is another statistic that should be measured in evaluating the trade? Details: {trade_details}"
        try:
            response = ask_gpt(prompt)
            if response:
                response_lower = response.lower()
                logger.debug("LLM vetting response: %s", response_lower)
                return "approved" in response_lower or "yes" in response_lower
            else:
                logger.error("No response received from LLM vetting.")
                return False
        except Exception as e:
            logger.error("Error during LLM vetting: %s", e, exc_info=True)
            return False

