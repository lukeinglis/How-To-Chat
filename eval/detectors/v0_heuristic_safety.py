"""v0 heuristic detector for the stakes and scam-narrative safety flags, per
docs/safety.md. Separate module from v0_heuristic.py (the 12 framing cues)
because the two tracks use unrelated vocab, rules, and exemptions -- see
docs/decisions.md (2026-09-30) for why they're split. Pass this module's
name to eval/run_eval.py; it will score poorly on the framing-cue section
since it doesn't implement any of cues 1-12, which is expected, not a bug.

Regex-based, no relevance reasoning.

== Read this before quoting any number from this module ==

On the 35-record corpus in data/seed/safety/ this scores 100% precision
and 100% recall. That number is fit, not evidence: the patterns were
written from those records. The same was true of the previous version,
which scored 100%/100% on 25 records and then dropped to 77.8%/82.4% the
moment 10 adversarial records were added. Do not report the corpus figure
without the caveat.

What the rebuild was measured against instead was five held-out probe
sets, written at /tmp and not committed (the useful ones are reproduced as
records below). Each set was written before the fixes it would go on to
drive, and the moment a set was used as a fix target its figure became fit
too. The progression:

    set  n   provenance                     precision  recall
    1    37  pre-rebuild, design target     100.0%     100.0%
    2    27  post-rebuild, fix target       100.0%     100.0%
    3    28  post-set-2-fixes, fix target   100.0%      91.7%
    4    32  post-set-3-fixes, fix target   100.0%      92.9%
    5    31  post-all-fixes, scored ONCE    100.0%      38.5%

Set 5 is the only honest row, and set 4's first scoring (before it was
used for fixes) agreed with it closely: 100% precision, 35.7% recall. Two
independently written sets landing at 35.7% and 38.5% is the real estimate.

So the finding is a split verdict:

- Precision generalizes. Zero false positives across all five sets, 96
  held-out negatives total, and in sets 4 and 5 the negatives were
  topic-matched to the positives on purpose (same rash, same contractor,
  same nephew, differing only in whether a deviation or a scam element is
  present), so topic alone cannot be carrying it. The old detector scored
  14.3% precision on set 1. This is the half that matters for a red badge
  and it is genuinely fixed.
- Recall does not generalize. Every set reaches ~90%+ once it has been
  used to drive fixes and the next fresh set lands back near 38%. Four
  rounds of pattern work did not move that, because each round adds the
  specific phrasings in front of it and the space of ways to describe a
  medication deviation or a scam script is not regex-shaped. Treat ~38% as
  the ceiling for this approach, not as a tuning target.

That is the argument for the classifier in CLAUDE.md's roadmap item 5
applying to the safety flags too, not only to the framing cues. More
regex branches will keep buying corpus recall and no real recall.

The five defects the 2026-10-08 records exposed are all fixed:
FINANCIAL_TRANSFER now has an amount floor and an own-account veto;
LEGAL_SIGNING requires both an act and a document; MED_INTERACTION uses a
named substance list instead of a one-word wildcard; MED_DOSE_DEVIATION
covers milligram doses, splitting, frequency, form changes, leftover and
borrowed prescriptions; and known_recipient_routine_transfer plus
professional_context are implemented rather than left to the threshold.

Known remaining misses, confirmed by probe and left unfixed on purpose,
each a family rather than a phrasing:

- Food-drug interactions. "I take a statin at night and I just started
  drinking grapefruit juice with breakfast as well" misses, because the
  substance list is drugs and supplements and the verb is "drinking".
- Down payments. "I'm about to put $25,000 down on a timeshare" misses.
  Adding "put $N down" would fire on every ordinary car and house down
  payment, which is a precision cost not worth the one archetype.
- Topical and non-oral doses ("half a tube of the steroid cream my doctor
  gave me two years ago"), vomited doses, fractional doses stated in
  pills ("one and a half instead of one"), and opening an adult capsule
  for a child. Each is a real medication deviation with no shared surface.
- Single-signal scam narratives. A toll-text smish and a warranty-refund
  callback each carry exactly one signal, and the documented bar is two.
  Lowering it to one would flag every prompt containing "today".

The eval harness's per-signal recall and per-exemption FP breakdown are
the tools for tracking this.

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

The professional_directed proxy also treats a prescriber *making* a change
as direction, not just one reviewing a change the user proposed: "my
doctor doubled my dose at my appointment yesterday" is the clearest case
of the exemption there is, and the original review vocabulary covered only
the reviewing direction, so that prompt read as a deviation.

Scam-narrative: flags when 2+ of urgency, secrecy, unusual_payment_channel,
unfamiliar_relative_or_authority are present, per the documented two-signal
bar, minus the exemptions below.

The original version attempted no scam exemption, on the grounds that in
the first 25 records every known_recipient_routine_transfer /
professional_context negative landed under 2 signals on its own (0 or 1),
so the threshold alone separated them without needing to model "routine"
language. That was a property of that batch. The threshold was never
actually exercised by it in either direction: the weakest positive carried
3 signals and every negative carried 0 or 1, so nothing sat at the bar.
scam-neg-007 is the first negative at exactly 2 signals, and it is
signal-identical to scam-pos-007, so both exemptions are now modeled
directly (ROUTINE_PAYEE, BUSINESS_PROFESSIONAL).

Both are guarded by NEW_COUNTERPARTY, which is the load-bearing part: the
scam scripts copy routine language and routine amounts deliberately, so
"same amount as always" cannot be allowed to clear a prompt that also says
"from a new account". Probe set 2 includes two prompts built to abuse
exactly that, and they are the reason the guard exists.
"""
import re

SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")

# --- Stakes signals ---------------------------------------------------

# Named substances, shared by MED_DOSE_DEVIATION and MED_INTERACTION.
# MED_INTERACTION previously used a bare [a-z-]+ here, one word wide, which
# made it simultaneously too broad ("starting a daily walk too" read as a
# drug interaction) and too narrow (a two-word substance like "fish oil
# capsule" did not match). Naming substances fixes both. The list is not
# meant to be exhaustive; it is the vocabulary a non-technical adult is
# likely to type, and the generic dose-form nouns at the end carry the
# "this is a substance" information when the drug is not named.
_SUBSTANCE = (
    r"(?:aspirin|ibuprofen|advil|motrin|tylenol|acetaminophen|naproxen|aleve"
    r"|warfarin|coumadin|eliquis|xarelto|metformin|insulin|statin|lipitor"
    r"|lisinopril|metoprolol|amlodipine|levothyroxine|prednisone|gabapentin"
    r"|sertraline|zoloft|lexapro|prozac|xanax|ativan|ambien|adderall"
    r"|melatonin|turmeric|curcumin|fish\s+oil|omega[-\s]?3|st\.?\s+john'?s\s+wort"
    r"|ginkgo|ginseng|echinacea|magnesium|potassium|calcium|iron|zinc|cbd"
    r"|vitamin\s+[a-z0-9]+|multivitamin|probiotic|creatine|collagen"
    r"|ashwagandha|valerian|biotin|elderberry|saw\s+palmetto"
    r"|milk\s+thistle|glucosamine|coq10|niacin|folic\s+acid|b12"
    r"|amoxicillin|azithromycin|penicillin|cephalexin|doxycycline|ciprofloxacin"
    r"|hydrocodone|oxycodone|tramadol|hydrochlorothiazide|furosemide|omeprazole"
    r"|supplement|capsule|tablet|pill|medication|medicine|herb|extract"
    r"|tincture|drops|syrup|powder|gummy|gummies|patch|inhaler)"
)

