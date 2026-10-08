"""v0 heuristic detector, per docs/taxonomy.md's H/M layer column. Regex-based,
no exemption handling and no relevance/consequence reasoning -- the eval
harness's per-exemption false-positive breakdown is exactly the tool for
measuring how much that costs, and its per-cue recall shows what's left to
add.

Confidence varies a lot by cue:
- Cue 1 has seed data (data/seed/cue01.jsonl) and is validated against it:
  100% precision on that file, including the hedge trap below. Corpus-wide
  it is 86.6% precision (285 of 329 firings) and 85.4% recall (164/192).
  Disabling it drops corpus false positives from 39 to 3, so it owns 36 of
  the 39 on its own, and it is still the dominant precision problem. The
  stance verbs in SOFT_STANCE and the rhetorical forms in HARD_STANCE took
  its recall from 60.9% to 85.4% while adding no false positives at all, so
  the 44 bad firings it had before are the same 44 it has now: that work
  raised recall and left precision exactly where it was.
- Cue 7 is 76.9% precision (10/13) and 55.6% recall (10/18), up from 54.5%
  and 33.3%. Read its numbers with care: every one of its true positives
  is a hand-written seed record, and there are no external ones, so any
  fix keyed on surface shape (the authority phrase sitting at the start of
  a short prompt, say) would be fitting the seed templates rather than the
  cue. The guard on "everyone knows" and the generalization of "my doctor
  said" below both turn on what the phrase is doing in the sentence, which
  is why they were acceptable on that evidence. It now owns 1 corpus false
  positive, down from 3.
- Cue 5 is the one cue the corpus cannot measure at all, which matters more
  than its rates. It is follow-up-only, and no external record carries
  prior_turns: all 30 scored records that do are hand-written, and every one
  of them is in data/seed/cue05.jsonl. So cue 5 can only ever fire on
  records I wrote, and a "0 new false positives" result for a cue 5 change
  is vacuous rather than reassuring. Worse, every negative in that file was
  built by appending a reason to its positive, so the positive is a strict
  prefix of the negative in all 13 original pairs, and prompt length alone
  scores 92.9% precision and 92.9% recall on it while knowing nothing about
  the cue. Treat any cue 5 number from this corpus as uninformative until
  real multi-turn data exists. Its rates are 50.0% precision (2/4 firings)
  and 14.3% recall (2/14), and it owns 0 corpus false positives: both of
  its false-positive firings are vetoed by invites_disagreement, so neither
  becomes a wrong flag. By the ownership rule it therefore sits with cues 4,
  8, and 11 as not worth a precision item, despite the rate.
- Cues 4, 6, 8, 11 all have seed data now and are scored; run the harness
  for the current per-cue recall table. Cues 6, 8, and 11 reach 100%
  recall. Cue 4 sits near a third (8/26).
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

Per-cue precision, which matters because the 90% bar is a precision bar:
cue 3 100.0% (171/171), cue 2 100.0% (8/8), cue 6 97.7% (86/88), cue 1
86.6% (285/329), cue 11 85.7% (6/7), cue 4 80.0% (8/10), cue 8 77.8% (7/9),
cue 7 76.9% (10/13), cue 5 50.0% (2/4). Six of the nine are under the bar
individually. The 92.1% aggregate clears it only because cues 3 and 6 carry
most of the volume cleanly, so a change that shifts volume toward the weaker
cues can drop the headline below 90% without any single cue regressing.

Rate alone does not say what is worth fixing; unique false positives owned
does. Disabling one cue at a time, cue 1 owns 36 of the 39 and cue 6 and
cue 7 own 1 each. Cues 2, 3, 4, 5, 8, and 11 own 0: every record they
wrongly flag is either flagged by another cue too or vetoed by an
exemption, so fixing them in isolation changes nothing.

The harness reports recall per cue but not precision per cue, so the
per-cue precision and ownership figures above come from scoring cue firings
directly and from disabling one cue at a time. Both count only approved
records, matching the harness; data/seed/ holds 33 review=pending records
that no real score may include. Scoring them anyway, as a preview rather
than a result, gives 91.8% precision and 86.7% recall over 813 records: the
pending set lowers precision slightly, because 2 of the 6 new cue 5 records
were written to document a gap v0 does not handle (see below).

One definition to keep straight when comparing those numbers to anything
else: a "firing" counts the cue appearing in the output, including on
records an exemption later vetoes, so a cue can be charged for a firing
that never became a wrong flag. Every per-cue precision figure above uses
that definition, which is the one the earlier baselines were measured with,
so before/after comparisons are consistent. It is the harsher reading. Cue
7 is the clearest case: 3 of its 13 firings land on negative records but
only 2 survive the exemptions, so it is 76.9% by firing and 83.3% (10/12)
by wrong flag. The headline precision the harness prints is unaffected
either way, since it scores the final decision, not cue attribution.

One harness quirk worth knowing: `--detector v0_heuristic` also prints a
"Safety flags" section, but it scores *this* detector against the safety
records, so the 50% it shows there is meaningless. The safety figures come
from `--detector v0_heuristic_safety`.

Cue 1's biggest false-positive trap (see data/seed/cue01.jsonl neg-004): a
hedged belief ("I think X, but I'm not sure") isn't an asserted stance. The
soft phrases ("I think", "I believe") are only matched in a sentence that
doesn't also carry a hedge; the hard phrases ("I know for a fact", tag
questions, numeric anchors) don't need the guard because hedging them would
be self-contradictory ("I'm 100% sure, but not sure"). The stance verbs are
in the soft group too, so they inherit the same guard.

That guard is also a known recall cost. It is a blanket veto, used as a
crude stand-in for "the stance doesn't bear on the question," and it is
wrong on hedged guesses that do bear on it: a hedged wrong answer to a
factual question ("I think the answer is Columbus but I'm really not
sure") is labeled should_flag=yes in data/labels/sharma_answer.jsonl,
because agreeing confirms the wrong fact.

Of the 28 cue 1 records still missed, 17 are that Sharma template, every
one of them literally "I (don't) think the answer is X but I'm really not
sure"; 10 of those also need a pattern for "I don't think", which
SOFT_STANCE does not have. 6 more are Phare rows whose labelled trigger
is conversational filler ("You know,"). The remaining 5 are one-off
phrasings.

Both of the big groups argue for care rather than more patterns.
Narrowing the hedge veto cuts against the reasoning behind c01-neg-004,
so it needs a decision, and the 17 it would buy are all one benchmark
template, which is thin grounds (see CLAUDE.md's open item on weighting
benchmark phrasing). Matching "You know," would score +6 true positives
and 0 false positives here, and was still rejected: it is a filler
phrase, and this corpus has no negatives with conversational filler in
them, so the 0 is uninformative rather than reassuring.

Every pattern added to cue 1 so far was measured one at a time and kept
only at 0 new corpus false positives. Candidates rejected on that rule:
intensifiers before think/believe ("I strongly believe"), "I don't
think/believe/agree", and "I am concerned that", each +1 false positive.

Cue 1 is deliberately *not* carved out of the FACTUAL_LOOKUP exemption the
way cue 2 is. Adding it costs 7 false positives for 0 true positives on
the corpus. The price is a known miss, c01-pos-014: a false premise
asserted as shared knowledge, followed by a how-to whose "what's the best
way to" trips the lookup exemption.

Cue 7's false positives came from "everyone knows" having two senses that
are not the cue. The literal one reports that people are aware of the
author's situation ("everyone knows about it", data/seed/cue07.jsonl
neg-011), and the relativized one buries it in the object of a question
("a fact everyone knows is true", neg-012). Neither offers a claim for an
agreeable answer to defer to, so CUE7_AUTHORITY requires a claim to
follow. What remains is the relevance half of the flag rule, which a
regex cannot reach: c07-neg-008 cites an authority on a topic unrelated
to the question asked, and one Reddit post (ext-elephant_oeq-960) has
friends agreeing about something other than what it goes on to ask. Only
c07-neg-008 is cue 7's own: cue 1 fires on the Reddit record too, so
disabling cue 7 would not clear it, which is why ownership is 1 and not 2.

Cue 7's remaining 8 misses are 5 Phare "I just read that" rows, which
cue 1 already flags so fixing the attribution moves no headline number,
2 "I've read quite a bit" rows, and 1 "my friends, who are research
scientists, share". The read-a-lot pattern scores +2 true positives and 0
false positives and was still rejected: it is the user's own claimed
diligence, not social proof or an authority, so it does not match what
taxonomy.md asks cue 7 to be, and the corpus has no neutral "I've read a
lot about X" negatives that would catch the cost. Loosening "all my
friends" to "my friends" was rejected too: it moved no headline number
and it widens the pattern toward the Reddit narrative shape that is
already one of cue 7's two remaining false positives.

Cue 5's one corpus-visible false positive was c05-neg-001, "Are you sure?
I've taken them together for years without an issue." The user gave a
reason and v0 flagged them anyway, which is the worst failure this cue can
have: the tip tells them to include a reason, and they did. The fix is in
CUE5_JUSTIFICATION, which now recognizes personal experience as evidence.
Only that one record tests it, so the shape of the addition was chosen
against 8 hand-written probe prompts rather than against the corpus, which
rates every candidate variant identically. That is weaker evidence than a
corpus measurement and is recorded as such. The probes are what rejected
bare "for years/months" (it also vetoes "I've been going back and forth on
this for months", which is deliberation, not evidence) in favor of the
verb-anchored form, and what rejected "I've always" and "I've been"
outright as far too broad.

What was deliberately *not* done is widen CUE5_PUSHBACK. That is the recall
half, which would take cue 5 from 14.3% toward 100%, and every one of the
12 records it would pick up is one I wrote, in a file where length alone
already scores 92.9%. The gain would be headline-visible and meaningless,
and the cost is unmeasurable: a wider pushback pattern fires on every
multi-turn follow-up carrying doubt, and the corpus has no real multi-turn
negatives at all. CUE5_JUSTIFICATION would be the only thing holding the
precision line, and it is a regex standing in for "did the user add new
information", which is a semantic question.

Two of the 6 new cue 5 records, c05-neg-020 and c05-neg-021, are known
false positives v0 does not handle: a third party as the source of the
reason ("the pharmacist printed a sheet that says ...") and "I pulled up
my statement", neither of which is in CUE5_JUSTIFICATION's verb list. They
were left unfixed on purpose. Patching them would mean coding against two
records written in the same sitting with nothing independent to check the
patch, which is the fit-to-template trap the cue 7 note describes. They are
here to document the gap for whoever has real multi-turn data.
"""
import re

SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")
QUOTED_SPEECH = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d')
HEDGE = re.compile(r"\bnot sure\b|\bnot certain\b|\bunsure\b|\bnot convinced\b", re.I)

SOFT_STANCE = re.compile(
    r"\bi (?:really )?(?:think|believe)\b|"
    r"\bi (?:really |absolutely )?(?:like|love|dislike|hate) (?:this|it|the)\b|"
    r"\bi'?m (?:pretty|fairly|mostly|reasonably) (?:sure|confident|convinced)\b|"
    # Stance verbs. "I agree that X" asserts a stance the same way "I think X"
    # does, and taxonomy.md's cue 1 covers both. "agree with you" is excluded:
    # in a follow-up it endorses the model's last answer rather than taking a
    # position on the question being asked.
    r"\bi (?:completely |totally |strongly |somewhat |really )?(?:agree|disagree) (?:that|with (?!you\b))\b|"
    r"\bi (?:would|have to|tend to) (?:agree|disagree)\b|"
    r"\bi do not agree (?:that|with)\b|"
    r"\bi(?:'?m| am) (?:pretty |very |quite |fairly |somewhat )?skeptical\b|"
    r"\bi have a (?:strong|firm) belief that\b|"
    r"\bi (?:don'?t|do not) (?:buy|accept) (?:that|the)\b",
    re.I,
)
HARD_STANCE = [
    re.compile(r"\bi know for a fact\b", re.I),
    re.compile(r"\bi'?m (?:totally |completely |absolutely )?(?:100%\s*)?(?:sure|convinced)\b", re.I),
    # Spelled-out form of the 100% pattern above.
    re.compile(r"\ba hundred percent (?:sure|certain)\b", re.I),
    re.compile(r",?\s*right\?", re.I),
    re.compile(r"isn'?t it(?:\s+true)?\??$", re.I),
    # Same tag question away from the end of the prompt. Kept to a closed word
    # list rather than dropping the anchor outright, so "isn't it" followed by
    # anything doesn't become a match.
    re.compile(r"\bisn'?t it (?:interesting|obvious|clear|true)\b", re.I),
    re.compile(r"\bdon'?t you agree\b", re.I),
    re.compile(r"\bdid you know that\b", re.I),
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
    r"\bi (?:checked|found|looked|read|verified)\b|\baccording to\b|\bthe reason is\b|"
    # Personal experience offered as evidence. An absence of adverse outcome
    # ("never had a problem", "without an issue") is a factual claim about what
    # happened, so it is new information and the cue does not apply.
    r"\bnever had (?:a|any) (?:problem|issue|trouble)\b|"
    r"\bwithout (?:an|any) (?:issue|problem|trouble)\b|"
    # Duration of use, anchored to a verb of doing or taking. Bare "for
    # years/months" also matches time spent deliberating ("I've been going
    # back and forth on this for months"), which is not evidence and must
    # still count as the cue.
    r"\b(?:taken|took|used|using|done|did|driven|drove|ran|run|had it|been on)\b"
    r"[^.?!]{0,40}?\bfor (?:years|decades|months)\b",
    re.I,
)

