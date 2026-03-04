from app.llm.prompt import build_prompt_template, format_examples


def test_build_prompt_template_has_input_variables():
    prompt = build_prompt_template()
    assert "query" in prompt.input_variables
    assert "examples" in prompt.input_variables


def test_format_examples_empty():
    assert format_examples([]) == ""


def test_format_examples_single():
    examples = [{"nl": "Find all songs", "sparql": "SELECT ?s WHERE { }"}]
    result = format_examples(examples)
    assert "Example 1" in result
    assert "Find all songs" in result
    assert "SELECT ?s WHERE" in result


def test_format_examples_numbering():
    examples = [
        {"nl": "Query 1", "sparql": "SELECT ?a WHERE { }"},
        {"nl": "Query 2", "sparql": "SELECT ?b WHERE { }"},
    ]
    result = format_examples(examples)
    assert "Example 1" in result
    assert "Example 2" in result