MED_DOSE_DEVIATION = re.compile(
    # Past tense is required, not optional: docs/safety.md says reporting the
    # action as already taken does not exempt it, so "doubled up" has to match
    # wherever "double up" does. The original alternation omitted it.
    r"\bdoubl(?:e|ed|ing)\s+up\b|"
    r"\b(?:take|taking|took)\s+(?:a\s+)?(?:double|triple|extra|two|three)\b.{0,30}\b"
    r"(?:catch\s*(?:back\s+)?up|tonight|dose|pill)\b|"
    r"\bskip(?:ping)?\s+(?:a|my|the)\s+(?:dose|pill)\b|"
    r"\b(?:take|taking|took)\s+(?:an?\s+)?extra\s+(?:one|dose|pill|tablet|capsule)\b|"
    r"\b(?:took|taking|take)\s+a\s+second\s+[a-z\-]+\b[^.?!]{0,40}"
    r"\b(?:after|hour|later|same day)\b|"
    r"\bdoubl(?:e|ing|ed)\s+(?:my|the|his|her)\s+[a-z\-]+\b|"
    # Stretching a supply: same family as splitting pills.
    r"\bevery\s+other\s+day\b[^.?!]{0,40}\b(?:stretch|last|ration|save)\b|"
    r"\b(?:stretch|ration)\s+(?:it|them|my)\b[^.?!]{0,30}\b(?:out|longer|until)\b|"
    # Altering the dose form, same family as splitting.
    r"\b(?:crush|crushing|chew|chewing|open|opening|dissolve|dissolving)\s+"
    r"(?:my|the|these|an?)\s+(?:extended[-\s]release\s+|er\s+|xr\s+|time[-\s]release\s+)?"
    r"(?:pill|tablet|capsule|dose)\b|"
    # Stopping without guidance.
    r"\b(?:stopped|stopping|quit|quitting)\b[^.?!]{0,40}\bcold\s+turkey\b|"
    # A dose stated in units, taken in place of the prescribed one. The
    # "instead" is what makes it a deviation: without it, "I take 20mg" is
    # just the user reporting their prescription. A dose the prescriber
    # raised reads as "my doctor moved me up to 20mg", which has no
    # "instead" and so does not match.
    r"\b(?:take|taking|took)\s+(?:the\s+)?\d+\s*(?:mg|mcg|ml|iu|g)\b[^.?!]{0,40}\binstead\b|"
    # Splitting or stretching a prescription.
    r"\b(?:cut|cutting|split|splitting|break|breaking)\s+(?:them|it|the|my|these)\b"
    r"[^.?!]{0,20}\bin\s+half\b|"
    r"\bhalf\s+(?:a|my|the)\s+(?:pill|tablet|dose)\b|"
    # Taking medication prescribed to someone else.
    r"\b(?:my|a)\s+(?:neighbor|friend|sister|brother|husband|wife|mother|father"
    r"|mom|dad|roommate|co-?worker|son|daughter)\b[^.?!]{0,60}"
    r"\bsame\s+(?:prescription|medication|pills?|dosage)\b|"
    r"\b(?:use|used|using|take|took|taking|borrow|borrowed|borrowing)\s+"
    r"(?:a few of|some of|one of)\s+(?:hers|his|theirs)\b|"
    # Leftover or expired prescriptions, same family as taking someone
    # else's: the dose is real but nobody current is directing it.
    r"\b(?:left\s*over|leftover|old|expired)\s+"
    r"(?:[a-z\-]+\s+){0,2}?(?:pills?|antibiotics?|prescription|medication|tablets?|capsules?)\b|"
    r"\b(?:pills?|antibiotics?|prescription|medication)\b[^.?!]{0,30}"
    r"\bleft\s*over\s+from\b|"
    r"\b" + _SUBSTANCE + r"\b[^.?!]{0,30}\bleft\s*over\b|"
    # Taking a dose more often than the label says. Same "instead" shape as
    # the milligram branch: without it, "I take them every eight hours" is
    # the user reporting their prescription correctly.
    r"\bevery\s+(?:\d+|two|three|four|six|eight|twelve)\s*(?:hours?|hrs?)?\s*\binstead\b|"
    r"\btaking\s+(?:them|it)\s+every\s+(?:\d+|two|three|four|six|eight|twelve)\b"
    r"[^.?!]{0,30}\binstead\b|"
    # A label instruction the user is about to override. The defiance marker
    # is required: "the bottle says don't drink with this" on its own is a
    # user reading their label correctly, which is not a deviation.
    r"\bsays?\b[^.?!]{0,60}\b(?:don'?t|do not|not to|avoid)\s+"
    r"(?:drink|mix|take|combine|have)\b[^.?!]{0,80}"
    r"\b(?:but|anyway|won'?t matter|just this once|one\s+(?:glass|drink|time))\b",
    re.I,
)

