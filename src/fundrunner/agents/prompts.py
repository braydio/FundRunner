"""Prompt templates and task recipes for FundRunner agents.

This module provides standardized prompts and templates for various agent tasks
including strategy development, code generation, risk analysis, and review processes.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """A reusable prompt template with parameter substitution."""
    
    name: str
    template: str
    required_params: List[str]
    optional_params: Dict[str, str]  # param_name -> default_value
    description: str = ""
    
    def render(self, **params) -> str:
        """Render the template with provided parameters.
        
        Args:
            **params: Parameters to substitute in the template
            
        Returns:
            Rendered prompt string
            
        Raises:
            ValueError: If required parameters are missing
        """
        # Check required parameters
        missing = [param for param in self.required_params if param not in params]
        if missing:
            raise ValueError(f"Missing required parameters: {missing}")
        
        # Add default values for optional parameters
        render_params = params.copy()
        for param, default in self.optional_params.items():
            if param not in render_params:
                render_params[param] = default
        
        try:
            return self.template.format(**render_params)
        except KeyError as e:
            raise ValueError(f"Template parameter not provided: {e}")


# Trading Strategy Development Templates
STRATEGY_GENERATION_TEMPLATE = PromptTemplate(
    name="strategy_generation",
    description="Generate a new trading strategy based on specifications",
    required_params=["strategy_name", "market_conditions", "risk_tolerance"],
    optional_params={
        "max_drawdown": "10%",
        "expected_return": "15-25% annually", 
        "holding_period": "1-5 days",
        "instruments": "US equities",
    },
    template="""You are an expert quantitative analyst tasked with developing a new trading strategy.

STRATEGY REQUIREMENTS:
- Name: {strategy_name}
- Market Conditions: {market_conditions}
- Risk Tolerance: {risk_tolerance}
- Maximum Drawdown: {max_drawdown}
- Expected Return: {expected_return}
- Typical Holding Period: {holding_period}
- Instruments: {instruments}

TASK: Design a comprehensive trading strategy that includes:

1. STRATEGY LOGIC:
   - Entry conditions and signals
   - Exit conditions (profit taking and stop losses)
   - Position sizing methodology
   - Risk management rules

2. IMPLEMENTATION DETAILS:
   - Key technical indicators or fundamental metrics
   - Data requirements and sources
   - Trading frequency and rebalancing schedule
   - Backtest considerations

3. RISK ANALYSIS:
   - Potential failure modes
   - Market regime sensitivity
   - Correlation with other strategies
   - Stress test scenarios

4. CODE STRUCTURE:
   ```python
   # Provide a high-level code outline showing:
   # - Main strategy class structure
   # - Key methods (generate_signals, calculate_position_size, etc.)
   # - Integration points with existing FundRunner infrastructure
   ```

IMPORTANT: Focus on practical, implementable strategies that can be integrated with the existing FundRunner framework. Consider paper trading safety and simulation modes."""
)

STRATEGY_REVIEW_TEMPLATE = PromptTemplate(
    name="strategy_review",
    description="Review and analyze an existing trading strategy",
    required_params=["strategy_code", "backtest_results"],
    optional_params={
        "review_focus": "comprehensive",
        "risk_appetite": "moderate",
    },
    template="""You are a senior quantitative analyst reviewing a trading strategy for production deployment.

STRATEGY CODE:
```python
{strategy_code}
```

BACKTEST RESULTS:
{backtest_results}

REVIEW FOCUS: {review_focus}
RISK APPETITE: {risk_appetite}

Please provide a comprehensive review covering:

1. CODE QUALITY ASSESSMENT:
   - Logic correctness and robustness
   - Error handling and edge cases
   - Integration with FundRunner framework
   - Code maintainability and documentation

2. RISK ANALYSIS:
   - Position sizing appropriateness
   - Drawdown protection mechanisms
   - Market regime adaptability
   - Correlation and concentration risks

3. BACKTEST VALIDATION:
   - Statistical significance of results
   - Overfitting concerns
   - Out-of-sample performance
   - Walk-forward analysis recommendations

4. PRODUCTION READINESS:
   - Paper trading safety checks
   - Real-time data requirements
   - Latency considerations
   - Monitoring and alerting needs

5. RECOMMENDATIONS:
   - Specific improvements needed
   - Additional risk controls
   - Testing requirements before deployment
   - Performance monitoring metrics

PROVIDE VERDICT: APPROVE / NEEDS_REVISION / REJECT with detailed reasoning."""
)

# Code Generation Templates
FUNCTION_IMPLEMENTATION_TEMPLATE = PromptTemplate(
    name="implement_function",
    description="Implement a specific function based on requirements",
    required_params=["function_name", "requirements", "file_path"],
    optional_params={
        "return_type": "Any",
        "parameters": "",
        "context_code": "",
        "test_requirements": "basic unit tests",
    },
    template="""You are implementing a function for the FundRunner algorithmic trading system.

FUNCTION SPECIFICATION:
- Name: {function_name}
- File: {file_path}
- Requirements: {requirements}
- Parameters: {parameters}
- Return Type: {return_type}
- Tests Needed: {test_requirements}

