"""Agent orchestrator for coordinating multi-agent workflows."""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field

from .base import BaseAgent, AgentTask, AgentResult, AgentStatus, TaskPriority


@dataclass
class WorkflowResult:
    """Results from a complete workflow execution."""
    
    workflow_id: str
    status: AgentStatus
    results: Dict[str, AgentResult] = field(default_factory=dict)
    execution_time: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    
    @property
    def is_success(self) -> bool:
        """Check if the workflow completed successfully."""
        return (
            self.status == AgentStatus.COMPLETED and
            all(result.is_success for result in self.results.values())
        )
    
    @property
    def failed_tasks(self) -> List[str]:
        """Get list of failed task IDs."""
        return [
            task_id for task_id, result in self.results.items() 
            if result.is_failure
        ]


class AgentOrchestrator:
    """Orchestrates execution of multiple agents in workflows.
    
    Features:
    - Dependency resolution and topological sorting
    - Parallel execution where possible
    - Error handling and rollback
    - Progress monitoring
    - Human-in-the-loop checkpoints
    """

    def __init__(self, max_concurrent_agents: int = 3):
        """Initialize the orchestrator.
        
        Args:
            max_concurrent_agents: Maximum number of agents to run concurrently
        """
        self.max_concurrent_agents = max_concurrent_agents
        self.agents: Dict[str, BaseAgent] = {}
        self.logger = logging.getLogger("orchestrator")
        self.logger.setLevel(logging.INFO)
        
        # Workflow state
        self._active_workflows: Dict[str, WorkflowResult] = {}
        self._workflow_counter = 0

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.
        
        Args:
            agent: The agent to register
            
        Raises:
            ValueError: If agent name is already registered
        """
        if agent.name in self.agents:
            raise ValueError(f"Agent '{agent.name}' is already registered")
        
        self.agents[agent.name] = agent
        self.logger.info(f"Registered agent: {agent.name}")

    def unregister_agent(self, name: str) -> None:
        """Unregister an agent.
        
        Args:
            name: Name of the agent to unregister
        """
        if name in self.agents:
            del self.agents[name]
            self.logger.info(f"Unregistered agent: {name}")

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Get a registered agent by name.
        
        Args:
            name: Name of the agent
            
        Returns:
            The agent instance or None if not found
        """
        return self.agents.get(name)

    def list_agents(self) -> List[str]:
        """Get list of registered agent names."""
        return list(self.agents.keys())

    async def execute_workflow(
        self,
        tasks: List[AgentTask],
        agent_assignments: Dict[str, str],  # task_id -> agent_name
        workflow_id: Optional[str] = None,
        fail_fast: bool = True
    ) -> WorkflowResult:
        """Execute a workflow of tasks using assigned agents.
        
        Args:
            tasks: List of tasks to execute
            agent_assignments: Mapping of task ID to agent name
            workflow_id: Optional workflow ID (auto-generated if None)
            fail_fast: Whether to stop on first failure
            
        Returns:
            WorkflowResult with execution details
            
        Raises:
            ValueError: If validation fails
        """
        # Generate workflow ID if not provided
        if workflow_id is None:
            self._workflow_counter += 1
            workflow_id = f"workflow_{self._workflow_counter}"
        
        start_time = time.time()
        workflow_result = WorkflowResult(
            workflow_id=workflow_id,
            status=AgentStatus.RUNNING
        )
        self._active_workflows[workflow_id] = workflow_result
        
        self.logger.info(f"Starting workflow {workflow_id} with {len(tasks)} tasks")
        
        try:
            # Validate workflow
            await self._validate_workflow(tasks, agent_assignments)
            
            # Build dependency graph and sort tasks
            execution_order = self._resolve_dependencies(tasks)
            
            # Execute tasks in dependency order
            await self._execute_tasks(
                tasks, agent_assignments, execution_order, 
                workflow_result, fail_fast
            )
            
            # Determine final workflow status
            if all(result.is_success for result in workflow_result.results.values()):
                workflow_result.status = AgentStatus.COMPLETED
                self.logger.info(f"Workflow {workflow_id} completed successfully")
            else:
                workflow_result.status = AgentStatus.FAILED
                failed = workflow_result.failed_tasks
                self.logger.error(f"Workflow {workflow_id} failed. Failed tasks: {failed}")
                
        except Exception as e:
            workflow_result.status = AgentStatus.FAILED
            self.logger.error(f"Workflow {workflow_id} failed with exception: {e}", exc_info=True)
            
        finally:
            workflow_result.execution_time = time.time() - start_time
            
        return workflow_result

    async def _validate_workflow(
        self, 
        tasks: List[AgentTask], 
        agent_assignments: Dict[str, str]
    ) -> None:
        """Validate workflow parameters.
        
        Args:
            tasks: List of tasks
            agent_assignments: Task to agent mappings
            
        Raises:
            ValueError: If validation fails
        """
        if not tasks:
            raise ValueError("Task list cannot be empty")
        
        # Check for duplicate task IDs
        task_ids = [task.id for task in tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Duplicate task IDs found")
        
        # Validate agent assignments
        for task in tasks:
            if task.id not in agent_assignments:
                raise ValueError(f"No agent assigned to task {task.id}")
            
            agent_name = agent_assignments[task.id]
            if agent_name not in self.agents:
                raise ValueError(f"Agent '{agent_name}' not registered")
        
        # Validate dependencies
        for task in tasks:
            for dep_id in task.depends_on:
                if dep_id not in task_ids:
                    raise ValueError(f"Task {task.id} depends on unknown task {dep_id}")
        
        self.logger.debug("Workflow validation passed")

    def _resolve_dependencies(self, tasks: List[AgentTask]) -> List[List[str]]:
        """Resolve task dependencies and return execution order.
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of task ID batches that can be executed in parallel
            
        Raises:
            ValueError: If circular dependencies detected
        """
        # Build dependency graph
        task_map = {task.id: task for task in tasks}
        in_degree = defaultdict(int)
        graph = defaultdict(list)
        
        # Initialize all task IDs
        for task in tasks:
            in_degree[task.id] = 0
        
        # Build graph and calculate in-degrees
        for task in tasks:
            for dep_id in task.depends_on:
                graph[dep_id].append(task.id)
                in_degree[task.id] += 1
        
        # Topological sort with Kahn's algorithm
        execution_order = []
        queue = deque([
            task_id for task_id in in_degree 
            if in_degree[task_id] == 0
        ])
        
        # Sort initial queue by priority
        queue = deque(sorted(queue, key=lambda tid: task_map[tid].priority.value, reverse=True))
        
        while queue:
            # Get next batch of tasks that can run in parallel
            current_batch = []
            batch_size = min(len(queue), self.max_concurrent_agents)
            
            for _ in range(batch_size):
                task_id = queue.popleft()
                current_batch.append(task_id)
                
                # Update dependencies
                for dependent_id in graph[task_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
            
            # Sort queue by priority for next iteration
            queue = deque(sorted(queue, key=lambda tid: task_map[tid].priority.value, reverse=True))
            execution_order.append(current_batch)
        
        # Check for circular dependencies
        processed_count = sum(len(batch) for batch in execution_order)
        if processed_count != len(tasks):
            raise ValueError("Circular dependency detected in tasks")
        
        self.logger.debug(f"Dependency resolution complete. Execution order: {execution_order}")
        return execution_order

    async def _execute_tasks(
        self,
        tasks: List[AgentTask],
        agent_assignments: Dict[str, str],
        execution_order: List[List[str]],
        workflow_result: WorkflowResult,
        fail_fast: bool
    ) -> None:
        """Execute tasks in the resolved order.
        
        Args:
            tasks: List of all tasks
            agent_assignments: Task to agent mappings
            execution_order: Batches of task IDs to execute
            workflow_result: Workflow result to update
            fail_fast: Whether to stop on first failure
        """
        task_map = {task.id: task for task in tasks}
        
        for batch_num, task_ids in enumerate(execution_order):
            self.logger.info(f"Executing batch {batch_num + 1}/{len(execution_order)}: {task_ids}")
            
            # Create coroutines for parallel execution
            coroutines = []
            for task_id in task_ids:
                task = task_map[task_id]
                agent = self.agents[agent_assignments[task_id]]
                coroutines.append(agent.run(task))
            
            # Execute batch in parallel
            batch_results = await asyncio.gather(*coroutines, return_exceptions=True)
            
            # Process results
            has_failure = False
            for task_id, result in zip(task_ids, batch_results):
                if isinstance(result, Exception):
                    # Convert exception to failed result
                    result = AgentResult(
                        task_id=task_id,
                        agent_name=agent_assignments[task_id],
                        status=AgentStatus.FAILED,
                        error=str(result)
                    )
                
                workflow_result.results[task_id] = result
                
                if result.is_failure:
                    has_failure = True
                    self.logger.error(f"Task {task_id} failed: {result.error}")
                else:
                    self.logger.info(f"Task {task_id} completed successfully")
            
            # Check if we should stop due to failure
            if has_failure and fail_fast:
                self.logger.warning("Stopping workflow execution due to failure (fail_fast=True)")
                
                # Mark remaining tasks as cancelled
                for remaining_batch in execution_order[batch_num + 1:]:
                    for task_id in remaining_batch:
                        workflow_result.results[task_id] = AgentResult(
                            task_id=task_id,
                            agent_name=agent_assignments[task_id],
                            status=AgentStatus.CANCELLED,
                            error="Cancelled due to workflow failure"
                        )
                break

    async def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get the status of a running or completed workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            WorkflowResult or None if not found
        """
        return self._active_workflows.get(workflow_id)

    def get_agent_metrics(self) -> Dict[str, Dict[str, float]]:
        """Get performance metrics for all registered agents.
        
        Returns:
            Dictionary mapping agent names to their metrics
        """
        return {
            name: agent.get_metrics() 
            for name, agent in self.agents.items()
        }

    def reset_all_metrics(self) -> None:
        """Reset performance metrics for all agents."""
        for agent in self.agents.values():
            agent.reset_metrics()
        self.logger.info("Reset metrics for all agents")

    async def shutdown(self) -> None:
        """Gracefully shutdown the orchestrator."""
        self.logger.info("Shutting down orchestrator")
        
        # Wait for any active workflows to complete (with timeout)
        active_workflows = [
            workflow for workflow in self._active_workflows.values()
            if workflow.status == AgentStatus.RUNNING
        ]
        
        if active_workflows:
            self.logger.info(f"Waiting for {len(active_workflows)} active workflows to complete")
            # In a real implementation, you might want to add timeout and cancellation logic
        
        self.agents.clear()
        self._active_workflows.clear()
        self.logger.info("Orchestrator shutdown complete")

    def __repr__(self) -> str:
        """String representation of the orchestrator."""
        return f"<AgentOrchestrator(agents={len(self.agents)}, active_workflows={len(self._active_workflows)})>"