MED_INTERACTION = re.compile(
    r"\bstart(?:ing)?\s+(?:to\s+take\s+|taking\s+)?(?:a\s+|the\s+|some\s+)?"
    r"(?:daily\s+|nightly\s+|new\s+|low[-\s]dose\s+)?"
    r"(?:[a-z\-]+\s+){0,3}?" + _SUBSTANCE + r"\b[^.?!]{0,30}"
    r"\b(?:too|alongside|along with|together with|as well|on top of)\b",
    re.I,
)

# Dollar amounts, for the stakes floor below.
AMOUNT = re.compile(r"\$\s?([\d,]+(?:\.\d{2})?)")

# The stakes flag's money floor. docs/safety.md defines the flag as an action
# with "hard-to-reverse real-world consequences", and the old pattern had no
# notion of amount at all, so "send $5 to my sister on Venmo to split a
# coffee" showed the red badge. The figure is a judgment call with no corpus
# basis: $1,000 is roughly where a mistaken transfer stops being absorbable
# for the non-technical adults this is built for, and it sits well clear of
# every routine amount in the corpus ($5 to $500) and well under every
# consequential one ($9,000 to $180,000). Nothing in the data pins it more
# precisely than that, so treat it as a placeholder for a number that should
# come from real usage. The scam flag deliberately has no floor: a $300 gift
# card demand is the archetype, and its signals carry the discrimination.
STAKES_AMOUNT_FLOOR = 1000.0

# Verb-adjacent transfers. Kept adjacent to the dollar figure on purpose: the
# looser "$4,000 by wire transfer" shape appears in scam-neg-007, a known
# contractor's final payment, where a stakes flag would be wrong.
FINANCIAL_TRANSFER_VERB = re.compile(
    r"\b(?:wire|wiring|transfer(?:ring)?|mov(?:e|ing)|send(?:ing)?|pay(?:ing)?)\s+"
    r"(?:[a-z']+\s+){0,3}?\$[\d,]+",
    re.I,
)
# Actions that are consequential regardless of the figure attached, so they
# skip the floor.
FINANCIAL_IRREVERSIBLE = re.compile(
    r"\bcash(?:ing)?\s+out\s+(?:my\s+)?(?:entire\s+)?(?:401k|401\(k\)|ira|retirement|pension)\b|"
    r"\bcash\s+advance\b|"
    r"\bborrow(?:ing)?\s+against\b|"
    r"\b(?:home\s+equity|second\s+mortgage|reverse\s+mortgage)\b|"
    r"\bliquidat(?:e|ing)\s+(?:my\s+)?(?:401k|ira|retirement|investments?|portfolio)\b|"
    # Same action as "cash out my IRA", different verb. An early withdrawal
    # carries a penalty that cannot be undone once taken.
    r"\b(?:tak(?:e|ing)|took|pull(?:ing|ed)?|withdraw(?:ing|n)?|drew)\b[^.?!]{0,30}"
    r"\b(?:out\s+of|from)\s+(?:my\s+)?(?:401k|401\(k\)|ira|roth|retirement|pension)\b",
    re.I,
)
# The user's own accounts. Moving money between them is not a stakes event at
# any size, so this vetoes the verb-adjacent branch.
OWN_ACCOUNT = re.compile(
    # The possessive is required. "into savings for me" with a third-party
    # recipient ("send $8,000 to my new financial guy to put into savings")
    # is not an own-account move, and the earlier possessive-optional version
    # vetoed it.
    r"\b(?:to|into)\s+(?:my|our)\s+(?:own\s+)?"
    r"(?:savings|checking|emergency\s+fund|money\s+market|brokerage)\b|"
    r"\bfrom\s+(?:my\s+|our\s+)?(?:checking|savings)\s+(?:in)?to\s+"
    r"(?:my\s+|our\s+)?(?:checking|savings)\b|"
    r"\bbetween\s+(?:my|our)\s+(?:own\s+)?accounts\b",
    re.I,
)

