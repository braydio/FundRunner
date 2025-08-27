"""Tests for the FundRunner agent framework."""

import asyncio
import unittest
from unittest.mock import patch, AsyncMock
import tempfile
import os

from fundrunner.agents.base import BaseAgent, AgentTask, AgentResult, AgentStatus, TaskPriority
from fundrunner.agents.orchestrator import AgentOrchestrator, WorkflowResult
from fundrunner.agents.prompts import get_template, PromptTemplate, create_finance_context
from fundrunner.agents.io import DiffBuilder, safe_read_file, safe_write_file, create_artifact_file
from fundrunner.agents.example_agent import MockTradingAnalysisAgent, MockCodeGeneratorAgent


class MockAgent(BaseAgent):
    """Simple mock agent for testing."""
    
    def __init__(self, name: str, should_fail: bool = False, execution_delay: float = 0.0):
        super().__init__(name, f"Mock agent {name}")
        self.should_fail = should_fail
        self.execution_delay = execution_delay
        self.execution_calls = []
    
    async def _execute(self, task: AgentTask):
        """Mock execution that can be configured to succeed or fail."""
        self.execution_calls.append(task.id)
        
        if self.execution_delay > 0:
            await asyncio.sleep(self.execution_delay)
        
        if self.should_fail:
            raise Exception(f"Mock failure in agent {self.name}")
        
        return {
            "task_id": task.id,
            "agent_name": self.name,
            "result": "success",
            "processed_params": task.parameters
        }


