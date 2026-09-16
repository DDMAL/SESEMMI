import os
import socket

import pytest

os.environ.setdefault("LLM_API_KEY", "test-key")
# Disable external services so unit tests never attempt network connections
os.environ["RAG_ENABLED"] = "false"
os.environ["FEW_SHOT_ENABLED"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
# Never inherit a billable provider from the developer's root .env.
os.environ["LLM_PROVIDER"] = "ollama"
os.environ["OLLAMA_BASE_URL"] = "http://127.0.0.1:1"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """A missing mock must fail locally, never reach a model or the live store."""

    def blocked(*args, **kwargs):
        raise RuntimeError("Network access is disabled in unit tests; mock the client.")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
