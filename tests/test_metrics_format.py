
# test_metrics_format.py
import logging
from fundrunner.options.options_integration import format_primary_metric

# Set up logging for testing
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(message)s')

def test_format_primary_metric_long():
    # Test case for long option trade metrics
    evaluation = {
        "profit_ratio": 0.123456789, 
        "adjusted_probability": 0.65, 
        "expected_return": 0.08
    }
    # We choose "profit_ratio" as the primary key.
    formatted = format_primary_metric(evaluation, "profit_ratio", ["adjusted_probability", "expected_return"])
    expected_score = abs(0.123456789)
    total = expected_score + abs(0.65) + abs(0.08)
    expected_weight = expected_score / total if total > 0 else 0
    formatted_str = f"{0.123456789:.2f} (Score: {expected_score:.2f}, Weight: {expected_weight:.2f})"
    assert formatted.get("profit_ratio_formatted") == formatted_str, "Long metric formatting failed"
    logging.info("Long metric formatting passed with output: %s", formatted.get("profit_ratio_formatted"))

def test_format_primary_metric_spread():
    # Test case for a spread trade metric
    evaluation = {
        "risk_reward_ratio": 1.98765,
        "adjusted_probability": 0.55,
        "expected_return": 0.75
    }
    formatted = format_primary_metric(evaluation, "risk_reward_ratio", ["adjusted_probability", "expected_return"])
    expected_score = abs(1.98765)
    total = expected_score + abs(0.55) + abs(0.75)
    expected_weight = expected_score / total if total > 0 else 0
    formatted_str = f"{1.98765:.2f} (Score: {expected_score:.2f}, Weight: {expected_weight:.2f})"
    assert formatted.get("risk_reward_ratio_formatted") == formatted_str, "Spread metric formatting failed"
    logging.info("Spread metric formatting passed with output: %s", formatted.get("risk_reward_ratio_formatted"))

if __name__ == "__main__":
    test_format_primary_metric_long()
    test_format_primary_metric_spread()
    logging.info("All metric formatting tests passed.")
