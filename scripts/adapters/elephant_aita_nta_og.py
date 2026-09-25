#!/usr/bin/env python3
"""Converts ELEPHANT AITA-NTA-OG.csv (real r/AmITheAsshole posts, verdict =
NTA) into schema records. Covers cue 3 (one-sided conflict seeking a
verdict), paired with elephant_aita_yta.py so cue-3 sampling isn't confined
to posts with a known-bad-outcome verdict. See data/sources.md and
CLAUDE.md.

Same title handling as elephant_aita_yta.py (shared via _common.py): the
"AITA for X" / "WIBTA if X" title carries the cue 3 verdict request, so it's
rewritten into a natural question and appended to the end of the post
rather than stripped. The original title is kept in notes.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import (  # noqa: E402
    base_record,
    relpath,
    rewrite_aita_title,
    split_aita_title,
    write_jsonl,
)

SRC_PATH = os.path.join(
    "data", "external", "elephant", "datasets", "AITA-NTA-OG.csv"
)


def main():
    src_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_PATH)
    src_abs = os.path.abspath(src_abs)
    records = []
    undetected = 0
    with open(src_abs) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header is line 1
            raw = row["original_post"]
            title, body = split_aita_title(raw)
            if title is None:
                undetected += 1
                prompt = raw
                title_note = "(undetected, title not stripped)"
            else:
                question = rewrite_aita_title(title)
                prompt = f"{body}\n\n{question}"
                title_note = title
            notes = f"source_row: {SRC_PATH}:L{i}; title: {title_note}"
            records.append(
                base_record(
                    id_=f"ext-elephant_aita_nta_og-{len(records) + 1}",
                    prompt=prompt,
                    domain="other",
                    source="elephant_aita_nta_og",
                    notes=notes,
                )
            )
    out_path = write_jsonl(records, "elephant_aita_nta_og.jsonl")
    print(
        f"{relpath(out_path)}: {len(records)} records "
        f"({undetected} titles undetected, left unstripped)"
    )


if __name__ == "__main__":
    main()
