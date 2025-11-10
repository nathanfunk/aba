from __future__ import annotations

from aba.agent_builder import AgentBuilderAgent
from aba.language_model import RuleBasedLanguageModel


SPEC = """Agent Name: Research Navigator
The agent should research, summarize findings, and propose implementation steps.
It must reason about codebases and prepare tests for critical components.
"""


def test_plan_infers_capabilities_and_tools(tmp_path):
    agent = AgentBuilderAgent(language_model=RuleBasedLanguageModel())
    plan = agent.plan(SPEC)

    capability_names = {cap.name for cap in plan.capabilities}
    assert {"Research", "Summarize", "Code", "Test"}.issubset(capability_names)

    joined_tools = "\n".join(plan.recommended_tools)
    assert "httpx" in joined_tools
    assert "pytest" in joined_tools

    output_dir = tmp_path / "agent"
    agent.materialize(SPEC, output_dir)
    core_path = output_dir / "agents" / "research-navigator" / "core.py"
    assert core_path.exists()

    generated = core_path.read_text()
    assert "class ResearchNavigatorAgent" in generated
    assert "Goal: {task.goal}" in generated
