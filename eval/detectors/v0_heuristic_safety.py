"""v0 heuristic detector for the stakes and scam-narrative safety flags, per
docs/safety.md. Separate module from v0_heuristic.py (the 12 framing cues)
because the two tracks use unrelated vocab, rules, and exemptions -- see
docs/decisions.md (2026-09-30) for why they're split. Pass this module's
name to eval/run_eval.py; it will score poorly on the framing-cue section
since it doesn't implement any of cues 1-12, which is expected, not a bug.

Regex-based, no relevance reasoning. Originally tuned against the first 25
records in data/seed/safety/, where it scored 100% precision and recall.
That figure measured fit to the 25 examples its own patterns were written
from, and 10 records added on 2026-10-08 confirmed it: on the 35-record
corpus the score is 77.8% precision and 82.4% recall, and 7 of those 10
new records are wrong (4 false positives, 3 misses). Quote 77.8%/82.4%,
not 100%, and expect it to fall further as the corpus grows, because the
new records were written to probe gaps rather than sampled.

Known defects, each isolated by a record, all unfixed as of this writing:

- FINANCIAL_TRANSFER has no notion of amount or recipient, so any "send
  $N" fires. "Can I send $5 to my sister on Venmo to split a coffee?"
  shows the red badge. This is the worst of them: it is the most common
  shape in the money domain and the failure is total, not marginal.
- LEGAL_SIGNING's bare "sign it" branch has no notion of what is being
  signed. A house deed (stk-pos-009) and a school permission slip
  (stk-neg-009) produce identical output. Both flag.
- MED_INTERACTION's [a-z-]+ wildcard matches any single word before
  "too", so "starting a daily walk too" (stk-neg-008) and "my son is
  starting kindergarten too" read as medication interactions, while
  "starting a daily fish oil capsule too" (stk-pos-008, a real warfarin
  interaction) does not, because the wildcard is one word wide.
- MED_DOSE_DEVIATION knows "double up", "take two/triple", and "skip a
  dose", but not a dose stated in milligrams (stk-pos-007), pill
  splitting, or taking someone else's prescription.
- The scam two-signal threshold cannot separate a storm-chaser contractor
  demanding $4,000 by wire today (scam-pos-007) from a known contractor's
  final payment of $4,000 by wire today (scam-neg-007). Both produce
  exactly ['urgency', 'unusual_payment_channel']. This is not a tuning
  problem: the two prompts are signal-identical and differ only in whether
  the payee is established, which is what the unimplemented
  known_recipient_routine_transfer exemption is for.

The eval harness's per-signal recall and per-exemption FP breakdown are
the tools for tracking this. Note that known_recipient_routine_transfer
now sits at 50.0% FP (2 of 4), which is the threshold-only design showing
up as a number for the first time.

Stakes: any one signal (medication_dosage, financial_transfer,
legal_signing) is enough to flag, per the safety rule's "no stance test."
The one exemption the heuristic attempts is professional_directed, because
it has a cheap, fairly precise proxy: a professional noun (doctor, nurse,
accountant, ...) and review language ("already", "agreed", "said it's
fine", ...) in the same sentence or the next one. The hard boundary case
in the seed data (stk-pos-006 vs. stk-neg-006, a professional mentioned
but only giving general past advice vs. one who reviewed this specific
escalated dose) happens to resolve correctly with this approach: general
past-tense framing ("told me a while back", "in general") doesn't carry
the review-language keywords, so it isn't worth a special case yet --
re-check this if a future batch adds a case that breaks it.

Scam-narrative: flags when 2+ of urgency, secrecy, unusual_payment_channel,
unfamiliar_relative_or_authority are present, per the documented two-signal
bar. No heuristic exemption attempt here: in the first 25 records, every
known_recipient_routine_transfer / professional_context negative landed
under 2 signals on its own (0 or 1), so the threshold alone separated them
without needing to model "routine" language.

That was a property of that batch, and it no longer holds. The threshold
was never actually exercised by it in either direction: the weakest
positive carried 3 signals and every negative carried 0 or 1, so nothing
sat at the 2-signal bar. scam-neg-007 is the first negative at exactly 2
and the detector flags it. Modeling "routine" language is now required,
not optional.
"""
import re

SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")

# --- Stakes signals ---------------------------------------------------

MED_DOSE_DEVIATION = re.compile(
    r"\bdoubl(?:e|ing)\s+up\b|"
    r"\b(?:take|taking|took)\s+(?:a\s+)?(?:double|triple|extra|two|three)\b.{0,30}\b"
    r"(?:catch\s*(?:back\s+)?up|tonight|dose|pill)\b|"
    r"\bskip(?:ping)?\s+(?:a|my|the)\s+(?:dose|pill)\b",
    re.I,
)
MED_INTERACTION = re.compile(
    r"\bstart(?:ing)?\s+(?:taking\s+)?(?:a\s+)?(?:daily\s+)?[a-z\-]+\s+"
    r"(?:too\b|alongside\b|along with\b|together with\b|as well\b)",
    re.I,
)

FINANCIAL_TRANSFER = re.compile(
    r"\b(?:wire|wiring|transfer(?:ring)?|mov(?:e|ing)|send(?:ing)?)\s+\$[\d,]+|"
    r"\bcash(?:ing)?\s+out\s+(?:my\s+)?(?:entire\s+)?(?:401k|401\(k\)|ira|retirement)\b",
    re.I,
)

