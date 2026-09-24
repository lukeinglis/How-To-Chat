#!/usr/bin/env python3
"""Converts ELEPHANT AITA-YTA.csv (real r/AmITheAsshole posts, verdict = YTA)
into schema records. Covers cue 3 (one-sided conflict seeking a verdict).

The title carries the verdict request cue 3 needs ("AITA for X" = "was I
wrong to X"), so it isn't dropped: it's rewritten into a natural question
and appended to the end of the post. The original title is kept in notes.
See data/sources.md and CLAUDE.md.
"""
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import base_record, relpath, write_jsonl  # noqa: E402

SRC_PATH = os.path.join(
    "data", "external", "elephant", "datasets", "AITA-YTA.csv"
)

TITLE_RE = re.compile(r"^(AITAH?|WIBTA|Am I [Tt]he [Aa]sshole)\b")
# Title ends at the first sentence boundary or line break, searched within
# a window near the start. Real Reddit titles are short; the window keeps a
# stray mid-body period from swallowing the whole post as "title".
DELIM_RE = re.compile(r"\?|\.\s|\n")
WINDOW = 200

# Title clause -> natural verdict question. Tried in order; first match wins.
CLAUSE_PATTERNS = [
    (re.compile(r"^WIBTA\s+if\s+(?P<x>.+)$", re.IGNORECASE), "Would I be wrong if {x}?"),
    (re.compile(r"^WIBTA\s+for\s+(?P<x>.+)$", re.IGNORECASE), "Would I be wrong to {x}?"),
    (re.compile(r"^AITAH?\s+for\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong to {x}?"),
    (re.compile(r"^AITAH?\s+if\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong if {x}?"),
    (re.compile(r"^Am I [Tt]he [Aa]sshole\s+for\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong to {x}?"),
    (re.compile(r"^Am I [Tt]he [Aa]sshole\s+if\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong if {x}?"),
]


def split_title(raw):
    """Returns (title, body). If no clean split is found, title is None and
    body is the raw text unchanged (nothing is stripped)."""
    if not TITLE_RE.match(raw):
        return None, raw
    region = raw[:WINDOW]
    m = DELIM_RE.search(region)
    if not m:
        return None, raw
    cut = m.end()
    title = raw[:cut].strip()
    body = raw[cut:].strip()
    if not body:
        return None, raw
    return title, body


def rewrite_title(title):
    """Turns a detected title into a natural verdict question. Falls back to
    a generic verdict question when no "for"/"if" clause can be extracted
    (e.g. bare "AITA?" or dash-style titles)."""
    stripped = re.sub(r"[?.]+$", "", title).strip()
    for pattern, template in CLAUSE_PATTERNS:
        m = pattern.match(stripped)
        if m:
            return template.format(x=m.group("x").strip())
    return "Was I wrong here?"


def main():
    src_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_PATH)
    src_abs = os.path.abspath(src_abs)
    records = []
    undetected = 0
    with open(src_abs) as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # header is line 1
            raw = row["prompt"]
            title, body = split_title(raw)
            if title is None:
                undetected += 1
                prompt = raw
                title_note = "(undetected, title not stripped)"
            else:
                question = rewrite_title(title)
                prompt = f"{body}\n\n{question}"
                title_note = title
            notes = f"source_row: {SRC_PATH}:L{i}; title: {title_note}"
            records.append(
                base_record(
                    id_=f"ext-elephant_aita_yta-{len(records) + 1}",
                    prompt=prompt,
                    domain="other",
                    source="elephant_aita_yta",
                    notes=notes,
                )
            )
    out_path = write_jsonl(records, "elephant_aita_yta.jsonl")
    print(
        f"{relpath(out_path)}: {len(records)} records "
        f"({undetected} titles undetected, left unstripped)"
    )


if __name__ == "__main__":
    main()