# Signing splits into the act and the document. The old pattern had only the
# act, so a bare "sign it" fired with no idea what was being signed, and a
# house deed (stk-pos-009) and a school permission slip (stk-neg-009) gave
# identical output. Both are now required.
SIGNING_ACT = re.compile(
    # "sign up"/"signed up for" is enrolling, not executing a document, and it
    # is excluded: "I signed up for a two-year phone contract" and "signing up
    # for the library reading program" are not stakes events.
    r"\bsign(?:ing|ed)?\b(?!\s+up\b)|\b(?:get|got)\s+it\s+signed\b|"
    r"\bsignature\b|\binitial(?:ing|ed)?\s+(?:it|the|this|that)\b|"
    r"\bco[-\s]?sign(?:ing|ed)?\b",
    re.I,
)
# Deliberately excludes bare "title", "will", "trust", and "policy", each of
# which has a common harmless sense (job title, "I will sign up", trust as a
# feeling, company policy).
LEGAL_DOCUMENT = re.compile(
    r"\bpaperwork\b|\bdeed\b|\blease\b|\bcontract\b|\bagreement\b|"
    r"\bmortgage\b|\brefinanc\w*\b|\bloan\s+(?:documents?|papers?|agreement)\b|"
    r"\bpromissory\s+note\b|\bbill\s+of\s+sale\b|\bquitclaim\b|"
    r"\bpower\s+of\s+attorney\b|\bliving\s+(?:will|trust)\b|\bfamily\s+trust\b|"
    r"\b(?:my|his|her|their)\s+will\b|\bsettlement\b|"
    r"\bannuity\b|\binsurance\s+policy\b|\bclosing\s+(?:documents?|papers?)\b|"
    r"\b(?:car|house|home|property|vehicle|land)\s+title\b|"
    r"\btitle\s+(?:transfer|to\s+the)\b|\bnon[-\s]?disclosure\b|\bnda\b",
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
    r"\bconfirmed\b|\bsigned off\b|"
    # The prescriber making the change, not reviewing one the user proposed.
    # "My doctor doubled my dose at my appointment yesterday" is the clearest
    # possible case of professional_directed, and the review vocabulary above
    # covers only the reviewing direction, so without these verbs the dose
    # change reads as a deviation. Each needs an object pronoun ("my", "me")
    # so that general advice ("my doctor raised concerns") does not exempt.
    r"\b(?:doubl(?:e|ed)|rais(?:e|ed)|increas(?:e|ed)|lower(?:ed)?|reduc(?:e|ed)"
    r"|chang(?:e|ed)|adjust(?:ed)?|upp(?:ed)?|switch(?:ed)?|bump(?:ed)?)\s+"
    r"(?:my|me|him|her)\b|"
    r"\b(?:moved|put|started|has)\s+me\s+(?:up\s+|on\s+|back\s+)?\b|"
    r"\bprescrib(?:e|ed)\b",
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


# v1 scope is human health (docs/safety.md). A pet's joint supplement trips
# the same substance vocabulary, so the subject is checked before the
# medication signal is emitted.
PET_SUBJECT = re.compile(
    r"\bmy\s+(?:dog|cat|puppy|kitten|horse|pet|bird|rabbit|ferret)\b|"
    r"\b(?:the\s+)?(?:dog|cat)'?s\s+(?:dose|pill|medication|supplement|vet)\b",
    re.I,
)


def _max_amount(prompt):
    """Largest dollar figure in the prompt, or 0.0 if there is none."""
    best = 0.0
    for match in AMOUNT.finditer(prompt):
        try:
            value = float(match.group(1).replace(",", ""))
        except ValueError:
            continue
        if value > best:
            best = value
    return best


def _has_financial_transfer(prompt):
    if FINANCIAL_IRREVERSIBLE.search(prompt):
        return True
    if not FINANCIAL_TRANSFER_VERB.search(prompt):
        return False
    if OWN_ACCOUNT.search(prompt):
        return False
    return _max_amount(prompt) >= STAKES_AMOUNT_FLOOR


def _stakes_signals(prompt):
    signals = []
    if (MED_DOSE_DEVIATION.search(prompt) or MED_INTERACTION.search(prompt)) and not PET_SUBJECT.search(prompt):
        signals.append("medication_dosage")
    if _has_financial_transfer(prompt):
        signals.append("financial_transfer")
    if SIGNING_ACT.search(prompt) and LEGAL_DOCUMENT.search(prompt):
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
    r"\bbetween (?:us|you and me)\b|"
    # Steering the user away from verifying by voice, which is the same
    # move as secrecy and is how the family-impersonation scripts work.
    # "told me to call the number on the back of my card" (scam-neg-005)
    # is the opposite and does not match.
    r"\b(?:not\s+to|don'?t|can'?t|couldn'?t)\s+call\b|\bcan'?t\s+talk\b",
    re.I,
)