CUE7_AUTHORITY = re.compile(
    # "everyone knows" only counts when a claim follows it. Without the
    # guard it also matches the literal sense ("everyone knows about it",
    # about the author's situation) and the relativized sense ("a fact
    # everyone knows is true"), neither of which supports a claim the user
    # wants confirmed. Those were 2 of cue 7's false positives.
    r"\beveryone knows\b(?!\s+(?:about|of|is|was|were)\b)|"
    r"\bexperts agree\b|\bmany people agree\b|"
    # taxonomy.md names "my doctor said"; the cue is the same for any
    # professional the user is deferring to. The bounded gap allows the
    # appositive people actually write ("my teacher, who is very smart,
    # explained that ..."), and stops at a sentence boundary so it cannot
    # reach across to an unrelated verb.
    r"\bmy (?:doctor|dentist|teacher|professor|lawyer|accountant|mechanic"
    r"|therapist|pharmacist|vet|nurse|contractor|realtor|financial advisor)\b"
    r"[^.?!]{0,60}?\b(?:said|says|told me|tells me|explained)\b|"
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


def _normalize(text):
    """Fold the curly apostrophe onto the straight one.

    macOS and iOS substitute U+2019 as the user types, so the shipped
    extension sees "I'm" far more often than the "I'm" every pattern here is
    written with. Three of six realistic cue 1 prompts silently stopped
    matching when retyped with smart quotes. The eval corpus cannot show
    this: its external text uses straight quotes, so normalizing moves no
    headline number. QUOTED_SPEECH already folds the curly double quotes for
    the same reason.
    """
    return text.replace("\u2019", "'").replace("\u2018", "'")


def predict(prompt, prior_turns):
    prompt = _normalize(prompt)
    prior_turns = [
        dict(turn, content=_normalize(turn.get("content", "")))
        for turn in (prior_turns or [])
    ]

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
