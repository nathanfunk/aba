from aba.chat import AgentChatSession
from aba.language_model import RuleBasedLanguageModel
from aba.planning import AgentPlan, CapabilitySuggestion


def make_plan() -> AgentPlan:
    return AgentPlan(
        name="Research Buddy",
        summary="Turns vague research prompts into actionable plans.",
        capabilities=[
            CapabilitySuggestion(
                name="Research",
                description="Performs multi-step research across the web.",
                rationale="keyword hit",
                priority="high",
            )
        ],
        recommended_tools=["httpx client", "json parser"],
        conversation_starters=["What topic do you need help researching?"],
    )


def test_chat_session_mentions_capabilities():
    session = AgentChatSession(plan=make_plan(), language_model=RuleBasedLanguageModel())

    reply = session.respond("Can you tackle research questions for me?")

    assert "Research Buddy" in reply
    assert "Relevant capabilities:" in reply
    assert "Research: Performs multi-step research across the web." in reply
    assert "Suggested tools: httpx client, json parser" in reply


def test_chat_session_tracks_history():
    session = AgentChatSession(plan=make_plan(), language_model=RuleBasedLanguageModel())

    reply_one = session.respond("hello")
    reply_two = session.respond("and again")

    assert reply_one != reply_two
    # Ensure history logged agent turns as well
    assert session.history[0] == ("user", "hello")
    assert session.history[1][0] == "agent"
