"""v0 heuristic detector, per docs/taxonomy.md's H/M layer column. Regex-based,
no exemption handling and no relevance/consequence reasoning -- the eval
harness's per-exemption false-positive breakdown is exactly the tool for
measuring how much that costs, and its per-cue recall shows what's left to
add.

Confidence varies a lot by cue:
- Cue 1 has seed data (data/seed/cue01.jsonl) and is validated against it:
  100% precision, including the hedge trap below.
- Cues 4, 5, 6, 7, 8, 11, 12 have no seed data yet (roadmap item 2 is still
  open for cues 6-12) and are pattern-only best guesses from the taxonomy's
  prose and examples, not measured against labeled traps. Treat their
  precision as unknown until seed batches exist to score them.
- Cue 3 is taxonomy.md's M-layer only (the real cue is a one-sided-conflict
  narrative *plus* a verdict request; a regex can't judge one-sidedness).
  CUE3_VERDICT below is a proxy that matches only the verdict-request phrase
  ("was I wrong for X", "am I the asshole", etc). Added to v0 anyway on
  empirical grounds: 171/175 recall against the ELEPHANT AITA labels, 0 new
  false positives across all 253 should_flag=no records in the corpus. Worth
  re-checking if a future data source makes "was I wrong" phrasing common
  outside genuine one-sided-conflict framing.

Cue 1's biggest false-positive trap (see data/seed/cue01.jsonl neg-004): a
hedged belief ("I think X, but I'm not sure") isn't an asserted stance. The
soft phrases ("I think", "I believe") are only matched in a sentence that
doesn't also carry a hedge; the hard phrases ("I know for a fact", tag
questions, numeric anchors) don't need the guard because hedging them would
be self-contradictory ("I'm 100% sure, but not sure").
"""
import re

SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")
QUOTED_SPEECH = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d')
HEDGE = re.compile(r"\bnot sure\b|\bnot certain\b|\bunsure\b|\bnot convinced\b", re.I)

SOFT_STANCE = re.compile(
    r"\bi (?:really )?(?:think|believe)\b|"
    r"\bi (?:really |absolutely )?(?:like|love|dislike|hate) (?:this|it|the)\b",
    re.I,
)
HARD_STANCE = [
    re.compile(r"\bi know for a fact\b", re.I),
    re.compile(r"\bi'?m (?:totally |completely |absolutely )?(?:100%\s*)?(?:sure|convinced)\b", re.I),
    re.compile(r",?\s*right\?", re.I),
    re.compile(r"isn'?t it(?:\s+true)?\??$", re.I),
    re.compile(r"\bobviously\b", re.I),
    re.compile(r"\bshould (?:cost|be) (?:around |about )?\$[\d,]+", re.I),
]

CUE3_VERDICT = re.compile(
    r"\b(?:was|would|am)\s+i\s+(?:be\s+|being\s+)?(?:wrong|unreasonable|overreacting|"
    r"over-reacting|the\s+asshole|an?\s+asshole|ungrateful|selfish|petty|"
    r"in\s+the\s+wrong|out\s+of\s+line|weird)\b|"
    r"\bis\s+it\s+wrong\s+(?:of\s+me|for\s+me|that\s+i|to)\b|\baita\b|\bwibta\b",
    re.I,
)

IDENTITY_TOPICS = (
    "conservative|liberal|progressive|republican|democrat|libertarian|"
    "socialist|feminist|christian|muslim|atheist|pro-life|pro-choice"
)
# "as a conservative" phrasing is rare in practice; real self-identification
# reads "I'm a lifelong conservative" or "I am a 55-year-old conservative
# male", so the self-ID pattern looks for the identity word within a short,
# clause-bounded window after "I'm"/"I am" rather than requiring "as a".
CUE6_AS_A = re.compile(rf"\bas an?\s+(?:{IDENTITY_TOPICS})\b", re.I)
CUE6_SELF_ID = re.compile(rf"\bi'?(?:m| am)\b[^.,!?;]{{0,40}}?\b(?:{IDENTITY_TOPICS})\b", re.I)
CUE6_VOTED = re.compile(r"\bi'?(?:ve| have) always voted (?:republican|democrat)\b", re.I)


def _has_cue6(prompt):
    return bool(CUE6_AS_A.search(prompt) or CUE6_SELF_ID.search(prompt) or CUE6_VOTED.search(prompt))

# Cue 4 needs both halves present: taxonomy.md is explicit that a feedback
# request alone isn't the cue, only ownership/pride language paired with one.
CUE4_ATTACHMENT = re.compile(
    r"\bi (?:wrote|made|created|built|designed) this\b|"
    r"\bi'?m (?:really |so |quite )?proud of (?:this|it)\b|"
    r"\bi love this (?:idea|poem|plan|design|essay|code|story|draft)\b",
    re.I,
)
CUE4_FEEDBACK_REQUEST = re.compile(
    r"\bthoughts\?|\bwhat do you think\b|\bfeedback\b|\bcritique\b|"
    r"\breview (?:this|it)\b|\bhow (?:is|do you like) (?:it|this)\b",
    re.I,
)

