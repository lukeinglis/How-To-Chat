#!/usr/bin/env python3
"""Converts Sharma et al. feedback.jsonl (arguments/solutions/poems) into schema records.
Covers cue 4 (attachment to own work), "I wrote" variant. See data/sources.md.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import base_record, relpath, write_jsonl  # noqa: E402

SRC_PATH = os.path.join(
    "data", "external", "sharma", "datasets", "feedback.jsonl"
)


def template_tag(template):
    if "I really like" in template:
        return "I really like"
    if "I really dislike" in template:
        return "I really dislike"
    if "I did not write" in template:
        return "I did not write"
    if "I wrote" in template:
        return "I wrote"
    return "neutral"


def main():
    src_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_PATH)
    src_abs = os.path.abspath(src_abs)
    records = []
    with open(src_abs) as f:
        for i, line in enumerate(f, start=1):
            row = json.loads(line)
            prompt = row["prompt"][0]["content"]
            template = row["metadata"]["prompt_template"]
            tag = template_tag(template)
            notes = f"source_row: {SRC_PATH}:L{i}; template: {tag}"
            records.append(
                base_record(
                    id_=f"ext-sharma_feedback-{len(records) + 1}",
                    prompt=prompt,
                    domain="other",
                    source="sharma_feedback",
                    notes=notes,
                )
            )
    out_path = write_jsonl(records, "sharma_feedback.jsonl")
    print(f"{relpath(out_path)}: {len(records)} records")


if __name__ == "__main__":
    main()
