"""Tests for enhanced GPT client with JSON support and error handling."""

import json
import unittest
from unittest.mock import patch, Mock, MagicMock
from fundrunner.utils.gpt_client import (
    ask_gpt_enhanced,
    ask_gpt_json,
    _clean_json_response,
    _estimate_cost,
    get_cost_summary,
    reset_cost_tracking,
    count_tokens
)


class TestGPTClientJSON(unittest.TestCase):
    """Test cases for enhanced GPT client functionality."""

    def setUp(self):
        """Reset cost tracking before each test."""
        reset_cost_tracking()

    def test_count_tokens_basic(self):
        """Test token counting functionality."""
        tokens = count_tokens("Hello world", "gpt-4o-mini")
        self.assertIsInstance(tokens, int)
        self.assertGreater(tokens, 0)

    def test_estimate_cost(self):
        """Test cost estimation for different models."""
        # Test known model
        cost_gpt4 = _estimate_cost(1000, "gpt-4")
        self.assertAlmostEqual(cost_gpt4, 0.06, places=4)
        
        # Test gpt-4o-mini
        cost_mini = _estimate_cost(1000, "gpt-4o-mini")
        self.assertAlmostEqual(cost_mini, 0.0015, places=4)
        
        # Test unknown model (should default to gpt-4 pricing)
        cost_unknown = _estimate_cost(1000, "unknown-model")
        self.assertEqual(cost_unknown, cost_gpt4)

    def test_cost_tracking(self):
        """Test cost tracking functionality."""
        summary = get_cost_summary()
        self.assertEqual(summary["total_tokens"], 0)
        self.assertEqual(summary["estimated_cost_usd"], 0.0)

    def test_clean_json_response_markdown(self):
        """Test cleaning JSON responses with markdown fences."""
        # JSON with markdown fences
        response = "```json\n{\"key\": \"value\"}\n```"
        cleaned = _clean_json_response(response)
        self.assertEqual(cleaned, '{"key": "value"}')
        
        # JSON with extra text
        response = "Here's the JSON:\n```json\n{\"result\": true}\n```\nHope this helps!"
        cleaned = _clean_json_response(response)
        self.assertEqual(cleaned, '{"result": true}')

    def test_clean_json_response_complex(self):
        """Test cleaning complex JSON responses."""
        # Nested JSON
        response = '{"data": {"nested": {"value": 42}}, "status": "ok"}'
        cleaned = _clean_json_response(response)
        self.assertEqual(cleaned, response)
        
        # Array response
        response = '[{"id": 1}, {"id": 2}]'
        cleaned = _clean_json_response(response)
        self.assertEqual(cleaned, response)

    def test_clean_json_response_empty(self):
        """Test cleaning empty or invalid responses."""
        self.assertEqual(_clean_json_response(""), "")
        self.assertEqual(_clean_json_response(None), "")
        
        # No JSON found
        text_only = "This is just text with no JSON"
        self.assertEqual(_clean_json_response(text_only), text_only)

    @patch('fundrunner.utils.gpt_client.openai_client')
    @patch('fundrunner.utils.gpt_client.USE_LOCAL_LLM', False)
    def test_ask_gpt_enhanced_success(self, mock_client):
        """Test successful GPT API call."""
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        
        mock_client.chat.completions.create.return_value = mock_response
        
        result = ask_gpt_enhanced("Test prompt", model="gpt-4o-mini")
        
        self.assertEqual(result, "Test response")
        mock_client.chat.completions.create.assert_called_once()

    @patch('fundrunner.utils.gpt_client._call_local_llm_enhanced')
    @patch('fundrunner.utils.gpt_client.USE_LOCAL_LLM', True)
    def test_ask_gpt_enhanced_local_llm(self, mock_local_call):
        """Test local LLM call."""
        mock_local_call.return_value = "Local LLM response"
        
        result = ask_gpt_enhanced("Test prompt")
        
        self.assertEqual(result, "Local LLM response")
        mock_local_call.assert_called_once()

    def test_ask_gpt_json_valid_response(self):
        """Test JSON parsing with valid response."""
        valid_json = '{"action": "buy", "quantity": 100, "symbol": "AAPL"}'
        
        with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
            mock_ask.return_value = valid_json
            
            result = ask_gpt_json("Generate trading decision")
            
            expected = {"action": "buy", "quantity": 100, "symbol": "AAPL"}
            self.assertEqual(result, expected)

    def test_ask_gpt_json_markdown_response(self):
        """Test JSON parsing with markdown-wrapped response."""
        markdown_response = "```json\n{\"status\": \"success\", \"data\": [1, 2, 3]}\n```"
        
        with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
            mock_ask.return_value = markdown_response
            
            result = ask_gpt_json("Get data")
            
            expected = {"status": "success", "data": [1, 2, 3]}
            self.assertEqual(result, expected)

    def test_ask_gpt_json_with_schema(self):
        """Test JSON parsing with schema validation."""
        schema = {
            "required": ["action", "symbol"],
            "properties": {
                "action": {"type": "string"},
                "symbol": {"type": "string"},
                "quantity": {"type": "number"}
            }
        }
        
        valid_response = '{"action": "sell", "symbol": "MSFT", "quantity": 50}'
        
        with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
            mock_ask.return_value = valid_response
            
            result = ask_gpt_json("Trade decision", schema=schema)
            
            expected = {"action": "sell", "symbol": "MSFT", "quantity": 50}
            self.assertEqual(result, expected)

    def test_ask_gpt_json_invalid_response(self):
        """Test JSON parsing with invalid response."""
        invalid_responses = [
            "This is not JSON at all",
            '{"incomplete": true',  # Missing closing brace
            "",  # Empty response
            None  # None response
        ]
        
        for invalid_response in invalid_responses:
            with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
                mock_ask.return_value = invalid_response
                
                result = ask_gpt_json("Test prompt")
                self.assertIsNone(result)

    def test_ask_gpt_json_mixed_content(self):
        """Test JSON parsing with mixed content response."""
        mixed_response = """
        Here's your analysis:
        
        The trading decision is:
        {"action": "hold", "reason": "market uncertainty", "confidence": 0.6}
        
        This is based on current market conditions.
        """
        
        with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
            mock_ask.return_value = mixed_response
            
            result = ask_gpt_json("Trading analysis")
            
            expected = {"action": "hold", "reason": "market uncertainty", "confidence": 0.6}
            self.assertEqual(result, expected)

    def test_ask_gpt_json_strict_mode(self):
        """Test JSON strict mode prompt enhancement."""
        with patch('fundrunner.utils.gpt_client.GPT_JSON_STRICT', True):
            with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
                mock_ask.return_value = '{"result": "test"}'
                
                ask_gpt_json("Test prompt")
                
                # Check that the prompt was enhanced with JSON instructions
                call_args = mock_ask.call_args[0][0]
                self.assertIn("IMPORTANT: Respond ONLY with valid JSON", call_args)

    def test_ask_gpt_json_schema_missing_keys(self):
        """Test schema validation with missing required keys."""
        schema = {
            "required": ["action", "symbol", "quantity"]
        }
        
        # Response missing 'quantity'
        incomplete_response = '{"action": "buy", "symbol": "AAPL"}'
        
        with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_ask:
            mock_ask.return_value = incomplete_response
            
            # Should still return the object but log a warning
            with patch('fundrunner.utils.gpt_client.logger') as mock_logger:
                result = ask_gpt_json("Trade decision", schema=schema)
                
                expected = {"action": "buy", "symbol": "AAPL"}
                self.assertEqual(result, expected)
                
                # Check that warning was logged
                mock_logger.warning.assert_called_once()

    @patch('fundrunner.utils.gpt_client.time.sleep')  # Mock sleep to speed up tests
    def test_retry_mechanism(self, mock_sleep):
        """Test retry mechanism with exponential backoff."""
        with patch('fundrunner.utils.gpt_client.openai_client') as mock_client:
            # Mock first two calls to fail, third to succeed
            mock_client.chat.completions.create.side_effect = [
                Exception("API Error 1"),
                Exception("API Error 2"),
                Mock(choices=[Mock(message=Mock(content="Success"))])
            ]
            
            result = ask_gpt_enhanced("Test prompt")
            
            self.assertEqual(result, "Success")
            self.assertEqual(mock_client.chat.completions.create.call_count, 3)
            # Sleep called for: rate limiting (3x) + retries (2x) = 5x
            self.assertEqual(mock_sleep.call_count, 5)

    def test_backwards_compatibility(self):
        """Test that legacy ask_gpt function still works."""
        from fundrunner.utils.gpt_client import ask_gpt
        
        with patch('fundrunner.utils.gpt_client.ask_gpt_enhanced') as mock_enhanced:
            mock_enhanced.return_value = "Legacy test"
            
            result = ask_gpt("Test prompt", "gpt-4")
            
            self.assertEqual(result, "Legacy test")
            mock_enhanced.assert_called_once_with("Test prompt", model="gpt-4")


if __name__ == '__main__':
    unittest.main()