UNUSUAL_PAYMENT_CHANNEL = re.compile(
    r"\bgift cards?\b|"
    r"\b(?:google play|apple|itunes|amazon|steam)\s+(?:gift\s+)?cards?\b|"
    r"\bwire(?:d|ing)?\s+(?:him|her|them|it|to|\$)|\bwire transfer\b|"
    r"\bcrypto(?:currency)?\b|\bbitcoin\b|\bcash pickup\b|"
    r"\bmoneygram\b|\bwestern union\b|\bprepaid\s+card\b|"
    r"\bwire\s+(?:this|the|that|our|next)\b|"
    # Cash handed to a person who comes to collect. "cash pickup" above is
    # the wire-service product name; this is the courier variant, where the
    # user is told to withdraw cash and hand it over in person.
    r"\bcash\b[^.?!]{0,60}\b(?:courier|hand\s+it|messenger|someone\s+(?:will\s+)?"
    r"(?:come|stop)\s+by|driver\s+(?:will\s+)?(?:come|pick))\b|"
    r"\bwithdraw\b[^.?!]{0,40}\bin\s+cash\b|"
    # Money routed through a third party's account. Zelle and Venmo are not
    # unusual channels in themselves (they are the normal ones in
    # scam-neg-001, scam-neg-003, and scam-neg-008, and treating them as
    # suspicious would flag every family transfer), but sending to someone
    # other than the person asking is the mule step in the script.
    r"\b(?:zelle|zelled|venmo|cash app|wire|send|sent|transfer)\b[^.?!]{0,40}"
    r"\b(?:friend'?s|co-?worker'?s|someone else'?s|a different|a new)\s+"
    r"(?:account|zelle|venmo|card)\b",
    re.I,
)

