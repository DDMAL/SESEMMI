import json
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.runnables import Runnable, RunnableLambda

from app.config import settings


def get_chat_model() -> BaseChatModel:
    """Return the configured chat model.

    Uses lazy imports so only the active provider's package needs to be installed.
    Switch providers by setting LLM_PROVIDER and LLM_MODEL in the environment.
    """
    provider = settings.llm_provider
    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.llm_model,
            api_key=settings.anthropic_api_key,
            temperature=0,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.llm_model,
            google_api_key=settings.gemini_api_key,
            temperature=0,
        )
    elif provider == "qwen":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.qwen_base_url,
            temperature=0,
        )
    else:  # ollama (default)
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            num_ctx=settings.ollama_num_ctx,
            num_thread=settings.ollama_num_thread,
            think=settings.ollama_think,
        )


def get_structured_model(schema: Any) -> Runnable:
    """Return a model that emits structured output validated against ``schema``.

    Use this instead of ``get_chat_model().with_structured_output(...)`` so the Qwen/DashScope
    quirks are handled centrally. DashScope's OpenAI-compatible endpoint only supports
    ``response_format=json_object`` (it rejects forced tool_choice, so function-calling is out, and
    it rejects json_object unless the word "json" appears in the messages). In that mode it does
    NOT enforce the schema, so the model drifts on field names. We fix both by prepending a system
    message that contains the literal JSON schema with the exact field names. Other providers,
    which honour strict structured output, are left untouched.
    """
    model = get_chat_model().with_structured_output(schema)
    if settings.llm_provider == "qwen" and hasattr(schema, "model_json_schema"):
        schema_json = json.dumps(schema.model_json_schema())
        hint = SystemMessage(
            content=(
                "Respond with ONLY a single valid JSON object that strictly conforms to this "
                "JSON schema. Use these EXACT field names and include no extra fields:\n"
                f"{schema_json}"
            )
        )
        return RunnableLambda(lambda messages: [hint, *messages]) | model
    return model