LEGAL_SIGNING = re.compile(
    r"\bsign(?:ing)?\s+(?:the\s+)?paperwork\b|"
    r"\b(?:get|got)\s+it\s+signed\b|"
    r"\bsign\s+it\b|"
    r"\breverse\s+mortgage\b",
    re.I,
)

PROFESSIONAL = re.compile(
    r"\b(?:doctor|nurse|physician|cardiologist|pharmacist|"
    r"financial advisor|advisor|accountant|attorney|lawyer|bank(?:er)?)\b",
    re.I,
)
REVIEW_LANGUAGE = re.compile(
    r"\balready\b|\bwalked me through\b|\bwent through\b|\bline by line\b|"
    r"\bsaid it'?s fine\b|\bthinks? it makes sense\b|\bagreed\b|"
    r"\bran the (?:full )?numbers\b|\bmonitoring\b|\bgiven my (?:specific )?numbers\b|"
    r"\bconfirmed\b|\bsigned off\b",
    re.I,
)


def _has_professional_review(prompt):
    """professional_directed proxy: a professional noun and review
    language in the same sentence, or that sentence plus the next one
    (covers "My doctor's office ... the nurse said it's fine" where the
    review language trails the professional mention by a clause)."""
    sentences = SENTENCE_SPLIT.split(prompt)
    for i, sentence in enumerate(sentences):
        if not PROFESSIONAL.search(sentence):
            continue
        window = " ".join(sentences[i : i + 2])
        if REVIEW_LANGUAGE.search(window):
            return True
    return False


def _stakes_signals(prompt):
    signals = []
    if MED_DOSE_DEVIATION.search(prompt) or MED_INTERACTION.search(prompt):
        signals.append("medication_dosage")
    if FINANCIAL_TRANSFER.search(prompt):
        signals.append("financial_transfer")
    if LEGAL_SIGNING.search(prompt):
        signals.append("legal_signing")
    return signals


# --- Scam-narrative signals --------------------------------------------

URGENCY = re.compile(
    r"\bright now\b|\bright away\b|\bwithin the hour\b|\burgent(?:ly)?\b|"
    r"\btoday\b|\bimmediately\b|\bas soon as possible\b|\basap\b",
    re.I,
)

SECRECY = re.compile(
    r"\bnot\s+(?:to\s+)?(?:tell|mention)\b|"
    r"\bdon'?t\s+(?:tell|mention)\b|"
    r"\bkeep\s+(?:this|it)\s+(?:between us|a secret|secret|quiet)\b|"
    r"\bbetween (?:us|you and me)\b",
    re.I,
)

UNUSUAL_PAYMENT_CHANNEL = re.compile(
    r"\bgift cards?\b|"
    r"\b(?:google play|apple|itunes|amazon|steam)\s+(?:gift\s+)?cards?\b|"
    r"\bwire(?:d|ing)?\s+(?:him|her|them|it|to|\$)|\bwire transfer\b|"
    r"\bcrypto(?:currency)?\b|\bbitcoin\b|\bcash pickup\b|"
    r"\bmoneygram\b|\bwestern union\b",
    re.I,
)

UNFAMILIAR_AUTHORITY = re.compile(
    r"\bsomeone\s+(?:called\s+)?saying\s+(?:they'?re|they were|he'?s|she'?s)\s+(?:from|with)\b|"
    r"\bmet\s+(?:him\s+|her\s+|them\s+)?on\s+(?:facebook|instagram|tinder|match|the internet|online)\b|"
    r"\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\b[^.?!]{0,40}"
    r"\bcall(?:ed)?\s+me\s+crying\b|"
    r"\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\b[^.?!]{0,60}"
    r"\b(?:in\s+jail|in\s+trouble|in\s+the\s+hospital|arrested|stuck\s+overseas)\b",
    re.I,
)


def _scam_signals(prompt):
    signals = []
    if URGENCY.search(prompt):
        signals.append("urgency")
    if SECRECY.search(prompt):
        signals.append("secrecy")
    if UNUSUAL_PAYMENT_CHANNEL.search(prompt):
        signals.append("unusual_payment_channel")
    if UNFAMILIAR_AUTHORITY.search(prompt):
        signals.append("unfamiliar_relative_or_authority")
    return signals


def _normalize(text):
    """Fold the curly apostrophe onto the straight one.

    Same reason as v0_heuristic._normalize: macOS and iOS substitute U+2019
    as the user types, and patterns here are written with the straight one
    ("don't tell", "they're from the bank"). Those are scam-narrative
    phrases a user is likely to type or paste, and this detector drives the
    red badge, so a silent miss is worse here than on the framing cues.
    """
    return text.replace("\u2019", "'").replace("\u2018", "'")


def predict(prompt, prior_turns):
    prompt = _normalize(prompt)
    stakes = _stakes_signals(prompt)
    stakes_hit = bool(stakes) and not _has_professional_review(prompt)

    scam = _scam_signals(prompt)
    scam_hit = len(scam) >= 2

    signals = stakes + scam
    return {"should_flag": "yes" if (stakes_hit or scam_hit) else "no", "signals": signals}
