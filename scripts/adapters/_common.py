"""Shared helpers for source adapters. Eval-only data: see data/sources.md."""
import json
import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONVERTED_DIR = os.path.join(REPO_ROOT, "data", "external", "converted")

# Shared AITA title handling for ELEPHANT AITA-derived sources. Real Reddit
# posts start with "AITA for X" / "WIBTA if X"; the title carries the cue 3
# verdict request, so it's rewritten into a natural question and appended to
# the end of the post rather than stripped. See
# scripts/adapters/elephant_aita_yta.py and data/sources.md.
AITA_TITLE_RE = re.compile(r"^(AITAH?|WIBTA|Am I [Tt]he [Aa]sshole)\b")
# Title ends at the first sentence boundary or line break, searched within a
# window near the start. Real Reddit titles are short; the window keeps a
# stray mid-body period from swallowing the whole post as "title".
AITA_DELIM_RE = re.compile(r"\?|\.\s|\n")
AITA_TITLE_WINDOW = 200

# Title clause -> natural verdict question. Tried in order; first match wins.
AITA_CLAUSE_PATTERNS = [
    (re.compile(r"^WIBTA\s+if\s+(?P<x>.+)$", re.IGNORECASE), "Would I be wrong if {x}?"),
    (re.compile(r"^WIBTA\s+for\s+(?P<x>.+)$", re.IGNORECASE), "Would I be wrong for {x}?"),
    (re.compile(r"^AITAH?\s+for\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong for {x}?"),
    (re.compile(r"^AITAH?\s+if\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong if {x}?"),
    (re.compile(r"^Am I [Tt]he [Aa]sshole\s+for\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong for {x}?"),
    (re.compile(r"^Am I [Tt]he [Aa]sshole\s+if\s+(?P<x>.+)$", re.IGNORECASE), "Was I wrong if {x}?"),
]


def split_aita_title(raw):
    """Returns (title, body). If no clean split is found, title is None and
    body is the raw text unchanged (nothing is stripped)."""
    if not AITA_TITLE_RE.match(raw):
        return None, raw
    region = raw[:AITA_TITLE_WINDOW]
    m = AITA_DELIM_RE.search(region)
    if not m:
        return None, raw
    cut = m.end()
    title = raw[:cut].strip()
    body = raw[cut:].strip()
    if not body:
        return None, raw
    return title, body


def rewrite_aita_title(title):
    """Turns a detected title into a natural verdict question. Falls back to
    a generic verdict question when no "for"/"if" clause can be extracted
    (e.g. bare "AITA?" or dash-style titles)."""
    stripped = re.sub(r"[?.]+$", "", title).strip()
    for pattern, template in AITA_CLAUSE_PATTERNS:
        m = pattern.match(stripped)
        if m:
            return template.format(x=m.group("x").strip())
    return "Was I wrong here?"


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
