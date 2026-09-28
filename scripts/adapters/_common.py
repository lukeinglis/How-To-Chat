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


# Shared Perez et al. (Anthropic model-written-evals) benchmark-scaffold
# stripping. Their "question" field is a bio-plus-claim message followed by
# multiple-choice scaffolding meant for a completion API ("\n\nChoices:\n
# (A) ...\n (B) ...\n\nAnswer:"), not something a real person would type.
# See scripts/adapters/perez_political_typology.py and
# scripts/adapters/perez_nlp_survey.py.
PEREZ_ANSWER_SUFFIX_RE = re.compile(r"\n\nAnswer:\s*$")
PEREZ_CHOICES_BLOCK_RE = re.compile(r"\n\nChoices:\n")
PEREZ_CHOICE_A_RE = re.compile(r"\n\s*\(A\)\s*")
PEREZ_CHOICE_B_RE = re.compile(r"\n\s*\(B\)\s*")


def clean_perez_question(question):
    """Strips completion-API scaffolding from a Perez `question` field.

    Two shapes appear in the data:
    1. The claim is already a complete declarative sentence, followed by a
       redundant "\n\nChoices:\n (A) Agree\n (B) Disagree\n\nAnswer:" block
       (philpapers/nlp_survey). That block is dropped outright: the claim
       already reads as a natural agree/disagree question without it.
    2. The two options ARE the payload, given inline as "\n (A) X\n (B) Y"
       with no preceding claim sentence (political_typology_quiz). Those are
       collapsed into a single natural question: " (A) X, or (B) Y?"
    In both cases the trailing "\n\nAnswer:" prompt-completion cue is
    stripped first.
    """
    text = PEREZ_ANSWER_SUFFIX_RE.sub("", question)
    choices_block = PEREZ_CHOICES_BLOCK_RE.search(text)
    if choices_block:
        return text[: choices_block.start()].strip()
    text = PEREZ_CHOICE_A_RE.sub(" (A) ", text)
    text = PEREZ_CHOICE_B_RE.sub(", or (B) ", text)
    text = text.rstrip()
    if not text.endswith("?"):
        text += "?"
    return text


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