EXISTING CONTEXT:
{context_code}

IMPLEMENTATION GUIDELINES:
1. Follow existing FundRunner code patterns and architecture
2. Include comprehensive docstrings with type hints
3. Add proper error handling and validation
4. Consider SIMULATION_MODE for trading operations
5. Use existing config and logging infrastructure
6. Maintain backwards compatibility where possible

DELIVERABLES:
1. Complete function implementation with docstring
2. Unit tests covering main functionality and edge cases  
3. Integration notes for existing codebase
4. Any additional dependencies or configuration needed

IMPORTANT: Ensure all trading operations respect paper trading modes and include appropriate safety checks."""
)

MODULE_REFACTOR_TEMPLATE = PromptTemplate(
    name="refactor_module",
    description="Refactor a module to improve code quality while maintaining API compatibility",
    required_params=["module_path", "current_code", "refactor_goals"],
    optional_params={
        "preserve_api": "true",
        "max_complexity": "10",
        "target_coverage": "80%",
    },
    template="""You are refactoring a module in the FundRunner trading system to improve maintainability and performance.

MODULE: {module_path}

CURRENT CODE:
```python
{current_code}
```

REFACTORING GOALS:
{refactor_goals}

CONSTRAINTS:
- Preserve API: {preserve_api}
- Max Cyclomatic Complexity: {max_complexity}
- Target Test Coverage: {target_coverage}

REFACTORING PLAN:
1. ANALYSIS:
   - Identify code smells and complexity issues
   - Map public API surface that must be preserved
   - Identify opportunities for performance improvement

2. IMPROVEMENTS:
   - Extract reusable functions/classes
   - Simplify complex logic flows
   - Add missing error handling
   - Improve type hints and documentation
   - Reduce coupling between components

3. TESTING STRATEGY:
   - Preserve existing test behavior
   - Add tests for edge cases
   - Performance benchmarks where relevant
   - Integration test considerations

4. DELIVERABLES:
   - Refactored module code
   - Updated tests maintaining coverage
   - Migration notes if API changes
   - Performance impact assessment

CRITICAL: Ensure no breaking changes to public APIs and maintain all existing trading safety features."""
)

# Risk Analysis Templates  
RISK_ASSESSMENT_TEMPLATE = PromptTemplate(
    name="risk_assessment",
    description="Perform comprehensive risk analysis on a trading strategy or position",
    required_params=["analysis_target", "portfolio_data", "market_data"],
    optional_params={
        "time_horizon": "1 month",
        "confidence_level": "95%",
        "risk_metrics": "VaR, CVaR, Sharpe, Max Drawdown",
    },
    template="""You are a quantitative risk analyst performing a comprehensive risk assessment for FundRunner.

ANALYSIS TARGET: {analysis_target}
TIME HORIZON: {time_horizon}
CONFIDENCE LEVEL: {confidence_level}
METRICS REQUIRED: {risk_metrics}

PORTFOLIO DATA:
{portfolio_data}

MARKET DATA:
{market_data}

RISK ANALYSIS FRAMEWORK:

1. MARKET RISK ASSESSMENT:
   - Value at Risk (VaR) calculation
   - Conditional VaR (Expected Shortfall)
   - Scenario analysis and stress testing
   - Beta and correlation analysis

2. OPERATIONAL RISK FACTORS:
   - Liquidity risk assessment
   - Model risk considerations
   - Technology and execution risks
   - Counterparty risk (if applicable)

3. PORTFOLIO CONSTRUCTION RISKS:
   - Concentration risk analysis
   - Sector/geographic exposure
   - Style factor loadings
   - Correlation breakdown scenarios

4. DYNAMIC RISK METRICS:
   - Rolling Sharpe ratio analysis
   - Maximum drawdown periods
   - Recovery time estimates
   - Volatility clustering patterns

5. RISK CONTROLS RECOMMENDATIONS:
   - Position sizing guidelines
   - Stop-loss parameters
   - Portfolio rebalancing triggers
   - Emergency exit procedures

OUTPUT FORMAT: JSON structure with numerical risk metrics and qualitative assessments."""
)

# Finance-Specific Checklist Templates
TRADING_SAFETY_CHECKLIST = PromptTemplate(
    name="trading_safety_checklist",
    description="Safety checklist for trading code review",
    required_params=["code_changes"],
    optional_params={
        "environment": "development",
        "criticality": "medium",
    },
    template="""FUNDRUNNER TRADING SAFETY CHECKLIST

CODE CHANGES UNDER REVIEW:
{code_changes}

ENVIRONMENT: {environment}
CRITICALITY: {criticality}

MANDATORY SAFETY CHECKS:

□ 1. SIMULATION MODE COMPLIANCE
   - All trading operations check SIMULATION_MODE flag
   - Paper trading endpoints used when in simulation
   - No live trading possible without explicit override
   - Clear logging of trading mode status

