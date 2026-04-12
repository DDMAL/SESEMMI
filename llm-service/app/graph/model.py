from langchain_core.language_models import BaseChatModel

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
