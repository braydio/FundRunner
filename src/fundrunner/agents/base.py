"""Base agent class and supporting types for the FundRunner agent framework."""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from fundrunner.utils.gpt_client import ask_gpt_enhanced, ask_gpt_json
from fundrunner.utils.config import AGENTS_HUMAN_IN_LOOP, AGENTS_AUTO_APPROVE


class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentTask:
    """Represents a task to be executed by an agent."""
    
    id: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    depends_on: List[str] = field(default_factory=list)  # Task IDs this depends on
    created_at: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """Validate task parameters after initialization."""
        if not self.id:
            raise ValueError("Task ID cannot be empty")
        if not self.description:
            raise ValueError("Task description cannot be empty")


@dataclass
class AgentResult:
    """Represents the result of an agent's task execution."""
    
    task_id: str
    agent_name: str
    status: AgentStatus
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    artifacts: List[str] = field(default_factory=list)  # File paths created
    metrics: Dict[str, Union[int, float, str]] = field(default_factory=dict)
    execution_time: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    
    @property
    def is_success(self) -> bool:
        """Check if the task completed successfully."""
        return self.status == AgentStatus.COMPLETED and self.error is None
    
    @property
    def is_failure(self) -> bool:
        """Check if the task failed."""
        return self.status == AgentStatus.FAILED or self.error is not None


