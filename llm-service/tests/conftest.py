import os

os.environ.setdefault("LLM_API_KEY", "test-key")
# Disable external services so unit tests never attempt network connections
os.environ["RAG_ENABLED"] = "false"
os.environ["FEW_SHOT_ENABLED"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
