"""
Read more-few-shots.csv and append new examples to FEW_SHOT_EXAMPLES in examples.py.
Run from the repo root: python scripts/add_few_shots.py
"""
import ast
import csv
import sys
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "more-few-shots.csv"
EXAMPLES_PATH = Path(__file__).parent.parent / "llm-service/app/graph/examples.py"


def load_existing_nls(source: str) -> set[str]:
    tree = ast.parse(source)
    nls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value == "nl":
                    if isinstance(value, ast.Constant):
                        nls.add(value.value.strip())
    return nls


def format_example(nl: str, sparql: str) -> str:
    escaped = sparql.replace('"""', r'\"\"\"')
    return f'    {{\n        "nl": {nl!r},\n        "sparql": """{escaped}""",\n    }}'


def main() -> None:
    source = EXAMPLES_PATH.read_text()
    existing_nls = load_existing_nls(source)

    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    new_examples = []
    for row in rows:
        nl = row["nl"].strip()
        sparql = row["gold_sparql"].strip()
        if not nl or not sparql:
            continue
        if nl in existing_nls:
            print(f"  skip (duplicate): {nl[:60]}")
            continue
        new_examples.append((nl, sparql))
        existing_nls.add(nl)

    if not new_examples:
        print("No new examples to add.")
        return

    insertion_point = source.rfind("]")
    if insertion_point == -1:
        print("ERROR: could not find closing ] in examples.py", file=sys.stderr)
        sys.exit(1)

    additions = ",\n".join(format_example(nl, sparql) for nl, sparql in new_examples)
    new_source = source[:insertion_point] + additions + ",\n" + source[insertion_point:]
    EXAMPLES_PATH.write_text(new_source)
    print(f"Added {len(new_examples)} example(s) to {EXAMPLES_PATH}")


if __name__ == "__main__":
    main()