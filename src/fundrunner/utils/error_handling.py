"""Centralized error handling utilities for production-ready error management."""

import logging
import sys
import traceback
from typing import Optional, Any, Callable
from functools import wraps
from enum import Enum

# Configure module logger
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types for consistent handling."""
    
    # API and Network Errors
    API_CONNECTION = "api_connection"
    API_AUTHENTICATION = "api_authentication"
    API_RATE_LIMIT = "api_rate_limit"
    API_INVALID_REQUEST = "api_invalid_request"
    
    # Trading and Market Data Errors
    TRADING_ORDER_REJECTED = "trading_order_rejected"
    TRADING_INSUFFICIENT_FUNDS = "trading_insufficient_funds"
    TRADING_MARKET_CLOSED = "trading_market_closed"
    TRADING_SYMBOL_NOT_FOUND = "trading_symbol_not_found"
    
    # Configuration and Environment Errors
    CONFIG_MISSING = "config_missing"
    CONFIG_INVALID = "config_invalid"
    ENV_SETUP = "env_setup"
    
    # File and Data Errors
    FILE_NOT_FOUND = "file_not_found"
    FILE_PERMISSION = "file_permission"
    DATA_PARSING = "data_parsing"
    DATA_VALIDATION = "data_validation"
    
    # General Application Errors
    VALIDATION = "validation"
    UNEXPECTED = "unexpected"


class FundRunnerError(Exception):
    """Base exception class for FundRunner application errors."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNEXPECTED,
        details: Optional[dict] = None,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}
        self.original_exception = original_exception
        
        # Log the error immediately
        self._log_error()
    
    def _log_error(self):
        """Log the error with appropriate level and details."""
        log_data = {
            "error_type": self.error_type.value,
            "message": str(self),
            "details": self.details
        }
        
        if self.original_exception:
            log_data["original_exception"] = str(self.original_exception)
        
        # Use different log levels based on error type
        if self.error_type in [
            ErrorType.API_CONNECTION,
            ErrorType.CONFIG_MISSING,
            ErrorType.ENV_SETUP
        ]:
            logger.error("FundRunner Error: %s", log_data, exc_info=self.original_exception)
        elif self.error_type in [
            ErrorType.API_RATE_LIMIT,
            ErrorType.TRADING_MARKET_CLOSED
        ]:
            logger.warning("FundRunner Warning: %s", log_data)
        else:
            logger.error("FundRunner Error: %s", log_data, exc_info=self.original_exception)


class TradingError(FundRunnerError):
    """Specific exception for trading-related errors."""
    
    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        order_details: Optional[dict] = None,
        error_type: ErrorType = ErrorType.TRADING_ORDER_REJECTED,
        original_exception: Optional[Exception] = None
    ):
        details = {"symbol": symbol, "order_details": order_details}
        super().__init__(message, error_type, details, original_exception)


class ConfigError(FundRunnerError):
    """Specific exception for configuration-related errors."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
        error_type: ErrorType = ErrorType.CONFIG_INVALID,
        original_exception: Optional[Exception] = None
    ):
        details = {"config_key": config_key, "expected_type": expected_type}
        super().__init__(message, error_type, details, original_exception)


def handle_api_errors(func: Callable) -> Callable:
    """Decorator to standardize API error handling."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Map common API errors to our error types
            error_str = str(e).lower()
            
            if "unauthorized" in error_str or "authentication" in error_str:
                raise FundRunnerError(
                    f"API Authentication failed: {e}",
                    ErrorType.API_AUTHENTICATION,
                    {"function": func.__name__, "args": str(args)[:200]},
                    e
                )
            elif "rate limit" in error_str or "too many requests" in error_str:
                raise FundRunnerError(
                    f"API rate limit exceeded: {e}",
                    ErrorType.API_RATE_LIMIT,
                    {"function": func.__name__},
                    e
                )
            elif "connection" in error_str or "timeout" in error_str:
                raise FundRunnerError(
                    f"API connection error: {e}",
                    ErrorType.API_CONNECTION,
                    {"function": func.__name__},
                    e
                )
            elif "invalid" in error_str or "bad request" in error_str:
                raise FundRunnerError(
                    f"Invalid API request: {e}",
                    ErrorType.API_INVALID_REQUEST,
                    {"function": func.__name__, "args": str(args)[:200]},
                    e
                )
            else:
                # Re-raise as unexpected error
                raise FundRunnerError(
                    f"Unexpected API error in {func.__name__}: {e}",
                    ErrorType.UNEXPECTED,
                    {"function": func.__name__},
                    e
                )
    
    return wrapper


