#!/usr/bin/env python3
"""csv_to_yaml.py — convert samples.csv to per-category questions/gold YAML pairs.

Usage:
    python3 eval/text2sparql/csv_to_yaml.py
    python3 eval/text2sparql/csv_to_yaml.py --input path/to/other.csv
    python3 eval/text2sparql/csv_to_yaml.py --output-dir eval/text2sparql/generated

Then run a per-category eval:
    QUESTIONS_FILE=eval/text2sparql/questions_cross_database.yml \\
    GOLD_FILE=eval/text2sparql/gold_cross_database.yml \\
    ./eval/text2sparql/local_eval.sh
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

import yaml


# Force literal block style (|) for multiline strings so SPARQL is readable.
def _str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, _str_representer)


def _normalize_sparql(sparql: str) -> str:
    """Normalize line endings and strip trailing whitespace per line so PyYAML
    can always emit literal block style instead of falling back to quoted style."""
    lines = sparql.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    return "\n".join(line.rstrip() for line in lines).strip()


def parse_args() -> argparse.Namespace:
    here = Path(__file__).parent
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=str(here / "samples_apr13.csv"), help="Path to the input CSV file")
    p.add_argument("--output-dir", default=str(here), help="Directory to write the generated YAML files")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_by_category: dict[str, list[dict]] = defaultdict(list)

    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_by_category[row["category"]].append(row)

    for category, rows in sorted(rows_by_category.items()):
        questions_doc = {
            "dataset": {
                "id": "sesemmi",
                "prefix": f"sesemmi-{category}",
            },
            "questions": [
                {"id": row["id"], "question": {"en": row["nl"]}}
                for row in rows
            ],
        }

        gold_doc = {
            "queries": {row["id"]: _normalize_sparql(row["gold_sparql"]) for row in rows},
        }

        questions_path = output_dir / f"questions_{category}.yml"
        gold_path = output_dir / f"gold_{category}.yml"

        with open(questions_path, "w", encoding="utf-8") as f:
            yaml.dump(questions_doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        with open(gold_path, "w", encoding="utf-8") as f:
            yaml.dump(gold_doc, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        print(f"{category}: {len(rows)} questions -> {questions_path.name} + {gold_path.name}")


if __name__ == "__main__":
    main()