class BaseAgent(ABC):
    """Base class for all FundRunner agents.
    
    Provides common functionality including:
    - Standardized task execution interface
    - LLM client integration
    - Context provider management
    - Logging and metrics
    - Human-in-the-loop approvals
    """

    def __init__(
        self, 
        name: str,
        description: str = "",
        tools: Optional[List[str]] = None,
        context_providers: Optional[List[str]] = None,
        require_approval: bool = False
    ):
        """Initialize the base agent.
        
        Args:
            name: Agent name (must be unique)
            description: Human-readable description
            tools: List of tool names this agent can use
            context_providers: List of context provider names
            require_approval: Whether this agent requires human approval
        """
        self.name = name
        self.description = description
        self.tools = tools or []
        self.context_providers = context_providers or []
        self.require_approval = require_approval
        
        # Set up logging
        self.logger = logging.getLogger(f"agent.{name}")
        self.logger.setLevel(logging.INFO)
        
        # Execution metrics
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.success_count = 0
        self.failure_count = 0
        
        self.logger.info(f"Initialized agent '{name}' with tools: {tools}")

    async def run(self, task: AgentTask) -> AgentResult:
        """Execute a task and return the result.
        
        Args:
            task: The task to execute
            
        Returns:
            AgentResult with execution details
        """
        start_time = time.time()
        self.execution_count += 1
        
        result = AgentResult(
            task_id=task.id,
            agent_name=self.name,
            status=AgentStatus.RUNNING
        )
        
        self.logger.info(f"Starting task {task.id}: {task.description}")
        
        try:
            # Pre-execution validation
            await self._validate_task(task)
            
            # Human approval if required
            if self.require_approval and not await self._get_approval(task):
                result.status = AgentStatus.CANCELLED
                result.error = "Task cancelled by user"
                return result
            
            # Execute the main task logic
            execution_result = await self._execute(task)
            
            # Post-execution validation
            await self._validate_result(execution_result)
            
            result.result = execution_result
            result.status = AgentStatus.COMPLETED
            self.success_count += 1
            
            self.logger.info(f"Completed task {task.id} successfully")
            
        except Exception as e:
            result.status = AgentStatus.FAILED
            result.error = str(e)
            self.failure_count += 1
            
            self.logger.error(f"Task {task.id} failed: {e}", exc_info=True)
        
        finally:
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            self.total_execution_time += execution_time
            
            result.metrics = {
                "execution_time": execution_time,
                "tokens_used": getattr(self, '_last_tokens_used', 0),
                "llm_calls": getattr(self, '_last_llm_calls', 0),
            }
            
        return result

    @abstractmethod
    async def _execute(self, task: AgentTask) -> Dict[str, Any]:
        """Execute the main task logic. Must be implemented by subclasses.
        
        Args:
            task: The task to execute
            
        Returns:
            Dictionary containing the execution results
            
        Raises:
            Exception: If execution fails
        """
        pass

    async def _validate_task(self, task: AgentTask) -> None:
        """Validate task parameters before execution.
        
        Args:
            task: The task to validate
            
        Raises:
            ValueError: If task parameters are invalid
        """
        # Base validation - can be overridden by subclasses
        if not task.id:
            raise ValueError("Task ID is required")
        if not task.description:
            raise ValueError("Task description is required")
        
        self.logger.debug(f"Task {task.id} validation passed")

    async def _validate_result(self, result: Dict[str, Any]) -> None:
        """Validate execution results after completion.
        
        Args:
            result: The execution result to validate
            
        Raises:
            ValueError: If result is invalid
        """
        # Base validation - can be overridden by subclasses
        if result is None:
            raise ValueError("Execution result cannot be None")
        
        self.logger.debug("Result validation passed")

    async def _get_approval(self, task: AgentTask) -> bool:
        """Get human approval for task execution.
        
        Args:
            task: The task requiring approval
            
        Returns:
            True if approved, False if denied
        """
        if not AGENTS_HUMAN_IN_LOOP:
            return AGENTS_AUTO_APPROVE
        
        print(f"\n🤖 Agent '{self.name}' requests approval:")
        print(f"   Task: {task.description}")
        print(f"   Parameters: {task.parameters}")
        
        while True:
            response = input("   Approve? [y/n/details]: ").lower().strip()
            
            if response in ['y', 'yes']:
                self.logger.info(f"Task {task.id} approved by user")
                return True
            elif response in ['n', 'no']:
                self.logger.info(f"Task {task.id} denied by user")
                return False
            elif response == 'details':
                print(f"   Agent: {self.name}")
                print(f"   Description: {self.description}")
                print(f"   Tools: {self.tools}")
                print(f"   Context Providers: {self.context_providers}")
            else:
                print("   Please enter 'y', 'n', or 'details'")

    def ask_llm(self, prompt: str, model: str = None) -> Optional[str]:
        """Query the LLM with the given prompt.
        
        Args:
            prompt: The prompt to send
            model: Optional model override
            
        Returns:
            LLM response or None if failed
        """
        self._last_llm_calls = getattr(self, '_last_llm_calls', 0) + 1
        response = ask_gpt_enhanced(prompt, model=model)
        
        if response:
            # Estimate token usage (rough approximation)
            tokens = len(response.split()) * 1.3  # Rough tokens per word
            self._last_tokens_used = getattr(self, '_last_tokens_used', 0) + tokens
        
        return response

    def ask_llm_json(
        self, 
        prompt: str, 
        schema: Optional[Dict[str, Any]] = None,
        model: str = None
    ) -> Optional[Dict[str, Any]]:
        """Query the LLM for structured JSON response.
        
        Args:
            prompt: The prompt to send
            schema: Optional JSON schema for validation
            model: Optional model override
            
        Returns:
            Parsed JSON response or None if failed
        """
        self._last_llm_calls = getattr(self, '_last_llm_calls', 0) + 1
        response = ask_gpt_json(prompt, schema=schema, model=model)
        
        if response:
            # Rough token estimation for JSON responses
            import json
            tokens = len(json.dumps(response).split()) * 1.3
            self._last_tokens_used = getattr(self, '_last_tokens_used', 0) + tokens
        
        return response

    def get_metrics(self) -> Dict[str, Union[int, float]]:
        """Get agent performance metrics.
        
        Returns:
            Dictionary of performance metrics
        """
        avg_execution_time = (
            self.total_execution_time / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        
        success_rate = (
            self.success_count / self.execution_count 
            if self.execution_count > 0 else 0.0
        )
        
        return {
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "total_execution_time": self.total_execution_time,
            "avg_execution_time": avg_execution_time,
        }

    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.success_count = 0
        self.failure_count = 0
        self._last_tokens_used = 0
        self._last_llm_calls = 0
        
        self.logger.info("Agent metrics reset")

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"<{self.__class__.__name__}(name='{self.name}')>"
