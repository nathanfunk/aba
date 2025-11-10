"""Core implementation for the Agent Building Agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Iterable

from .language_model import LanguageModel
from .planning import AgentPlan, CapabilitySuggestion, FileArtifact


@dataclass
class AgentBuilderAgent:
    """An assistant that transforms free-form briefs into agent scaffolds."""

    language_model: LanguageModel

    def plan(self, specification: str) -> AgentPlan:
        """Analyze the specification and produce a structured plan."""

        normalized = specification.strip()
        name = self._infer_name(normalized)
        summary = self._summarize(normalized)
        capabilities = self._infer_capabilities(normalized)
        tools = self._infer_tools(capabilities, normalized)
        memory_strategy = self._infer_memory(normalized)
        conversation = self._conversation_starters(normalized, name)

        plan = AgentPlan(
            name=name,
            summary=summary,
            capabilities=capabilities,
            recommended_tools=tools,
            memory_strategy=memory_strategy,
            conversation_starters=conversation,
        )

        return plan

    def generate_file_artifacts(self, plan: AgentPlan) -> list[FileArtifact]:
        """Create the files required to bootstrap the agent described in ``plan``."""

        slug = self._slugify(plan.name)
        files: list[FileArtifact] = []

        agent_class_name = "".join(part.capitalize() for part in slug.split("-")) or "Agent"
        core_module = dedent(
            f'''"""Core runtime for the {plan.name} agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass
class Task:
    """Represents a unit of work handled by the agent."""

    goal: str
    context: dict[str, Any]


class {agent_class_name}Agent:
    """High-level orchestration for the agent."""

    def __init__(self, tools: Iterable[Any], memory: Any | None = None) -> None:
        self.tools = list(tools)
        self.memory = memory

    def run(self, task: Task) -> str:
        """Run the agent for ``task`` and return a reasoning transcript."""

        transcript = [f"Goal: {{task.goal}}"]
        if task.context:
            context_keys = ", ".join(sorted(task.context))
            transcript.append(f"Context keys detected: {{context_keys}}")
        else:
            transcript.append("No structured context supplied.")
        if self.memory is not None:
            transcript.append("Memory state loaded.")
        for tool in self.tools:
            transcript.append(f"Prepared tool: {{tool.__class__.__name__}}")
        transcript.append("Begin reasoning loop...")
        transcript.append("1. Understand the problem context.")
        transcript.append("2. Select relevant tools.")
        transcript.append("3. Produce an actionable result.")
        return "\\n".join(transcript)