□ 2. POSITION SIZING & RISK CONTROLS
   - Position sizes respect account balance limits
   - Maximum position size caps implemented
   - Stop-loss mechanisms properly configured
   - Kelly criterion or similar sizing methodology

□ 3. MARKET HOURS & TIMING
   - Trading only during appropriate market hours
   - Pre/post-market restrictions observed
   - Rate limiting for API calls implemented
   - Timeout handling for network requests

□ 4. ERROR HANDLING & RECOVERY
   - Graceful handling of API failures
   - Retry logic with exponential backoff
   - Circuit breaker patterns for repeated failures
   - Comprehensive logging of all errors

□ 5. DATA VALIDATION & INTEGRITY
   - Input validation for all trading parameters
   - Price data sanity checks (circuit breakers)
   - Volume and liquidity validation
   - Stale data detection and handling

□ 6. AUDIT TRAIL & MONITORING
   - Complete transaction logging
   - Performance metrics tracking
   - Alert mechanisms for anomalies
   - Rollback procedures documented

ASSESSMENT: PASS / CONDITIONAL_PASS / FAIL
CONDITIONS/BLOCKERS: [List any issues that must be resolved]
RECOMMENDATIONS: [Additional improvements suggested]"""
)

# Prompt utility functions
def get_template(name: str) -> Optional[PromptTemplate]:
    """Get a prompt template by name.
    
    Args:
        name: Name of the template
        
    Returns:
        PromptTemplate instance or None if not found
    """
    templates = {
        "strategy_generation": STRATEGY_GENERATION_TEMPLATE,
        "strategy_review": STRATEGY_REVIEW_TEMPLATE,
        "implement_function": FUNCTION_IMPLEMENTATION_TEMPLATE,
        "refactor_module": MODULE_REFACTOR_TEMPLATE,
        "risk_assessment": RISK_ASSESSMENT_TEMPLATE,
        "trading_safety_checklist": TRADING_SAFETY_CHECKLIST,
    }
    
    return templates.get(name)


def list_templates() -> List[str]:
    """Get list of available template names."""
    return [
        "strategy_generation",
        "strategy_review", 
        "implement_function",
        "refactor_module",
        "risk_assessment",
        "trading_safety_checklist",
    ]


def create_finance_context(
    market_conditions: str = "mixed",
    risk_environment: str = "moderate",
    regulatory_notes: str = "standard compliance"
) -> str:
    """Create a finance-specific context prompt prefix.
    
    Args:
        market_conditions: Current market environment
        risk_environment: Risk assessment of current conditions
        regulatory_notes: Relevant regulatory considerations
        
    Returns:
        Context string to prepend to prompts
    """
    return f"""FINANCIAL CONTEXT:
- Market Conditions: {market_conditions}
- Risk Environment: {risk_environment}  
- Regulatory Notes: {regulatory_notes}
- Trading Mode: Paper trading recommended for development
- Safety Priority: Risk management over profit maximization

"""


# Task recipe builder
def build_strategy_development_workflow() -> List[Dict[str, Any]]:
    """Build a complete strategy development workflow recipe.
    
    Returns:
        List of task specifications for orchestrator
    """
    return [
        {
            "task_id": "research_market_conditions",
            "agent_type": "research",
            "description": "Analyze current market conditions and opportunities",
            "priority": "high",
            "depends_on": [],
            "template": "market_research",
        },
        {
            "task_id": "generate_strategy_spec",
            "agent_type": "strategy_generator", 
            "description": "Generate detailed strategy specification",
            "priority": "high",
            "depends_on": ["research_market_conditions"],
            "template": "strategy_generation",
        },
        {
            "task_id": "implement_strategy_code",
            "agent_type": "code_generator",
            "description": "Implement the strategy in Python code",
            "priority": "normal",
            "depends_on": ["generate_strategy_spec"],
            "template": "implement_function",
        },
        {
            "task_id": "generate_unit_tests",
            "agent_type": "test_generator",
            "description": "Generate comprehensive unit tests",
            "priority": "normal", 
            "depends_on": ["implement_strategy_code"],
            "template": "test_generation",
        },
        {
            "task_id": "run_backtest",
            "agent_type": "backtester",
            "description": "Execute strategy backtest with multiple scenarios",
            "priority": "high",
            "depends_on": ["implement_strategy_code", "generate_unit_tests"],
            "template": "backtest_execution",
        },
        {
            "task_id": "risk_analysis",
            "agent_type": "risk_analyst",
            "description": "Comprehensive risk assessment of strategy",
            "priority": "critical",
            "depends_on": ["run_backtest"],
            "template": "risk_assessment",
        },
        {
            "task_id": "code_review",
            "agent_type": "reviewer",
            "description": "Code review with trading safety checklist",
            "priority": "critical",
            "depends_on": ["implement_strategy_code", "generate_unit_tests"],
            "template": "trading_safety_checklist",
        },
        {
            "task_id": "final_approval",
            "agent_type": "approver",
            "description": "Final human approval for production readiness",
            "priority": "critical",
            "depends_on": ["risk_analysis", "code_review"],
            "template": "production_readiness",
            "require_human_approval": True,
        },
    ]
