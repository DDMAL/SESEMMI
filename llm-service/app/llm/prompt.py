from langchain_core.prompts import ChatPromptTemplate
from app.llm.schema_context import SCHEMA_CONTEXT


def format_examples(examples: list[dict]) -> str:
    if not examples:
        return ""
    pairs = "\n\n".join(
        f"Example {i+1}: \nQuestion: {ex['nl']}\nSPARQL:\n{ex['sparql']}"
        for i, ex in enumerate(examples)
    )
    return f"\n\nHere are some examples of correct queries:\n\n{pairs}\n\n"


def build_prompt_template() -> ChatPromptTemplate:
    template = SCHEMA_CONTEXT.replace("<<USER_INPUT>>", "{{ query }}{{ examples }}")
    return ChatPromptTemplate.from_messages(
        [("human", template)], template_format="jinja2"
    )