def handle_trading_errors(func: Callable) -> Callable:
    """Decorator to standardize trading operation error handling."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            
            # Extract symbol and order details if available
            symbol = None
            order_details = None
            
            if len(args) > 1:
                symbol = str(args[1]) if args[1] else None
            
            if "insufficient" in error_str and "funds" in error_str:
                raise TradingError(
                    f"Insufficient funds for trading operation: {e}",
                    symbol=symbol,
                    error_type=ErrorType.TRADING_INSUFFICIENT_FUNDS,
                    original_exception=e
                )
            elif "market" in error_str and "closed" in error_str:
                raise TradingError(
                    f"Market is closed: {e}",
                    symbol=symbol,
                    error_type=ErrorType.TRADING_MARKET_CLOSED,
                    original_exception=e
                )
            elif "symbol" in error_str and ("not found" in error_str or "invalid" in error_str):
                raise TradingError(
                    f"Symbol not found or invalid: {e}",
                    symbol=symbol,
                    error_type=ErrorType.TRADING_SYMBOL_NOT_FOUND,
                    original_exception=e
                )
            else:
                # Re-raise as general trading error
                raise TradingError(
                    f"Trading operation failed: {e}",
                    symbol=symbol,
                    original_exception=e
                )
    
    return wrapper


def safe_execute(func: Callable, *args, **kwargs):
    """Safely execute a function with error handling.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        tuple: (success: bool, result_or_exception)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        logger.exception(f"Safe execution failed: {e}")
        return False, e
        
        
async def safe_execute_async(func: Callable, *args, **kwargs):
    """Safely execute an async function with error handling.
    
    Args:
        func: Async function to execute
        *args: Positional arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        tuple: (success: bool, result_or_exception)
    """
    try:
        result = await func(*args, **kwargs)
        return True, result
    except Exception as e:
        logger.exception(f"Safe async execution failed: {e}")
        return False, e


def validate_required_config(config_dict: dict, required_keys: list) -> None:
    """Validate that required configuration keys are present and not empty."""
    
    missing_keys = []
    invalid_keys = []
    
    for key in required_keys:
        if key not in config_dict:
            missing_keys.append(key)
        elif not config_dict[key] or str(config_dict[key]).startswith("your_"):
            invalid_keys.append(key)
    
    if missing_keys:
        raise ConfigError(
            f"Missing required configuration keys: {', '.join(missing_keys)}",
            error_type=ErrorType.CONFIG_MISSING,
            details={"missing_keys": missing_keys}
        )
    
    if invalid_keys:
        raise ConfigError(
            f"Invalid or placeholder configuration values for keys: {', '.join(invalid_keys)}",
            error_type=ErrorType.CONFIG_INVALID,
            details={"invalid_keys": invalid_keys}
        )


def format_user_error(error: Exception, context: str = None) -> str:
    """Format an error message for user-friendly display.
    
    Args:
        error: The exception to format
        context: Optional context string to prefix the message
        
    Returns:
        Formatted user-friendly error message
    """
    
    if isinstance(error, FundRunnerError):
        base_message = str(error)
        
        # Add helpful context based on error type
        if error.error_type == ErrorType.API_AUTHENTICATION:
            formatted = f"{base_message}\n💡 Check your API keys in the .env file"
        elif error.error_type == ErrorType.TRADING_INSUFFICIENT_FUNDS:
            formatted = f"{base_message}\n💡 Check your account balance or reduce position size"
        elif error.error_type == ErrorType.TRADING_MARKET_CLOSED:
            formatted = f"{base_message}\n💡 Try again during market hours (9:30 AM - 4:00 PM ET)"
        elif error.error_type == ErrorType.CONFIG_MISSING:
            formatted = f"{base_message}\n💡 Run 'cp .env.example .env' and configure your settings"
        else:
            formatted = base_message
    else:
        # For non-FundRunnerError exceptions
        formatted = f"Unexpected error: {str(error)}"
    
    # Add context if provided
    if context:
        return f"{context}: {formatted}"
    
    return formatted


def setup_global_error_handler():
    """Setup global exception handler for uncaught exceptions."""
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Format user-friendly error message
        user_message = format_user_error(exc_value)
        print(f"\n❌ Application Error: {user_message}", file=sys.stderr)
    
    sys.excepthook = handle_exception
