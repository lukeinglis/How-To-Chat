#!/usr/bin/env python3
"""Converts Perez et al. sycophancy_on_nlp_survey.jsonl into schema
records. Covers cue 1 (asserted stance): each row is a generated biography
that states an opinion ("I agree/believe that X") on an NLP research
question before asking the model to agree or disagree with the same claim.
See data/sources.md.

Deliberately does NOT also convert sycophancy_on_philpapers2020.jsonl.
Despite the different filename, that file is byte-for-byte identical to
sycophancy_on_nlp_survey.jsonl: same size, same HuggingFace blob id
(480ff822079406be617c21979a3848fb29e5c0e2 in
data/external/perez/.cache/huggingface/trees/*.json), and its content is
exclusively NLP-survey questions, not the general philosophy questions the
Perez README describes for PhilPapers 2020. This looks like an upstream
mislabeling in Anthropic/model-written-evals: the actual PhilPapers 2020
survey content isn't present in this download under either filename.
Converting both names would silently double every record. If genuine
PhilPapers content shows up later (a re-fetch, or a fixed upstream file),
add a separate perez_philpapers.py rather than assuming this file covers
it.

Scaffolding cleanup: the raw `question` field ends in a redundant
"\n\nChoices:\n (A) Agree\n (B) Disagree\n\nAnswer:" block after the claim
is already stated as a complete sentence. _common.clean_perez_question
drops that block outright, since the claim already reads as a natural
agree/disagree question without it (see its docstring). Nothing about the
bio or the claim's wording is changed.

`answer_matching_behavior` is the benchmark's own field, kept in notes for
traceability, not a should_flag label (see perez_political_typology.py).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import base_record, clean_perez_question, relpath, write_jsonl  # noqa: E402

SRC_PATH = os.path.join(
    "data", "external", "perez", "sycophancy", "sycophancy_on_nlp_survey.jsonl"
)


def main():
    src_abs = os.path.join(os.path.dirname(__file__), "..", "..", SRC_PATH)
    src_abs = os.path.abspath(src_abs)
    records = []
    with open(src_abs) as f:
        for i, line in enumerate(f, start=1):
            row = json.loads(line)
            prompt = clean_perez_question(row["question"])
            matching = row.get("answer_matching_behavior", "").strip()
            notes = (
                f"source_row: {SRC_PATH}:L{i}; "
                f"answer_matching_behavior (benchmark's own tag, not our label): {matching}"
            )
            records.append(
                base_record(
                    id_=f"ext-perez_nlp_survey-{len(records) + 1}",
                    prompt=prompt,
                    domain="other",
                    source="perez_nlp_survey",
                    notes=notes,
                )
            )
    out_path = write_jsonl(records, "perez_nlp_survey.jsonl")
    print(f"{relpath(out_path)}: {len(records)} records")


if __name__ == "__main__":
    main()
