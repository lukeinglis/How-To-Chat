#!/usr/bin/env python3
"""Converts Perez et al. sycophancy_on_political_typology_quiz.jsonl into
schema records. Covers cue 6 (identity cue on a contested topic): each row
is a generated biography that discloses a political identity (liberal or
conservative) before asking one of 10 Pew Research political-typology-quiz
questions. See data/sources.md.

The raw `question` field ends in completion-API scaffolding ("\n\nAnswer:")
and, for most rows, an inline two-choice list on separate lines. Neither is
something a real person would type, so both are cleaned up by
_common.clean_perez_question before the prompt is written: the trailing
"Answer:" cue is dropped, and "\n (A) X\n (B) Y" becomes a single inline
question ending in " (A) X, or (B) Y?". Nothing about the bio or the
question's content is changed.

`user_affiliation` (liberal/conservative) and `answer_matching_behavior`
are the benchmark's own fields, kept in notes for traceability. They are
not a should_flag label: per data/sources.md, none of these datasets label
prompts, only model responses, so answering to the field's plain "Answer:"
choice says nothing about whether the identity disclosure biases the
answer here.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import base_record, clean_perez_question, relpath, write_jsonl  # noqa: E402

SRC_PATH = os.path.join(
    "data", "external", "perez", "sycophancy", "sycophancy_on_political_typology_quiz.jsonl"
)


def main():
    src_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_PATH)
    src_abs = os.path.abspath(src_abs)
    records = []
    with open(src_abs) as f:
        for i, line in enumerate(f, start=1):
            row = json.loads(line)
            prompt = clean_perez_question(row["question"])
            affiliation = row.get("user_affiliation")
            matching = row.get("answer_matching_behavior", "").strip()
            notes = (
                f"source_row: {SRC_PATH}:L{i}; user_affiliation: {affiliation}; "
                f"answer_matching_behavior (benchmark's own tag, not our label): {matching}"
            )
            records.append(
                base_record(
                    id_=f"ext-perez_political_typology-{len(records) + 1}",
                    prompt=prompt,
                    domain="other",
                    source="perez_political_typology",
                    notes=notes,
                )
            )
    out_path = write_jsonl(records, "perez_political_typology.jsonl")
    print(f"{relpath(out_path)}: {len(records)} records")


if __name__ == "__main__":
    main()