'''
        )

        files.append(
            FileArtifact(
                path=f"agents/{slug}/core.py",
                description="Agent runtime entry point",
                content=core_module,
            )
        )

        tools_section = "\n".join(
            f"- {tool}" for tool in (plan.recommended_tools or ["Tool selection TBD"])
        )
        conversation_section = "\n".join(
            f"- {line}" for line in (
                plan.conversation_starters or ["How can I assist you today?"]
            )
        )
        readme = dedent(
            f"""# {plan.name} Agent

{plan.summary}

## Capabilities

{plan.capability_table()}

## Recommended tools

{tools_section}

## Memory strategy

{plan.memory_strategy or "Memory approach to be decided."}

## Conversation starters

{conversation_section}
"""
        )

        files.append(
            FileArtifact(
                path=f"agents/{slug}/README.md",
                description="Documentation for the generated agent",
                content=readme,
            )
        )

        return files

    def materialize(self, specification: str, output_dir: str | Path) -> AgentPlan:
        """Create files on disk for the target agent and return the plan used."""

        plan = self.plan(specification)
        artifacts = self.generate_file_artifacts(plan)

        base_path = Path(output_dir)
        for artifact in artifacts:
            target = base_path / artifact.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(artifact.content)

        return plan

    # --- heuristics -----------------------------------------------------
    def _infer_name(self, specification: str) -> str:
        for line in specification.splitlines():
            if ":" in line:
                key, value = [part.strip() for part in line.split(":", 1)]
                if key.lower() in {"agent", "agent name", "name"} and value:
                    return value
        first_line = specification.splitlines()[0]
        words = first_line.split()
        return " ".join(word.capitalize() for word in words[:3]) or "New Agent"

    def _summarize(self, specification: str) -> str:
        first_sentence = specification.split(".")[0].strip()
        if len(first_sentence) > 20:
            return first_sentence + "."
        response = self.language_model.complete(
            "Provide a short summary for an agent specification." + specification
        )
        return response.strip() or "Agent summary unavailable."

    def _infer_capabilities(self, specification: str) -> list[CapabilitySuggestion]:
        keywords = {
            "research": "Performs multi-step research across the web.",
            "summarize": "Summarises long-form documents into concise insights.",
            "code": "Generates and reviews source code snippets.",
            "test": "Creates regression tests to validate behaviour.",
            "plan": "Breaks big objectives into small, ordered tasks.",
            "data": "Cleans and analyses structured datasets.",
            "deploy": "Prepares deployment scripts and infrastructure notes.",
            "monitor": "Observes systems and raises alerts on anomalies.",
        }

        priorities = ["high", "medium", "low"]
        capabilities: list[CapabilitySuggestion] = []
        lowered = specification.lower()
        for keyword, description in keywords.items():
            if keyword in lowered:
                rationale = f"Keyword '{keyword}' detected in specification."
                priority = priorities[len(capabilities) % len(priorities)]
                capabilities.append(
                    CapabilitySuggestion(
                        name=keyword.capitalize(),
                        description=description,
                        rationale=rationale,
                        priority=priority,
                    )
                )

        if not capabilities:
            capabilities.append(
                CapabilitySuggestion(
                    name="General Assistance",
                    description="Provides broad problem-solving support.",
                    rationale="No specific keywords were detected; fallback to generalist mode.",
                    priority="medium",
                )
            )

        return capabilities

    def _infer_tools(
        self, capabilities: Iterable[CapabilitySuggestion], specification: str
    ) -> list[str]:
        suggestions: list[str] = []
        lowered = specification.lower()
        if any(cap.name.lower() == "research" for cap in capabilities) or "web" in lowered:
            suggestions.append("httpx for async HTTP calls")
            suggestions.append("BeautifulSoup for HTML parsing")
        if any(cap.name.lower() == "code" for cap in capabilities):
            suggestions.append("ruff for linting and static analysis")
            suggestions.append("pytest for unit testing")
        if "data" in lowered:
            suggestions.append("pandas for data wrangling")
        if "knowledge" in lowered or "memory" in lowered:
            suggestions.append("SQLite for structured long-term memory")

        if not suggestions:
            lm_response = self.language_model.complete(
                "Suggest essential tools for an automation agent." + specification
            )
            suggestions.extend(part.strip() for part in lm_response.split(".") if part.strip())

        return suggestions or ["Tooling to be refined with stakeholders"]

    def _infer_memory(self, specification: str) -> str | None:
        lowered = specification.lower()
        if "long-term" in lowered or "history" in lowered:
            return "Vector store memory for semantic recall of conversations."
        if "lightweight" in lowered or "privacy" in lowered:
            return "Ephemeral in-memory storage with periodic redaction."
        response = self.language_model.complete(
            "Propose a memory strategy for the agent." + specification
        )
        return response.strip() or None

    def _conversation_starters(self, specification: str, name: str) -> list[str]:
        lowered = specification.lower()
        starters: list[str] = [
            f"Hello! I'm {name}. What automation work should we tackle today?",
        ]
        if "research" in lowered:
            starters.append("Which topic would you like me to investigate first?")
        if "code" in lowered:
            starters.append("Do you have a repository or snippet I should review?")
        if "data" in lowered:
            starters.append("Can you describe the dataset and desired insights?")
        if len(starters) == 1:
            starters.append("What goals should I prioritize in this session?")
        return starters

    def _slugify(self, name: str) -> str:
        return "-".join(
            "".join(ch.lower() for ch in part if ch.isalnum())
            for part in name.split()
            if part
        ) or "agent"
