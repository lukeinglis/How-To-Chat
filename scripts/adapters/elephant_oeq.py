#!/usr/bin/env python3
"""Converts ELEPHANT OEQ.csv (real advice-column/forum posts, mostly not
flag-worthy) into schema records. Best source of realistic negatives.
See data/sources.md.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import base_record, relpath, write_jsonl  # noqa: E402

SRC_PATH = os.path.join("data", "external", "elephant", "datasets", "OEQ.csv")


def main():
    src_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_PATH)
    src_abs = os.path.abspath(src_abs)
    records = []
    with open(src_abs) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header is line 1
            prompt = row["prompt"]
            notes = f"source_row: {SRC_PATH}:L{i}"
            records.append(
                base_record(
                    id_=f"ext-elephant_oeq-{len(records) + 1}",
                    prompt=prompt,
                    domain="other",
                    source="elephant_oeq",
                    notes=notes,
                )
            )
    out_path = write_jsonl(records, "elephant_oeq.jsonl")
    print(f"{relpath(out_path)}: {len(records)} records")


if __name__ == "__main__":
    main()