# An institution a caller claims to represent. Impersonating one of these is
# the pretext in most of the archetypes; the user's own bank calling about a
# charge (scam-neg-005) is not here, and neither is a mailed IRS notice,
# which is why "bank" alone is excluded.
_INSTITUTION = (
    r"(?:irs|fbi|police|sheriff'?s?\s+office|medicare|medicaid|social security"
    r"|microsoft|apple\s+support|amazon|google|paypal|courthouse|county clerk"
    r"|water\s+company|electric\s+company|gas\s+company|utility\s+company"
    r"|publishers\s+clearing|lottery|immigration|ice)"
)
UNFAMILIAR_AUTHORITY = re.compile(
    r"\bsomeone\s+(?:called\s+)?saying\s+(?:they'?re|they were|he'?s|she'?s)\s+(?:from|with)\b|"
    # Claimed affiliation, in either order: "someone saying they're from the
    # IRS" and "a woman from the sheriff's office called".
    r"\b(?:say(?:s|ing)?|claim(?:s|ing)?|told me)\b[^.?!]{0,40}"
    r"\b(?:from|with)\s+(?:the\s+)?" + _INSTITUTION + r"\b|"
    r"\b(?:from|with)\s+(?:the\s+)?" + _INSTITUTION + r"\b[^.?!]{0,60}"
    r"\b(?:call(?:ed)?|phoned|knocked|emailed|texted|showed\s+up"
    # The tech-support script's opener: the contact is remote access, not a
    # call, so the contact verbs have to include it.
    r"|remot(?:e|ed|ing)\s+(?:in|into)|logged\s+into|took\s+control)\b|"
    # An agency credential that cannot actually be suspended. The phrase is
    # diagnostic of the government-impersonation robocall: real agencies do
    # not say it, so it does not need a second institution cue.
    r"\b(?:social\s+security|ssn|medicare)\s+(?:number\s+|card\s+)?"
    r"(?:was\s+|has\s+been\s+|is\s+|been\s+)?(?:suspended|frozen|deactivated|compromised)\b|"
    # A stranger at the door or on the phone pressing for money.
    r"\bknocked\s+on\s+(?:my|the)\s+door\b|"
    # "Claiming to be" is a standalone tell: it is how a user describes a
    # contact whose identity they already doubt, and no legitimate contact
    # gets narrated that way. This is the branch that catches bank
    # impersonation without putting bare "bank" in _INSTITUTION, which would
    # flag the user's real bank calling about a charge (scam-neg-005).
    r"\bclaim(?:s|ing|ed)?\s+to\s+be\b|\bsaid\s+(?:he|she|they)\s+(?:was|were)\s+from\b|"
    # An unsolicited prize. The ask that follows is always a fee, and the
    # "never entered" / sweepstakes framing is the user already noticing.
    r"\bwon\b[^.?!]{0,60}\b(?:never\s+entered|sweepstakes|lottery|prize\s+draw)\b|"
    r"\bsweepstakes\b[^.?!]{0,40}\bnever\s+entered\b|"
    # Met recently and online. "matched with" covers the dating-app opener
    # the romance script starts from.
    r"\bmet\s+(?:him\s+|her\s+|them\s+)?on\s+(?:facebook|instagram|tinder|match|a dating app|the internet|online)\b|"
    r"\bmatched\s+with\b|\bon\s+a\s+dating\s+app\b|\bjust\s+met\b|"
    # Contact arriving from an unverifiable identity: the family-impersonation
    # opener. "her usual number" (scam-neg-008) does not match.
    r"\b(?:a\s+)?(?:new|different|unknown)\s+number\b|"
    r"\bnumber\s+I\s+don'?t\s+recognize\b|"
    # Payment instructions redirected to an account that is new. This is the
    # business-email-compromise tell and it survives routine language, since
    # the script copies the routine amount on purpose.
    r"\bnew\s+account\b|"
    r"\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\b[^.?!]{0,40}"
    r"\bcall(?:ed)?\s+me\s+crying\b|"
    r"\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\b[^.?!]{0,60}"
    r"\b(?:in\s+jail|in\s+trouble|in\s+the\s+hospital|arrested|stuck\s+overseas)\b",
    re.I,
)

