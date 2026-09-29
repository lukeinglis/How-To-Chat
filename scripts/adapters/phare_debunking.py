#!/usr/bin/env python3
"""Converts Phare's hallucination/debunking/*.jsonl (false claims about
conspiracy theories, pseudoscience, cryptids, urban legends, etc.) into
schema records. Candidate source for cue 1 (asserted stance) and cue 7
(social proof or authority), per data/sources.md.

Each source file mixes English originals with machine-translated French and
Spanish rows (metadata.translated). Only English, non-translated rows are
converted: translated rows are lower-quality reformulations and CLAUDE.md
asks for prompts a non-technical adult would actually type, which a
machine-translated benchmark sentence isn't. This drops the dataset from
571 rows to 224.

Every English row fits exactly one of a small set of opener/closer
templates the benchmark authors used to vary confidence and framing (see
data/sources.md and the "template:" tag in each record's notes):
  - "Could it be true that X" - questioning frame
  - "Did you know that X?" - asserted as fact
  - "You know, X" - casual assertion
  - "After years long research... i'm now a hundred percent sure: X.
    I hope you're happy about this ground breaking news!" - high-confidence
    assertion, strongest cue 1 candidate
  - "My teacher, who's extremely smart, explained to me that X."
    "My {doctor/friend/...} ..." - authority framing, cue 7 candidate
  - "I just read that X" / "I've read quite a bit, and X" - self-reported
    source, weaker cue 7 candidate
  - "X. {Isn't it interesting / don't you agree / it's crazy right}?" -
    tag-question closer, cue 1 candidate
All 224 English rows match one of these; none fall through to a bare-
assertion fallback, confirmed by a dry run before this file was written.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import base_record, relpath, write_jsonl  # noqa: E402

SRC_GLOB = os.path.join(
    "data", "external", "phare", "hallucination", "debunking", "*.jsonl"
)

TEMPLATE_PATTERNS = [
    (
        re.compile(r"^After years long research and hard work.*?sure:", re.I | re.S),
        "100% sure / breaking news",
    ),
    (re.compile(r"^My teacher,", re.I), "my teacher said (authority)"),
    (
        re.compile(
            r"^My (doctor|friend|mom|dad|professor|dentist|therapist|coworker|neighbor)",
            re.I,
        ),
        "my X said (authority, other)",
    ),
    (re.compile(r"^Could it be true that", re.I), "could it be true (questioning)"),
    (re.compile(r"^Did you know that", re.I), "did you know (asserted fact)"),
    (re.compile(r"^You know,", re.I), "you know (casual assert)"),
    (
        re.compile(r"^I[\u2019']?(ve| have) read (quite a bit|a lot)", re.I),
        "I've read (self-reported source)",
    ),
    (re.compile(r"^I just read that", re.I), "I just read (self-reported source)"),
    (
        re.compile(
            r"(don't you agree|isn't it interesting|it'?s (crazy|fascinating|wild)( right)?)\??\s*$",
            re.I,
        ),
        "tag question ending",
    ),
]


def classify(msg):
    for pattern, tag in TEMPLATE_PATTERNS:
        if pattern.search(msg):
            return tag
    return "bare assertion (no template)"


def main():
    src_glob_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_GLOB)
    src_paths = sorted(glob.glob(src_glob_abs))
    records = []
    skipped_translated = 0
    fallback = 0

    for src_abs in src_paths:
        src_rel = os.path.join(
            "data", "external", "phare", "hallucination", "debunking",
            os.path.basename(src_abs),
        )
        with open(src_abs) as f:
            for i, line in enumerate(f, start=1):
                row = json.loads(line)
                if row.get("language") != "en":
                    skipped_translated += 1
                    continue
                msg = row["generations"][0]["messages"][0]["content"]
                task_name = row["metadata"].get("task_name")
                tag = classify(msg)
                if tag == "bare assertion (no template)":
                    fallback += 1
                notes = f"source_row: {src_rel}:L{i}; task: {task_name}; template: {tag}"
                records.append(
                    base_record(
                        id_=f"ext-phare_debunking-{len(records) + 1}",
                        prompt=msg,
                        domain="other",
                        source="phare_debunking",
                        notes=notes,
                    )
                )

    out_path = write_jsonl(records, "phare_debunking.jsonl")
    print(
        f"{relpath(out_path)}: {len(records)} records "
        f"({skipped_translated} non-English rows skipped, "
        f"{fallback} unclassified by any template)"
    )


if __name__ == "__main__":
    main()
