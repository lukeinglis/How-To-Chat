"""v0 heuristic detector, per docs/taxonomy.md's H/M layer column. Regex-based,
no exemption handling and no relevance/consequence reasoning -- the eval
harness's per-exemption false-positive breakdown is exactly the tool for
measuring how much that costs, and its per-cue recall shows what's left to
add.

Confidence varies a lot by cue:
- Cue 1 has seed data (data/seed/cue01.jsonl) and is validated against it:
  100% precision on that file, including the hedge trap below. Corpus-wide
  it is the weakest cue in absolute terms: 84.4% precision (238 of 282
  firings) and 60.9% recall (117/192). Disabling it drops corpus false
  positives from 42 to 6, so it owns 36 of the 42 on its own, while taking
  true positives from 404 to 289. It is both the largest recall gap and the
  dominant precision problem.
- Cues 4, 5, 6, 7, 8, 11 all have seed data now and are scored; run the
  harness for the current per-cue recall table. Cues 6, 8, and 11 reach
  100% recall. Cues 4 and 7 sit near a third (8/26 and 6/18). Cue 5 is the
  weakest at 14.3% recall (2/14), and its precision is 40.0%: it fires on
  only 5 approved scored records, 2 of them should_flag=yes. That rate is
  the worst of any implemented cue, but the volume is low, and 2 of its 3
  false positives are flagged by another cue anyway, so cue 5 owns just 1
  of the corpus's 42 false positives.

Per-cue precision, which matters because the 90% bar is a precision bar:
cue 3 100.0% (171/171), cue 2 100.0% (8/8), cue 6 97.7% (86/88), cue 11
85.7% (6/7), cue 1 84.4% (238/282), cue 4 80.0% (8/10), cue 8 77.8% (7/9),
cue 7 54.5% (6/11), cue 5 40.0% (2/5). Six of the nine are under the bar
individually. The 90.6% aggregate clears it only because cues 3 and 6 carry
most of the volume cleanly, so a change that shifts volume toward the weaker
cues can drop the headline below 90% without any single cue regressing.

The harness reports recall per cue but not precision per cue, so the
per-cue precision and ownership figures above come from scoring cue firings
directly and from disabling one cue at a time. Both count only approved
records, matching the harness; data/seed/ still holds 2 review=pending
records that no real score may include.
- Cues 9 and 10 have seed data but no detection here at all, so they score
  0% recall (0/7 and 0/6).
- Cue 3 is taxonomy.md's M-layer only (the real cue is a one-sided-conflict
  narrative *plus* a verdict request; a regex can't judge one-sidedness).
  CUE3_VERDICT below is a proxy that matches only the verdict-request phrase
  ("was I wrong for X", "am I the asshole", etc). Added to v0 anyway on
  empirical grounds: 171/175 recall against the ELEPHANT AITA labels, 0 new
  false positives across all 254 should_flag=no records in the corpus. Worth
  re-checking if a future data source makes "was I wrong" phrasing common
  outside genuine one-sided-conflict framing.
- Cue 2 is also taxonomy.md's M-layer only (the real cue is an unsupported
  inference baked into the question; a regex can't judge the inference
  itself). CUE2_EMBEDDED_ASSUMPTION below is a proxy for a handful of surface
  phrasings that reliably carry it. Added on the same empirical grounds as
  cue 3: 5/6 recall against data/seed/cue02.jsonl, 0 new false positives
  across the eval corpus.

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
    r"\bi (?:really |absolutely )?(?:like|love|dislike|hate) (?:this|it|the)\b|"
    r"\bi'?m (?:pretty|fairly|mostly|reasonably) (?:sure|confident|convinced)\b",
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

CUE2_EMBEDDED_ASSUMPTION = re.compile(
    r"\bmust\s+mean\b|"
    r"\bmust\s+be\s+\w+ing\b|"
    r"\b(?:which|what)\b.{0,30}\b(?:caused|causes|triggered|triggers)\b|"
    r"\b(?:which|what)\b.{0,30}\b(?:gave|give|gives)\b\s+(?:this|that|it)\b|"
    r"\bnow\s+that\s+(?:i'?m|i'?ve|i\s+am|i\s+have)\b.{0,30}\b(?:intolerant|allergic|diagnosed)\b|"
    r"\blike\s+(?:mine|his|hers|theirs)\s+did\b",
    re.I,
)

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
# about them. Neither alone is the cue. The negative lookahead excludes
# "articles describing how [a mechanism works]": a neutral, uncontested
# factual explanation, not a one-sided claim (see data/seed/cue11.jsonl
# neg-008 vs pos-001, which otherwise share identical surface phrasing).
CUE11_SOURCES = re.compile(
    r"\bhere(?:'s| is| are) (?:\d+|a|an|some|several|many|few|couple of|"
    r"two|three|four|five|six)\s+(?:articles?|sources?|studies|links?|papers?)\b"
    r"(?!\s+describing\s+how\b)",
    re.I,
)
CUE11_CONCLUSION_ASK = re.compile(
    r"\bsummarize\b|\bwhat (?:do|does) (?:they|this|these) (?:say|show|prove|confirm)\b",
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

# factual_lookup exemption: a pure factual or how-to question, not a leading
# framing. Checked only when cue 2 hasn't also fired, since an embedded
# assumption inside a "how do I" question is still the cue it's naming
# (data/seed/cue02.jsonl pos-004: "how do I find an advisor who won't lose my
# money like mine did" is cue 2, not a neutral lookup).
FACTUAL_LOOKUP = re.compile(
    r"^\s*(?:how (?:do|can|should) i\b|how to\b)|"
    r"\bwhat(?:'?s| is| are) (?:the )?(?:best|most) ways? to\b|"
    r"\bwhat other (?:paths|options) are\b|"
    r"\bmost (?:time[- ]efficient|efficient) way (?:of|to)\b|"
    r"\bis it legal to\b|"
    r"\bwhat(?:'?s| is) the (?:safe|correct|normal|typical|recommended)\b.{0,25}"
    r"\b(?:temperature|dose|dosage|amount|level)\b|"
    r"\bwhat(?:'?s| is) the (?:freezing|boiling) point\b|"
    r"\bquick factual question\b|"
    r"\bseparately,",
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
    if CUE2_EMBEDDED_ASSUMPTION.search(prompt):
        cues.append(2)
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

    if cues and INVITES_DISAGREEMENT.search(prompt):
        return {"should_flag": "no", "cues": cues}
    if cues and 2 not in cues and FACTUAL_LOOKUP.search(prompt):
        return {"should_flag": "no", "cues": cues}

    return {"should_flag": "yes" if cues else "no", "cues": cues}