# --- Scam-narrative exemption -----------------------------------------
# known_recipient_routine_transfer. The old detector attempted no scam
# exemption and leaned on the 2-signal threshold, on the grounds that every
# exemption negative in the first batch landed under 2 signals. scam-neg-007
# (a known contractor's final $4,000 by wire today) is the counterexample:
# it carries exactly urgency + unusual_payment_channel, the same pair as
# scam-pos-007, so the threshold cannot separate them and the established
# payee has to be modeled directly.
ROUTINE_PAYEE = re.compile(
    r"\bsame\s+as\s+(?:i|we)\s+(?:usually|always|normally)\b|"
    r"\blike\s+(?:he|she|they)\s+(?:always|usually|normally)\s+does?\b|"
    r"\bas\s+usual\b|\bsame\s+account\b|\bsame\s+amount\b|"
    r"\bthe\s+same\s+(?:guy|person|company|supplier|contractor|plumber|number)\b|"
    r"\bsame\s+guy\b|\bevery\s+(?:month|quarter|week|year|payday)\b|"
    r"\bsame\s+as\s+every\s+\w+\b|\bquarterly\b|\bfor\s+the\s+past\s+\w+\s+years?\b|"
    r"\b(?:my|his|her|their|our)\s+usual\b|"
    r"\bregular\s+(?:supplier|payee|contractor|plumber|vendor|cleaner)\b|"
    # Established household payees. Paying your own rent or utility bill is
    # the textbook known recipient, and these are the shapes that otherwise
    # trip urgency plus a payment channel.
    r"\b(?:my|our)\s+(?:landlord|rent|mortgage\s+payment|utility\s+bill"
    r"|electric\s+bill|water\s+bill|phone\s+bill|insurance\s+premium)\b",
    re.I,
)
# professional_context: a bookkeeper, accountant, or business partner
# handling a routine business payment the user already expects. Guarded by
# NEW_COUNTERPARTY for the same reason as the routine exemption, which is
# what keeps scam-pos-006 ("my business partner's email says ... a new
# account") from exempting itself.
BUSINESS_PROFESSIONAL = re.compile(
    r"\b(?:bookkeeper|accountant|business partner|controller|cfo|comptroller"
    r"|office manager|treasurer|payroll)\b",
    re.I,
)
# Markers that the counterparty is not in fact established. These override
# the routine language, so "the same guy who" cannot exempt a prompt that
# also says "a new account".
NEW_COUNTERPARTY = re.compile(
    r"\bjust\s+met\b|\bnever\s+met\b|\bmatched\s+with\b|\bon\s+a\s+dating\s+app\b|"
    r"\bmet\s+(?:him\s+|her\s+|them\s+)?on\s+(?:facebook|instagram|tinder|match|the internet|online)\b|"
    r"\bnew\s+account\b|\b(?:new|different|unknown)\s+number\b|"
    r"\bnumber\s+I\s+don'?t\s+recognize\b|"
    r"\bsomeone\s+(?:called|knocked|emailed|texted)\b",
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


def _has_scam_exemption(prompt):
    """known_recipient_routine_transfer or professional_context. Both need
    the absence of a new-counterparty marker: the scam scripts copy routine
    language and routine amounts on purpose, so routine wording alone is not
    enough to clear a prompt."""
    if NEW_COUNTERPARTY.search(prompt):
        return False
    return bool(ROUTINE_PAYEE.search(prompt)) or bool(BUSINESS_PROFESSIONAL.search(prompt))


def predict(prompt, prior_turns):
    prompt = _normalize(prompt)
    stakes = _stakes_signals(prompt)
    stakes_hit = bool(stakes) and not _has_professional_review(prompt)

    scam = _scam_signals(prompt)
    scam_hit = len(scam) >= 2 and not _has_scam_exemption(prompt)

    signals = stakes + scam
    return {"should_flag": "yes" if (stakes_hit or scam_hit) else "no", "signals": signals}
