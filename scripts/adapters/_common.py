"""Shared helpers for source adapters. Eval-only data: see data/sources.md."""
import json
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONVERTED_DIR = os.path.join(REPO_ROOT, "data", "external", "converted")


def relpath(path):
    return os.path.relpath(path, REPO_ROOT)


def base_record(id_, prompt, domain, source, notes):
    return {
        "id": id_,
        "prompt": prompt,
        "prior_turns": [],
        "should_flag": "borderline",
        "cues": [],
        "exemption": None,
        "near_miss_of": None,
        "pair": None,
        "domain": domain,
        "source": source,
        "review": "pending",
        "notes": notes,
    }


def write_jsonl(records, out_name):
    os.makedirs(CONVERTED_DIR, exist_ok=True)
    out_path = os.path.join(CONVERTED_DIR, out_name)
    with open(out_path, "w") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out_path
