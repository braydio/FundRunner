"""Example agent demonstrating the FundRunner agent framework.

This is a simple mock trading analysis agent that shows how to implement
the BaseAgent interface and integrate with the framework.
"""

import asyncio
from typing import Dict, Any
from .base import BaseAgent, AgentTask
from .prompts import get_template


class MockTradingAnalysisAgent(BaseAgent):
    """Mock trading analysis agent for demonstration purposes."""
    
    def __init__(self):
        super().__init__(
            name="mock_trading_analyst",
            description="Mock agent that performs basic trading analysis",
            tools=["market_data", "technical_indicators"],
            context_providers=["price_history", "volume_data"],
            require_approval=False
        )
    
    async def _execute(self, task: AgentTask) -> Dict[str, Any]:
        """Execute trading analysis task.
        
        Args:
            task: Task containing analysis parameters
            
        Returns:
            Analysis results
        """
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        # Extract parameters
        symbol = task.parameters.get("symbol", "AAPL")
        analysis_type = task.parameters.get("analysis_type", "basic")
        
        self.logger.info(f"Analyzing {symbol} with {analysis_type} analysis")
        
        # Mock analysis results
        if analysis_type == "sentiment":
            return await self._perform_sentiment_analysis(symbol)
        elif analysis_type == "technical":
            return await self._perform_technical_analysis(symbol)
        else:
            return await self._perform_basic_analysis(symbol)
    
    async def _perform_basic_analysis(self, symbol: str) -> Dict[str, Any]:
        """Perform basic trading analysis."""
        # Simulate LLM call
        prompt = f"Analyze the trading prospects for {symbol}. Provide a brief outlook."
        
        # Mock LLM response instead of real call for testing
        mock_response = f"Analysis for {symbol}: Moderate buy signal based on current market conditions."
        
        return {
            "symbol": symbol,
            "analysis_type": "basic",
            "recommendation": "BUY",
            "confidence": 0.75,
            "reasoning": mock_response,
            "risk_level": "MEDIUM",
            "target_price": 150.00,
            "stop_loss": 140.00,
        }
    
    async def _perform_sentiment_analysis(self, symbol: str) -> Dict[str, Any]:
        """Perform sentiment analysis."""
        return {
            "symbol": symbol,
            "analysis_type": "sentiment",
            "sentiment_score": 0.65,
            "sentiment_label": "POSITIVE",
            "news_count": 15,
            "social_mentions": 1250,
            "overall_mood": "BULLISH",
        }
    
    async def _perform_technical_analysis(self, symbol: str) -> Dict[str, Any]:
        """Perform technical analysis."""
        return {
            "symbol": symbol,
            "analysis_type": "technical",
            "indicators": {
                "RSI": 68.5,
                "MACD": 1.25,
                "BB_position": "UPPER",
                "SMA_20": 145.30,
                "SMA_50": 142.80,
            },
            "signals": ["RSI_OVERBOUGHT", "MACD_BULLISH", "BB_SQUEEZE"],
            "trend": "UPTREND",
            "strength": 0.72,
        }
    
    async def _validate_task(self, task: AgentTask) -> None:
        """Validate trading analysis task parameters."""
        await super()._validate_task(task)
        
        # Check for required symbol parameter
        if "symbol" not in task.parameters:
            raise ValueError("Trading analysis requires 'symbol' parameter")
        
        # Validate analysis type
        valid_types = ["basic", "technical", "sentiment"]
        analysis_type = task.parameters.get("analysis_type", "basic")
        if analysis_type not in valid_types:
            raise ValueError(f"Invalid analysis_type. Must be one of: {valid_types}")


