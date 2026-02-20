from ai import agent as agent_module
from ai import apis as ai_apis


def test_agent_preserves_sensitive_text(monkeypatch):
    class DummyClient:
        def __init__(self, message=None, model=None, user_id=None, **kwargs):
            pass

        def ask_llm(self, message=None, chat_history=None, max_steps=8):
            history = [
                {
                    "role": "USER",
                    "message": "email me at test@example.com or 555-555-1234",
                }
            ]
            return "Contact test@example.com", history

    monkeypatch.setattr(agent_module, "CohereClient", DummyClient)
    agent_module.SESSION_MEMORY.clear()

    agent = agent_module.PolicyAgent("hello", session_id="s1")
    result = agent.run()
    assert "test@example.com" in result["response"]
    assert "555-555-1234" in result["messages"][0]["message"]


def test_agent_trims_history(monkeypatch):
    class DummyClient:
        def __init__(self, message=None, model=None, user_id=None, **kwargs):
            pass

        def ask_llm(self, message=None, chat_history=None, max_steps=8):
            history = [
                {"role": "USER", "message": f"msg {idx}"}
                for idx in range(agent_module.MAX_HISTORY + 5)
            ]
            return "ok", history

    monkeypatch.setattr(agent_module, "CohereClient", DummyClient)
    agent_module.SESSION_MEMORY.clear()

    agent = agent_module.PolicyAgent("hello", session_id="s2")
    result = agent.run()
    assert len(result["messages"]) == agent_module.MAX_HISTORY + 5
    assert len(agent_module.SESSION_MEMORY["s2"]) == agent_module.MAX_HISTORY


def test_ai_assistant_endpoint_uses_agent(
    client, monkeypatch, create_user, auth_headers
):
    class DummyAgent:
        def __init__(self, question, session_id=None, user_id=None):
            self.question = question
            self.session_id = session_id

        def run(self):
            return {
                "response": "ok",
                "session_id": self.session_id,
                "messages": [{"role": "CHATBOT", "message": "ok"}],
            }

    monkeypatch.setattr(ai_apis, "PolicyAgent", DummyAgent)
    user = create_user(username="ai-user", email="ai-user@example.com")
    response = client.post(
        "/ai_assistant",
        json={"question": "Hello"},
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["response"] == "ok"
    assert payload["messages"][0]["message"] == "ok"


def test_policy_agent_passes_user_id_to_cohere_client(monkeypatch):
    captured = {}

    class FakeCohereClient:
        def __init__(self, message=None, model=None, user_id=None):
            captured["user_id"] = user_id

        def ask_llm(self, message=None, chat_history=None, max_steps=8):
            return "ok", []

    monkeypatch.setattr(agent_module, "CohereClient", FakeCohereClient)
    agent_module.SESSION_MEMORY.clear()

    agent_module.PolicyAgent("hello", session_id="s1", user_id="user-123").run()
    assert captured.get("user_id") == "user-123"


def test_policy_agent_accepts_none_user_id(monkeypatch):
    captured = {}

    class FakeCohereClient:
        def __init__(self, message=None, model=None, user_id=None):
            captured["user_id"] = user_id

        def ask_llm(self, message=None, chat_history=None, max_steps=8):
            return "ok", []

    monkeypatch.setattr(agent_module, "CohereClient", FakeCohereClient)
    agent_module.SESSION_MEMORY.clear()

    agent_module.PolicyAgent("hello", session_id="s2").run()
    assert captured.get("user_id") is None


def test_ai_assistant_passes_user_id_to_agent(
    client, monkeypatch, create_user, auth_headers
):
    captured = {}

    class SpyAgent:
        def __init__(self, question, session_id=None, user_id=None):
            captured["user_id"] = user_id
            captured["question"] = question

        def run(self):
            return {
                "response": "ok",
                "session_id": None,
                "messages": [],
            }

    monkeypatch.setattr(ai_apis, "PolicyAgent", SpyAgent)
    user = create_user(username="spy-user", email="spy@example.com")
    response = client.post(
        "/ai_assistant",
        json={"question": "What is my organization?"},
        headers=auth_headers(user),
    )
    assert response.status_code == 200
    assert captured.get("user_id") == str(user.id)
    assert captured.get("question") == "What is my organization?"


def test_get_my_pending_leaves_tool_registered_for_authenticated_user():
    from ai.tools import AI_TOOLS, get_ai_function_map

    tool_names = [t["name"] for t in AI_TOOLS]
    assert "get_my_pending_leaves" in tool_names

    fn_map = get_ai_function_map(user_id="test-uuid")
    assert "get_my_pending_leaves" in fn_map


def test_get_my_pending_leaves_tool_excluded_when_user_id_none():
    from ai.clients import CohereClient

    client = CohereClient(user_id=None)
    tool_names = [t["name"] for t in client.tools]
    assert "get_my_pending_leaves" not in tool_names


def test_get_my_pending_leaves_returns_approved_and_policy(
    app,
    create_user,
    create_organization,
    create_user_organization,
    create_leave_request,
    monkeypatch,
):
    from unittest.mock import MagicMock

    from users.choices import LeaveType

    from ai import tools as ai_tools

    # Mock RAGClient so we don't hit Cohere/pgvector in tests
    mock_rag = MagicMock()
    mock_rag.query_policy_index.return_value = []
    monkeypatch.setattr(ai_tools, "RAGClient", lambda: mock_rag)

    user = create_user(username="pending-user", email="pending@example.com")
    org = create_organization(name="Pending Org")
    create_user_organization(user_id=user.id, organization_id=org.id)
    create_leave_request(
        user_id=user.id, organization_id=org.id, is_accepted=True, leave_type=LeaveType.SICK_LEAVE
    )

    fn_map = ai_tools.get_ai_function_map(user_id=str(user.id))
    result = fn_map["get_my_pending_leaves"]()

    assert "approved_leaves" in result
    assert "total_approved_days" in result
    assert "policy_excerpts" in result
    assert result["total_approved_days"] == 1
    assert len(result["approved_leaves"]) == 1


def test_policy_prompt_format_no_key_error():
    """Ensure POLICY_PROMPT.format() does not raise KeyError (e.g. 'os')."""
    from ai.prompts import POLICY_PROMPT

    # Verify template uses safe placeholders
    prompt = POLICY_PROMPT.format(excerpts_text="Sample excerpt", question="How many days?")
    assert "Sample excerpt" in prompt
    assert "How many days?" in prompt