class TestAgentBase(unittest.TestCase):
    """Test cases for the base agent functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.agent = MockAgent("test_agent")
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        self.assertEqual(self.agent.name, "test_agent")
        self.assertEqual(self.agent.description, "Mock agent test_agent")
        self.assertEqual(self.agent.execution_count, 0)
        self.assertEqual(self.agent.success_count, 0)
        self.assertEqual(self.agent.failure_count, 0)
    
    def test_agent_task_creation(self):
        """Test agent task creation and validation."""
        task = AgentTask(
            id="test_task",
            description="Test task description",
            parameters={"param1": "value1"},
            priority=TaskPriority.HIGH
        )
        
        self.assertEqual(task.id, "test_task")
        self.assertEqual(task.priority, TaskPriority.HIGH)
        self.assertEqual(task.parameters["param1"], "value1")
    
    def test_agent_task_validation_errors(self):
        """Test task validation errors."""
        with self.assertRaises(ValueError):
            AgentTask(id="", description="Test")
        
        with self.assertRaises(ValueError):
            AgentTask(id="test", description="")
    
    async def test_agent_successful_execution(self):
        """Test successful agent task execution."""
        task = AgentTask(
            id="success_task",
            description="Test successful execution",
            parameters={"test_param": "test_value"}
        )
        
        result = await self.agent.run(task)
        
        self.assertTrue(result.is_success)
        self.assertEqual(result.status, AgentStatus.COMPLETED)
        self.assertEqual(result.task_id, "success_task")
        self.assertEqual(result.agent_name, "test_agent")
        self.assertIsNotNone(result.execution_time)
        self.assertIn("result", result.result)
    
    async def test_agent_failed_execution(self):
        """Test failed agent task execution."""
        failing_agent = MockAgent("failing_agent", should_fail=True)
        
        task = AgentTask(
            id="fail_task",
            description="Test failed execution"
        )
        
        result = await failing_agent.run(task)
        
        self.assertTrue(result.is_failure)
        self.assertEqual(result.status, AgentStatus.FAILED)
        self.assertIsNotNone(result.error)
        self.assertIn("Mock failure", result.error)
    
    def test_agent_metrics(self):
        """Test agent metrics tracking."""
        initial_metrics = self.agent.get_metrics()
        self.assertEqual(initial_metrics["execution_count"], 0)
        self.assertEqual(initial_metrics["success_rate"], 0.0)
        
        # Reset metrics should work
        self.agent.reset_metrics()
        metrics = self.agent.get_metrics()
        self.assertEqual(metrics["execution_count"], 0)


class TestAgentOrchestrator(unittest.TestCase):
    """Test cases for the agent orchestrator."""
    
    def setUp(self):
        """Set up test orchestrator."""
        self.orchestrator = AgentOrchestrator(max_concurrent_agents=3)
        
        # Register test agents
        self.agent1 = MockAgent("agent1")
        self.agent2 = MockAgent("agent2")
        self.agent3 = MockAgent("agent3", execution_delay=0.1)
        
        self.orchestrator.register_agent(self.agent1)
        self.orchestrator.register_agent(self.agent2)
        self.orchestrator.register_agent(self.agent3)
    
    def test_agent_registration(self):
        """Test agent registration and management."""
        self.assertIn("agent1", self.orchestrator.list_agents())
        self.assertIn("agent2", self.orchestrator.list_agents())
        self.assertEqual(len(self.orchestrator.list_agents()), 3)
        
        # Test duplicate registration
        with self.assertRaises(ValueError):
            self.orchestrator.register_agent(self.agent1)
        
        # Test unregistration
        self.orchestrator.unregister_agent("agent3")
        self.assertNotIn("agent3", self.orchestrator.list_agents())
    
    async def test_simple_workflow_execution(self):
        """Test execution of a simple workflow."""
        tasks = [
            AgentTask(
                id="task1",
                description="First task",
                parameters={"step": 1}
            ),
            AgentTask(
                id="task2", 
                description="Second task",
                parameters={"step": 2}
            )
        ]
        
        assignments = {
            "task1": "agent1",
            "task2": "agent2"
        }
        
        result = await self.orchestrator.execute_workflow(
            tasks=tasks,
            agent_assignments=assignments,
            workflow_id="test_workflow"
        )
        
        self.assertTrue(result.is_success)
        self.assertEqual(result.status, AgentStatus.COMPLETED)
        self.assertEqual(len(result.results), 2)
        self.assertIn("task1", result.results)
        self.assertIn("task2", result.results)
    
    async def test_dependency_resolution(self):
        """Test task dependency resolution."""
        tasks = [
            AgentTask(
                id="task_a",
                description="Independent task A"
            ),
            AgentTask(
                id="task_b",
                description="Task B depends on A",
                depends_on=["task_a"]
            ),
            AgentTask(
                id="task_c",
                description="Task C depends on B", 
                depends_on=["task_b"]
            )
        ]
        
        assignments = {
            "task_a": "agent1",
            "task_b": "agent2", 
            "task_c": "agent3"
        }
        
        result = await self.orchestrator.execute_workflow(
            tasks=tasks,
            agent_assignments=assignments
        )
        
        self.assertTrue(result.is_success)
        
        # Check execution order based on calls
        self.assertEqual(self.agent1.execution_calls[0], "task_a")
        self.assertEqual(self.agent2.execution_calls[0], "task_b")
        self.assertEqual(self.agent3.execution_calls[0], "task_c")
    
    async def test_parallel_execution(self):
        """Test parallel execution of independent tasks."""
        tasks = [
            AgentTask(id="parallel1", description="Parallel task 1"),
            AgentTask(id="parallel2", description="Parallel task 2"),
            AgentTask(id="parallel3", description="Parallel task 3")
        ]
        
        assignments = {
            "parallel1": "agent1",
            "parallel2": "agent2", 
            "parallel3": "agent3"
        }
        
        import time
        start_time = time.time()
        
        result = await self.orchestrator.execute_workflow(
            tasks=tasks,
            agent_assignments=assignments
        )
        
        execution_time = time.time() - start_time
        
        self.assertTrue(result.is_success)
        # Should complete in roughly the time of the slowest agent (0.1s)
        # rather than sum of all agents (0.1s total vs 0.3s sequential)
        self.assertLess(execution_time, 0.2)
    
    async def test_workflow_failure_handling(self):
        """Test workflow failure handling."""
        failing_agent = MockAgent("failing_agent", should_fail=True)
        self.orchestrator.register_agent(failing_agent)
        
        tasks = [
            AgentTask(id="good_task", description="Should succeed"),
            AgentTask(id="bad_task", description="Should fail"),
        ]
        
        assignments = {
            "good_task": "agent1",
            "bad_task": "failing_agent"
        }
        
        result = await self.orchestrator.execute_workflow(
            tasks=tasks,
            agent_assignments=assignments,
            fail_fast=True
        )
        
        self.assertFalse(result.is_success)
        self.assertEqual(result.status, AgentStatus.FAILED)
        self.assertIn("bad_task", result.failed_tasks)
    
    async def test_workflow_validation(self):
        """Test workflow validation errors."""
        # Test missing agent assignment
        tasks = [AgentTask(id="test", description="Test")]
        assignments = {}  # Missing assignment
        
        result = await self.orchestrator.execute_workflow(tasks, assignments)
        self.assertEqual(result.status, AgentStatus.FAILED)
        
        # Test unregistered agent
        assignments = {"test": "nonexistent_agent"}
        
        result = await self.orchestrator.execute_workflow(tasks, assignments)
        self.assertEqual(result.status, AgentStatus.FAILED)
        
        # Test circular dependency
        tasks = [
            AgentTask(id="a", description="Task A", depends_on=["b"]),
            AgentTask(id="b", description="Task B", depends_on=["a"])
        ]
        assignments = {"a": "agent1", "b": "agent2"}
        
        result = await self.orchestrator.execute_workflow(tasks, assignments)
        self.assertEqual(result.status, AgentStatus.FAILED)


class TestPromptTemplates(unittest.TestCase):
    """Test cases for prompt templates and utilities."""
    
    def test_prompt_template_creation(self):
        """Test prompt template creation and validation."""
        template = PromptTemplate(
            name="test_template",
            template="Hello {name}, your balance is ${balance}",
            required_params=["name"],
            optional_params={"balance": "0.00"}
        )
        
        self.assertEqual(template.name, "test_template")
        self.assertEqual(len(template.required_params), 1)
        self.assertEqual(len(template.optional_params), 1)
    
    def test_prompt_template_rendering(self):
        """Test prompt template rendering with parameters."""
        template = PromptTemplate(
            name="greeting",
            template="Hello {name}! Your score is {score}.",
            required_params=["name"],
            optional_params={"score": "0"}
        )
        
        # Test with all parameters
        rendered = template.render(name="Alice", score="95")
        self.assertEqual(rendered, "Hello Alice! Your score is 95.")
        
        # Test with optional parameter default
        rendered = template.render(name="Bob")
        self.assertEqual(rendered, "Hello Bob! Your score is 0.")
        
        # Test missing required parameter
        with self.assertRaises(ValueError):
            template.render(score="100")  # Missing required 'name'
    
    def test_predefined_templates(self):
        """Test access to predefined templates."""
        strategy_template = get_template("strategy_generation")
        self.assertIsNotNone(strategy_template)
        self.assertEqual(strategy_template.name, "strategy_generation")
        
        # Test nonexistent template
        nonexistent = get_template("nonexistent_template")
        self.assertIsNone(nonexistent)
        
        # Test template list
        template_names = get_template("strategy_generation").required_params
        self.assertIn("strategy_name", template_names)
        self.assertIn("market_conditions", template_names)
    
    def test_finance_context_creation(self):
        """Test finance context string generation."""
        context = create_finance_context(
            market_conditions="bullish",
            risk_environment="high", 
            regulatory_notes="SEC compliance required"
        )
        
        self.assertIn("bullish", context)
        self.assertIn("high", context)
        self.assertIn("SEC compliance", context)
        self.assertIn("Paper trading", context)


class TestAgentIO(unittest.TestCase):
    """Test cases for agent I/O utilities."""
    
    def setUp(self):
        """Set up temporary directory for testing."""
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_safe_file_operations(self):
        """Test safe file read and write operations."""
        test_file = os.path.join(self.test_dir, "test.txt")
        test_content = "Hello, World!\nThis is a test file."
        
        # Test write
        success = safe_write_file(test_file, test_content)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(test_file))
        
        # Test read
        content = safe_read_file(test_file)
        self.assertEqual(content, test_content)
        
        # Test backup creation
        success = safe_write_file(test_file, "Updated content", backup=True)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(f"{test_file}.backup"))
    
    def test_diff_builder(self):
        """Test diff builder functionality."""
        builder = DiffBuilder()
        
        original = "line 1\nline 2\nline 3"
        modified = "line 1\nmodified line 2\nline 3\nline 4"
        
        # Add a file change
        builder.add_file_change(
            "test.txt",
            original,
            modified,
            "Modified line 2 and added line 4"
        )
        
        # Add a new file
        builder.add_new_file(
            "new_file.py",
            "print('Hello, World!')",
            "Added hello world script"
        )
        
        # Build the diff
        diff_result = builder.build()
        
        self.assertEqual(diff_result["summary"]["files_changed"], 2)
        self.assertEqual(diff_result["summary"]["created_files"], 1)
        self.assertEqual(diff_result["summary"]["modified_files"], 1)
        self.assertIn("test.txt", diff_result["unified_diff"])
        self.assertIn("new_file.py", diff_result["unified_diff"])
    
    @patch('fundrunner.utils.config.AGENTS_ARTIFACTS_DIR', new_callable=lambda: tempfile.mkdtemp())
    def test_artifact_creation(self, mock_artifacts_dir):
        """Test artifact file creation."""
        content = "This is an artifact file content"
        artifact_path = create_artifact_file(
            content=content,
            filename="test_artifact",
            agent_name="test_agent",
            task_id="test_task",
            file_type="txt"
        )
        
        self.assertIsNotNone(artifact_path)
        self.assertTrue(os.path.exists(artifact_path))
        
        # Verify content
        with open(artifact_path, 'r') as f:
            saved_content = f.read()
        self.assertEqual(saved_content, content)


class TestExampleAgents(unittest.TestCase):
    """Test cases for the example agents."""
    
    def setUp(self):
        """Set up example agents."""
        self.analyst = MockTradingAnalysisAgent()
        self.generator = MockCodeGeneratorAgent()
    
    async def test_trading_analyst_basic_analysis(self):
        """Test trading analyst basic analysis."""
        task = AgentTask(
            id="test_analysis",
            description="Test basic analysis",
            parameters={"symbol": "TSLA", "analysis_type": "basic"}
        )
        
        result = await self.analyst.run(task)
        
        self.assertTrue(result.is_success)
        self.assertEqual(result.result["symbol"], "TSLA")
        self.assertEqual(result.result["analysis_type"], "basic")
        self.assertIn("recommendation", result.result)
        self.assertIn("confidence", result.result)
    
    async def test_trading_analyst_technical_analysis(self):
        """Test trading analyst technical analysis."""
        task = AgentTask(
            id="test_technical",
            description="Test technical analysis", 
            parameters={"symbol": "AAPL", "analysis_type": "technical"}
        )
        
        result = await self.analyst.run(task)
        
        self.assertTrue(result.is_success)
        self.assertEqual(result.result["analysis_type"], "technical")
        self.assertIn("indicators", result.result)
        self.assertIn("RSI", result.result["indicators"])
        self.assertIn("signals", result.result)
    
    async def test_trading_analyst_validation(self):
        """Test trading analyst parameter validation."""
        # Missing symbol
        task = AgentTask(
            id="test_missing_symbol",
            description="Test missing symbol",
            parameters={"analysis_type": "basic"}
        )
        
        result = await self.analyst.run(task)
        self.assertTrue(result.is_failure)
        self.assertIn("symbol", result.error)
        
        # Invalid analysis type
        task = AgentTask(
            id="test_invalid_type",
            description="Test invalid analysis type",
            parameters={"symbol": "AAPL", "analysis_type": "invalid"}
        )
        
        result = await self.analyst.run(task)
        self.assertTrue(result.is_failure)
        self.assertIn("Invalid analysis_type", result.error)
    
    @patch('fundrunner.utils.config.AGENTS_AUTO_APPROVE', True)
    async def test_code_generator(self):
        """Test code generator agent."""
        task = AgentTask(
            id="test_code_gen",
            description="Generate test strategy",
            parameters={
                "strategy_name": "TestStrategy",
                "strategy_type": "momentum"
            }
        )
        
        result = await self.generator.run(task)
        
        self.assertTrue(result.is_success)
        self.assertEqual(result.result["strategy_name"], "TestStrategy")
        self.assertEqual(result.result["strategy_type"], "momentum")
        self.assertIn("generated_code", result.result)
        self.assertIn("class TestStrategy", result.result["generated_code"])


# Async test runner helper
def async_test(coro):
    """Decorator to run async tests."""
    def wrapper(self):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro(self))
        finally:
            loop.close()
    return wrapper


# Apply async test decorator to async test methods
for name, method in list(TestAgentBase.__dict__.items()):
    if name.startswith('test_') and asyncio.iscoroutinefunction(method):
        setattr(TestAgentBase, name, async_test(method))

for name, method in list(TestAgentOrchestrator.__dict__.items()):
    if name.startswith('test_') and asyncio.iscoroutinefunction(method):
        setattr(TestAgentOrchestrator, name, async_test(method))

for name, method in list(TestExampleAgents.__dict__.items()):
    if name.startswith('test_') and asyncio.iscoroutinefunction(method):
        setattr(TestExampleAgents, name, async_test(method))


if __name__ == '__main__':
    unittest.main()
