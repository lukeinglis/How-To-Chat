"""v0 heuristic detector: cues 1 (asserted stance) and 6 (identity cue on a
contested topic) only, per docs/taxonomy.md. Regex-based, no exemption
handling and no relevance/consequence reasoning -- the eval harness's
per-exemption false-positive breakdown is exactly the tool for measuring how
much that costs, and its per-cue recall shows what's left to add.

Cue 1's biggest false-positive trap (see data/seed/cue01.jsonl neg-004): a
hedged belief ("I think X, but I'm not sure") isn't an asserted stance. The
soft phrases ("I think", "I believe") are only matched in a sentence that
doesn't also carry a hedge; the hard phrases ("I know for a fact", tag
questions, numeric anchors) don't need the guard because hedging them would
be self-contradictory ("I'm 100% sure, but not sure").
"""
import re

SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")
HEDGE = re.compile(r"\bnot sure\b|\bnot certain\b|\bunsure\b|\bnot convinced\b", re.I)

SOFT_STANCE = re.compile(r"\bi (?:really )?(?:think|believe)\b", re.I)
HARD_STANCE = [
    re.compile(r"\bi know for a fact\b", re.I),
    re.compile(r"\bi'?m (?:totally |completely |absolutely )?(?:100%\s*)?(?:sure|convinced)\b", re.I),
    re.compile(r",?\s*right\?", re.I),
    re.compile(r"isn'?t it(?:\s+true)?\??$", re.I),
    re.compile(r"\bobviously\b", re.I),
    re.compile(r"\bshould (?:cost|be) (?:around |about )?\$[\d,]+", re.I),
]

IDENTITY_TOPICS = (
    "conservative|liberal|progressive|republican|democrat|libertarian|"
    "socialist|feminist|christian|muslim|atheist|pro-life|pro-choice"
)
CUE6_IDENTITY = re.compile(rf"\bas an?\s+(?:{IDENTITY_TOPICS})\b", re.I)


def _has_cue1(prompt):
    for sentence in SENTENCE_SPLIT.split(prompt):
        if SOFT_STANCE.search(sentence) and not HEDGE.search(sentence):
            return True
        if any(pattern.search(sentence) for pattern in HARD_STANCE):
            return True
    return False


def predict(prompt, prior_turns):
    cues = []
    if _has_cue1(prompt):
        cues.append(1)
    if CUE6_IDENTITY.search(prompt):
        cues.append(6)

    return {"should_flag": "yes" if cues else "no", "cues": cues}