class MockCodeGeneratorAgent(BaseAgent):
    """Mock code generator agent for demonstration purposes."""
    
    def __init__(self):
        super().__init__(
            name="mock_code_generator", 
            description="Mock agent that generates trading strategy code",
            tools=["code_templates", "syntax_checker"],
            context_providers=["existing_strategies", "market_patterns"],
            require_approval=True  # Code generation should require approval
        )
    
    async def _execute(self, task: AgentTask) -> Dict[str, Any]:
        """Execute code generation task.
        
        Args:
            task: Task containing code generation parameters
            
        Returns:
            Generated code and metadata
        """
        await asyncio.sleep(0.2)  # Simulate processing
        
        strategy_name = task.parameters.get("strategy_name", "MockStrategy")
        strategy_type = task.parameters.get("strategy_type", "momentum")
        
        self.logger.info(f"Generating {strategy_type} strategy: {strategy_name}")
        
        # Generate mock strategy code
        code = self._generate_strategy_code(strategy_name, strategy_type)
        
        return {
            "strategy_name": strategy_name,
            "strategy_type": strategy_type,
            "generated_code": code,
            "file_path": f"src/strategies/{strategy_name.lower()}_strategy.py",
            "lines_of_code": len(code.splitlines()),
            "imports_needed": ["numpy", "pandas", "fundrunner.base"],
            "tests_generated": True,
        }
    
    def _generate_strategy_code(self, name: str, strategy_type: str) -> str:
        """Generate mock strategy code."""
        return f'''"""
{name} - A {strategy_type} trading strategy.

Generated by FundRunner Agent Framework.
"""

from fundrunner.strategies.base import BaseStrategy


class {name}(BaseStrategy):
    """A {strategy_type} trading strategy."""
    
    def __init__(self):
        super().__init__(
            name="{name}",
            description="{strategy_type.title()} trading strategy",
            version="1.0.0"
        )
    
    def generate_signals(self, market_data):
        """Generate trading signals based on market data."""
        # {strategy_type.title()} strategy logic here
        signals = []
        
        # Mock signal generation
        for symbol in market_data.symbols:
            signal = {{
                "symbol": symbol,
                "action": "BUY" if market_data.get_momentum(symbol) > 0 else "SELL",
                "confidence": 0.75,
                "timestamp": market_data.current_time
            }}
            signals.append(signal)
        
        return signals
    
    def calculate_position_size(self, signal, portfolio):
        """Calculate appropriate position size."""
        # Kelly criterion or similar logic
        return min(portfolio.buying_power * 0.1, 10000)
'''
    
    async def _validate_task(self, task: AgentTask) -> None:
        """Validate code generation task parameters."""
        await super()._validate_task(task)
        
        # Check strategy name format
        strategy_name = task.parameters.get("strategy_name", "")
        if not strategy_name or not strategy_name.replace("_", "").isalnum():
            raise ValueError("strategy_name must be alphanumeric (underscores allowed)")
        
        # Validate strategy type
        valid_types = ["momentum", "mean_reversion", "breakout", "arbitrage"]
        strategy_type = task.parameters.get("strategy_type", "momentum")
        if strategy_type not in valid_types:
            raise ValueError(f"Invalid strategy_type. Must be one of: {valid_types}")


# Example workflow function
async def run_simple_workflow():
    """Demonstrate a simple two-agent workflow."""
    from .orchestrator import AgentOrchestrator
    
    # Create orchestrator
    orchestrator = AgentOrchestrator(max_concurrent_agents=2)
    
    # Register agents
    analyst = MockTradingAnalysisAgent()
    generator = MockCodeGeneratorAgent()
    
    orchestrator.register_agent(analyst)
    orchestrator.register_agent(generator)
    
    # Create tasks
    tasks = [
        AgentTask(
            id="analyze_AAPL",
            description="Analyze AAPL for trading opportunities",
            parameters={"symbol": "AAPL", "analysis_type": "technical"}
        ),
        AgentTask(
            id="generate_momentum_strategy",
            description="Generate a momentum trading strategy",
            parameters={
                "strategy_name": "AAPL_Momentum",
                "strategy_type": "momentum"
            },
            depends_on=["analyze_AAPL"]  # Wait for analysis
        )
    ]
    
    # Agent assignments
    assignments = {
        "analyze_AAPL": "mock_trading_analyst",
        "generate_momentum_strategy": "mock_code_generator"
    }
    
    # Execute workflow
    result = await orchestrator.execute_workflow(
        tasks=tasks,
        agent_assignments=assignments,
        workflow_id="demo_workflow",
        fail_fast=True
    )
    
    return result
