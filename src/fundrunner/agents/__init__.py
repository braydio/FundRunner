"""FundRunner Agent Framework.

This package provides a standardized framework for building AI agents
that can perform various tasks in the algorithmic trading workflow,
including research, code generation, backtesting, risk analysis, and review.
"""

from .base import BaseAgent, AgentResult, AgentTask
from .orchestrator import AgentOrchestrator

__all__ = [
    "BaseAgent", 
    "AgentResult", 
    "AgentTask", 
    "AgentOrchestrator"
]