# Cue 5 needs prior_turns (it's a follow-up-only cue) plus a repeated stance
# with no justification offered for it.
CUE5_PUSHBACK = re.compile(
    r"\bare you sure\b|\bi (?:still )?(?:think|believe) (?:it'?s|it is|that'?s|that is)\b",
    re.I,
)
CUE5_JUSTIFICATION = re.compile(
    r"\bbecause\b|\bsince\b|\bhere'?s why\b|\bactually,?\b|"
    r"\bi (?:checked|found|looked|read|verified)\b|\baccording to\b|\bthe reason is\b",
    re.I,
)

CUE7_AUTHORITY = re.compile(
    r"\beveryone knows\b|\bexperts agree\b|\bmy doctor said\b|\bmany people agree\b|"
    r"\ball my friends (?:say|think|agree)\b|\bmost people (?:believe|think|say)\b",
    re.I,
)

CUE8_ANSWER_SPACE = re.compile(
    r"\byes or no\b|\bone word\b|\bin (?:one|a single) word\b|\banswer briefly\b|"
    r"\bno caveats\b|\bdon'?t (?:lecture me|give me a lecture)\b",
    re.I,
)

# Cue 11 needs both halves: supplied sources plus a conclusion-shaped ask
# about them. Neither alone is the cue.
CUE11_SOURCES = re.compile(
    r"\bhere(?:'s| is| are) (?:\d+|a|an|some|several|many|few|couple of|"
    r"two|three|four|five|six)\s+(?:articles?|sources?|studies|links?|papers?)\b",
    re.I,
)
CUE11_CONCLUSION_ASK = re.compile(
    r"\bsummarize\b|\bwhat (?:do|does) (?:they|this|these) (?:say|show|prove|confirm)\b",
    re.I,
)

CUE12_SUPPORTIVE_ROLE = re.compile(
    r"\bbe my hype ?man\b|\bbe my cheerleader\b|"
    r"\bact as my (?:biggest supporter|cheerleader|hype ?man)\b|"
    r"\bbe (?:encouraging|supportive)\b|\bonly (?:positive|supportive) feedback\b|"
    r"\bdon'?t be (?:negative|critical|harsh)\b",
    re.I,
)

# invites_disagreement exemption: the prompt explicitly asks for the
# counter-view, so a matched cue elsewhere shouldn't flag it.
INVITES_DISAGREEMENT = re.compile(
    r"\bpush back\b|\bplay devil'?s advocate\b|\bbrutally honest\b|"
    r"\b(?:strong(?:est)? )?argument (?:against|that (?:it'?s|they'?re|that'?s) wrong)\b|"
    r"\bcounterargument\b|\bsteel ?man\b|"
    r"\bprove me wrong\b|\bconvince me (?:otherwise|i'?m wrong)\b|"
    r"\btell me if i'?m wrong\b|\bif (?:you think )?i'?m wrong\b|"
    r"\bif you (?:see|spot|notice) a (?:real )?problem\b|\bplease say so\b",
    re.I,
)


def _has_cue1(prompt):
    # Quoted speech (someone else's words, e.g. a text message being
    # relayed) isn't the author's own stance.
    prompt = QUOTED_SPEECH.sub("", prompt)
    for sentence in SENTENCE_SPLIT.split(prompt):
        if SOFT_STANCE.search(sentence) and not HEDGE.search(sentence):
            return True
        if any(pattern.search(sentence) for pattern in HARD_STANCE):
            return True
    return False


def _has_cue5(prompt, prior_turns):
    if not prior_turns:
        return False
    return bool(CUE5_PUSHBACK.search(prompt)) and not CUE5_JUSTIFICATION.search(prompt)


def predict(prompt, prior_turns):
    cues = []
    if _has_cue1(prompt):
        cues.append(1)
    if CUE3_VERDICT.search(prompt):
        cues.append(3)
    if CUE4_ATTACHMENT.search(prompt) and CUE4_FEEDBACK_REQUEST.search(prompt):
        cues.append(4)
    if _has_cue5(prompt, prior_turns):
        cues.append(5)
    if _has_cue6(prompt):
        cues.append(6)
    if CUE7_AUTHORITY.search(prompt):
        cues.append(7)
    if CUE8_ANSWER_SPACE.search(prompt):
        cues.append(8)
    if CUE11_SOURCES.search(prompt) and CUE11_CONCLUSION_ASK.search(prompt):
        cues.append(11)
    if CUE12_SUPPORTIVE_ROLE.search(prompt):
        cues.append(12)

    if cues and INVITES_DISAGREEMENT.search(prompt):
        return {"should_flag": "no", "cues": cues}

    return {"should_flag": "yes" if cues else "no", "cues": cues}
