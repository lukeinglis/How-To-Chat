// Port of eval/detectors/v0_heuristic_safety.py. Keep the two in sync: this
// is the detector actually shipped, that one is what the eval harness
// scores. Separate from detector.js because the safety flags (docs/safety.md)
// use their own rule and vocab, not the 12 framing cues.
//
// This file drives the red badge. Read the Python module's docstring before
// changing anything here; it carries the measurement history and the reason
// the recall number is what it is. Short version: the five defects that the
// 2026-10-08 probe records exposed are fixed, precision is 100% on two
// independently written held-out sets, and recall on unseen phrasing is
// about 38%. The badge is now quiet rather than wrong, which is the right
// trade for a red badge, but do not read the corpus's 100% recall as real.
window.HowToChat = window.HowToChat || {};

(function () {
  const SENTENCE_SPLIT = /(?<=[.?!])\s+/;

  // --- Stakes signals ---------------------------------------------------

  // Named substances, shared by MED_DOSE_DEVIATION and MED_INTERACTION.
  // MED_INTERACTION previously used a bare [a-z-]+ here, one word wide,
  // which made it simultaneously too broad ("starting a daily walk too" read
  // as a drug interaction) and too narrow ("fish oil capsule" did not
  // match). The generic dose-form nouns at the end carry the "this is a
  // substance" information when the drug is not named.
  const SUBSTANCE =
    "(?:aspirin|ibuprofen|advil|motrin|tylenol|acetaminophen|naproxen|aleve" +
    "|warfarin|coumadin|eliquis|xarelto|metformin|insulin|statin|lipitor" +
    "|lisinopril|metoprolol|amlodipine|levothyroxine|prednisone|gabapentin" +
    "|sertraline|zoloft|lexapro|prozac|xanax|ativan|ambien|adderall" +
    "|melatonin|turmeric|curcumin|fish\\s+oil|omega[-\\s]?3|st\\.?\\s+john'?s\\s+wort" +
    "|ginkgo|ginseng|echinacea|magnesium|potassium|calcium|iron|zinc|cbd" +
    "|vitamin\\s+[a-z0-9]+|multivitamin|probiotic|creatine|collagen" +
    "|ashwagandha|valerian|biotin|elderberry|saw\\s+palmetto" +
    "|milk\\s+thistle|glucosamine|coq10|niacin|folic\\s+acid|b12" +
    "|amoxicillin|azithromycin|penicillin|cephalexin|doxycycline|ciprofloxacin" +
    "|hydrocodone|oxycodone|tramadol|hydrochlorothiazide|furosemide|omeprazole" +
    "|supplement|capsule|tablet|pill|medication|medicine|herb|extract" +
    "|tincture|drops|syrup|powder|gummy|gummies|patch|inhaler)";

  const MED_DOSE_DEVIATION = new RegExp(
    // Past tense is required, not optional: docs/safety.md says reporting the
    // action as already taken does not exempt it, so "doubled up" has to
    // match wherever "double up" does.
    "\\bdoubl(?:e|ed|ing)\\s+up\\b|" +
    "\\b(?:take|taking|took)\\s+(?:a\\s+)?(?:double|triple|extra|two|three)\\b.{0,30}\\b" +
    "(?:catch\\s*(?:back\\s+)?up|tonight|dose|pill)\\b|" +
    "\\bskip(?:ping)?\\s+(?:a|my|the)\\s+(?:dose|pill)\\b|" +
    "\\b(?:take|taking|took)\\s+(?:an?\\s+)?extra\\s+(?:one|dose|pill|tablet|capsule)\\b|" +
    "\\b(?:took|taking|take)\\s+a\\s+second\\s+[a-z\\-]+\\b[^.?!]{0,40}" +
    "\\b(?:after|hour|later|same day)\\b|" +
    "\\bdoubl(?:e|ing|ed)\\s+(?:my|the|his|her)\\s+[a-z\\-]+\\b|" +
    // Stretching a supply: same family as splitting pills.
    "\\bevery\\s+other\\s+day\\b[^.?!]{0,40}\\b(?:stretch|last|ration|save)\\b|" +
    "\\b(?:stretch|ration)\\s+(?:it|them|my)\\b[^.?!]{0,30}\\b(?:out|longer|until)\\b|" +
    // Altering the dose form, same family as splitting.
    "\\b(?:crush|crushing|chew|chewing|open|opening|dissolve|dissolving)\\s+" +
    "(?:my|the|these|an?)\\s+(?:extended[-\\s]release\\s+|er\\s+|xr\\s+|time[-\\s]release\\s+)?" +
    "(?:pill|tablet|capsule|dose)\\b|" +
    // Stopping without guidance.
    "\\b(?:stopped|stopping|quit|quitting)\\b[^.?!]{0,40}\\bcold\\s+turkey\\b|" +
    // A dose stated in units, taken in place of the prescribed one. The
    // "instead" is what makes it a deviation: without it, "I take 20mg" is
    // just the user reporting their prescription.
    "\\b(?:take|taking|took)\\s+(?:the\\s+)?\\d+\\s*(?:mg|mcg|ml|iu|g)\\b[^.?!]{0,40}\\binstead\\b|" +
    // Splitting or stretching a prescription.
    "\\b(?:cut|cutting|split|splitting|break|breaking)\\s+(?:them|it|the|my|these)\\b" +
    "[^.?!]{0,20}\\bin\\s+half\\b|" +
    "\\bhalf\\s+(?:a|my|the)\\s+(?:pill|tablet|dose)\\b|" +
    // Taking medication prescribed to someone else.
    "\\b(?:my|a)\\s+(?:neighbor|friend|sister|brother|husband|wife|mother|father" +
    "|mom|dad|roommate|co-?worker|son|daughter)\\b[^.?!]{0,60}" +
    "\\bsame\\s+(?:prescription|medication|pills?|dosage)\\b|" +
    "\\b(?:use|used|using|take|took|taking|borrow|borrowed|borrowing)\\s+" +
    "(?:a few of|some of|one of)\\s+(?:hers|his|theirs)\\b|" +
    // Leftover or expired prescriptions, same family as taking someone
    // else's: the dose is real but nobody current is directing it.
    "\\b(?:left\\s*over|leftover|old|expired)\\s+" +
    "(?:[a-z\\-]+\\s+){0,2}?(?:pills?|antibiotics?|prescription|medication|tablets?|capsules?)\\b|" +
    "\\b(?:pills?|antibiotics?|prescription|medication)\\b[^.?!]{0,30}" +
    "\\bleft\\s*over\\s+from\\b|" +
    "\\b" + SUBSTANCE + "\\b[^.?!]{0,30}\\bleft\\s*over\\b|" +
    // Taking a dose more often than the label says. Same "instead" shape as
    // the milligram branch.
    "\\bevery\\s+(?:\\d+|two|three|four|six|eight|twelve)\\s*(?:hours?|hrs?)?\\s*\\binstead\\b|" +
    "\\btaking\\s+(?:them|it)\\s+every\\s+(?:\\d+|two|three|four|six|eight|twelve)\\b" +
    "[^.?!]{0,30}\\binstead\\b|" +
    // A label instruction the user is about to override. The defiance marker
    // is required: "the bottle says don't drink with this" on its own is a
    // user reading their label correctly, which is not a deviation.
    "\\bsays?\\b[^.?!]{0,60}\\b(?:don'?t|do not|not to|avoid)\\s+" +
    "(?:drink|mix|take|combine|have)\\b[^.?!]{0,80}" +
    "\\b(?:but|anyway|won'?t matter|just this once|one\\s+(?:glass|drink|time))\\b",
    "i"
  );

  const MED_INTERACTION = new RegExp(
    "\\bstart(?:ing)?\\s+(?:to\\s+take\\s+|taking\\s+)?(?:a\\s+|the\\s+|some\\s+)?" +
    "(?:daily\\s+|nightly\\s+|new\\s+|low[-\\s]dose\\s+)?" +
    "(?:[a-z\\-]+\\s+){0,3}?" + SUBSTANCE + "\\b[^.?!]{0,30}" +
    "\\b(?:too|alongside|along with|together with|as well|on top of)\\b",
    "i"
  );

  // Dollar amounts, for the stakes floor below.
  const AMOUNT = /\$\s?([\d,]+(?:\.\d{2})?)/g;

  // The stakes flag's money floor. docs/safety.md defines the flag as an
  // action with "hard-to-reverse real-world consequences", and the old
  // pattern had no notion of amount at all, so "send $5 to my sister on
  // Venmo to split a coffee" showed the red badge. $1,000 is a judgment call
  // with no corpus basis; see the Python module for the reasoning. The scam
  // flag deliberately has no floor: a $300 gift card demand is the archetype.
  const STAKES_AMOUNT_FLOOR = 1000.0;

  // Verb-adjacent transfers. Kept adjacent to the dollar figure on purpose:
  // the looser "$4,000 by wire transfer" shape appears in scam-neg-007, a
  // known contractor's final payment, where a stakes flag would be wrong.
  const FINANCIAL_TRANSFER_VERB =
    /\b(?:wire|wiring|transfer(?:ring)?|mov(?:e|ing)|send(?:ing)?|pay(?:ing)?)\s+(?:[a-z']+\s+){0,3}?\$[\d,]+/i;
  // Actions that are consequential regardless of the figure attached, so they
  // skip the floor.
  const FINANCIAL_IRREVERSIBLE =
    /\bcash(?:ing)?\s+out\s+(?:my\s+)?(?:entire\s+)?(?:401k|401\(k\)|ira|retirement|pension)\b|\bcash\s+advance\b|\bborrow(?:ing)?\s+against\b|\b(?:home\s+equity|second\s+mortgage|reverse\s+mortgage)\b|\bliquidat(?:e|ing)\s+(?:my\s+)?(?:401k|ira|retirement|investments?|portfolio)\b|\b(?:tak(?:e|ing)|took|pull(?:ing|ed)?|withdraw(?:ing|n)?|drew)\b[^.?!]{0,30}\b(?:out\s+of|from)\s+(?:my\s+)?(?:401k|401\(k\)|ira|roth|retirement|pension)\b/i;
  // The user's own accounts. Moving money between them is not a stakes event
  // at any size, so this vetoes the verb-adjacent branch. The possessive is
  // required: "send $8,000 to my new financial guy to put into savings for
  // me" is not an own-account move.
  const OWN_ACCOUNT =
    /\b(?:to|into)\s+(?:my|our)\s+(?:own\s+)?(?:savings|checking|emergency\s+fund|money\s+market|brokerage)\b|\bfrom\s+(?:my\s+|our\s+)?(?:checking|savings)\s+(?:in)?to\s+(?:my\s+|our\s+)?(?:checking|savings)\b|\bbetween\s+(?:my|our)\s+(?:own\s+)?accounts\b/i;

  // Signing splits into the act and the document. The old pattern had only
  // the act, so a bare "sign it" fired with no idea what was being signed,
  // and a house deed (stk-pos-009) and a school permission slip
  // (stk-neg-009) gave identical output. Both are now required.
  //
  // "sign up"/"signed up for" is enrolling, not executing a document, and is
  // excluded: "I signed up for a two-year phone contract" is not a stakes
  // event.
  const SIGNING_ACT =
    /\bsign(?:ing|ed)?\b(?!\s+up\b)|\b(?:get|got)\s+it\s+signed\b|\bsignature\b|\binitial(?:ing|ed)?\s+(?:it|the|this|that)\b|\bco[-\s]?sign(?:ing|ed)?\b/i;
  // Deliberately excludes bare "title", "will", "trust", and "policy", each
  // of which has a common harmless sense (job title, "I will sign up", trust
  // as a feeling, company policy).
  const LEGAL_DOCUMENT =
    /\bpaperwork\b|\bdeed\b|\blease\b|\bcontract\b|\bagreement\b|\bmortgage\b|\brefinanc\w*\b|\bloan\s+(?:documents?|papers?|agreement)\b|\bpromissory\s+note\b|\bbill\s+of\s+sale\b|\bquitclaim\b|\bpower\s+of\s+attorney\b|\bliving\s+(?:will|trust)\b|\bfamily\s+trust\b|\b(?:my|his|her|their)\s+will\b|\bsettlement\b|\bannuity\b|\binsurance\s+policy\b|\bclosing\s+(?:documents?|papers?)\b|\b(?:car|house|home|property|vehicle|land)\s+title\b|\btitle\s+(?:transfer|to\s+the)\b|\bnon[-\s]?disclosure\b|\bnda\b/i;

  const PROFESSIONAL =
    /\b(?:doctor|nurse|physician|cardiologist|pharmacist|financial advisor|advisor|accountant|attorney|lawyer|bank(?:er)?)\b/i;
  // Includes the prescriber *making* a change, not just reviewing one the
  // user proposed. "My doctor doubled my dose at my appointment yesterday" is
  // the clearest possible professional_directed case, and without those verbs
  // the dose change reads as a deviation. Each needs an object pronoun so
  // that general advice ("my doctor raised concerns") does not exempt.
  const REVIEW_LANGUAGE =
    /\balready\b|\bwalked me through\b|\bwent through\b|\bline by line\b|\bsaid it'?s fine\b|\bthinks? it makes sense\b|\bagreed\b|\bran the (?:full )?numbers\b|\bmonitoring\b|\bgiven my (?:specific )?numbers\b|\bconfirmed\b|\bsigned off\b|\b(?:doubl(?:e|ed)|rais(?:e|ed)|increas(?:e|ed)|lower(?:ed)?|reduc(?:e|ed)|chang(?:e|ed)|adjust(?:ed)?|upp(?:ed)?|switch(?:ed)?|bump(?:ed)?)\s+(?:my|me|him|her)\b|\b(?:moved|put|started|has)\s+me\s+(?:up\s+|on\s+|back\s+)?\b|\bprescrib(?:e|ed)\b/i;

  // v1 scope is human health (docs/safety.md). A pet's joint supplement trips
  // the same substance vocabulary, so the subject is checked before the
  // medication signal is emitted.
  const PET_SUBJECT =
    /\bmy\s+(?:dog|cat|puppy|kitten|horse|pet|bird|rabbit|ferret)\b|\b(?:the\s+)?(?:dog|cat)'?s\s+(?:dose|pill|medication|supplement|vet)\b/i;

  // professional_directed proxy: a professional noun and review language in
  // the same sentence, or that sentence plus the next one.
  function hasProfessionalReview(prompt) {
    const sentences = prompt.split(SENTENCE_SPLIT);
    for (let i = 0; i < sentences.length; i++) {
      if (!PROFESSIONAL.test(sentences[i])) continue;
      const window_ = sentences.slice(i, i + 2).join(" ");
      if (REVIEW_LANGUAGE.test(window_)) return true;
    }
    return false;
  }

  // Largest dollar figure in the prompt, or 0 if there is none.
  function maxAmount(prompt) {
    let best = 0;
    AMOUNT.lastIndex = 0;
    let match;
    while ((match = AMOUNT.exec(prompt)) !== null) {
      const value = parseFloat(match[1].replace(/,/g, ""));
      if (!isNaN(value) && value > best) best = value;
    }
    return best;
  }

  function hasFinancialTransfer(prompt) {
    if (FINANCIAL_IRREVERSIBLE.test(prompt)) return true;
    if (!FINANCIAL_TRANSFER_VERB.test(prompt)) return false;
    if (OWN_ACCOUNT.test(prompt)) return false;
    return maxAmount(prompt) >= STAKES_AMOUNT_FLOOR;
  }

  function stakesSignals(prompt) {
    const signals = [];
    if (
      (MED_DOSE_DEVIATION.test(prompt) || MED_INTERACTION.test(prompt)) &&
      !PET_SUBJECT.test(prompt)
    ) {
      signals.push("medication_dosage");
    }
    if (hasFinancialTransfer(prompt)) signals.push("financial_transfer");
    if (SIGNING_ACT.test(prompt) && LEGAL_DOCUMENT.test(prompt)) {
      signals.push("legal_signing");
    }
    return signals;
  }

  // --- Scam-narrative signals --------------------------------------------

  const URGENCY =
    /\bright now\b|\bright away\b|\bwithin the hour\b|\burgent(?:ly)?\b|\btoday\b|\bimmediately\b|\bas soon as possible\b|\basap\b/i;

  // The last two branches cover steering the user away from verifying by
  // voice, which is the same move as secrecy and is how the family
  // impersonation scripts work. "told me to call the number on the back of
  // my card" (scam-neg-005) is the opposite and does not match.
  const SECRECY =
    /\bnot\s+(?:to\s+)?(?:tell|mention)\b|\bdon'?t\s+(?:tell|mention)\b|\bkeep\s+(?:this|it)\s+(?:between us|a secret|secret|quiet)\b|\bbetween (?:us|you and me)\b|\b(?:not\s+to|don'?t|can'?t|couldn'?t)\s+call\b|\bcan'?t\s+talk\b/i;

  // Zelle and Venmo are not unusual channels in themselves (they are the
  // normal ones in scam-neg-001, -003, and -008, and treating them as
  // suspicious would flag every family transfer), but sending to someone
  // other than the person asking is the mule step in the script.
  const UNUSUAL_PAYMENT_CHANNEL =
    /\bgift cards?\b|\b(?:google play|apple|itunes|amazon|steam)\s+(?:gift\s+)?cards?\b|\bwire(?:d|ing)?\s+(?:him|her|them|it|to|\$)|\bwire transfer\b|\bcrypto(?:currency)?\b|\bbitcoin\b|\bcash pickup\b|\bmoneygram\b|\bwestern union\b|\bprepaid\s+card\b|\bwire\s+(?:this|the|that|our|next)\b|\bcash\b[^.?!]{0,60}\b(?:courier|hand\s+it|messenger|someone\s+(?:will\s+)?(?:come|stop)\s+by|driver\s+(?:will\s+)?(?:come|pick))\b|\bwithdraw\b[^.?!]{0,40}\bin\s+cash\b|\b(?:zelle|zelled|venmo|cash app|wire|send|sent|transfer)\b[^.?!]{0,40}\b(?:friend'?s|co-?worker'?s|someone else'?s|a different|a new)\s+(?:account|zelle|venmo|card)\b/i;

  // An institution a caller claims to represent. Impersonating one of these
  // is the pretext in most of the archetypes; the user's own bank calling
  // about a charge (scam-neg-005) is not here, which is why "bank" alone is
  // excluded.
  const INSTITUTION =
    "(?:irs|fbi|police|sheriff'?s?\\s+office|medicare|medicaid|social security" +
    "|microsoft|apple\\s+support|amazon|google|paypal|courthouse|county clerk" +
    "|water\\s+company|electric\\s+company|gas\\s+company|utility\\s+company" +
    "|publishers\\s+clearing|lottery|immigration|ice)";

  const UNFAMILIAR_AUTHORITY = new RegExp(
    "\\bsomeone\\s+(?:called\\s+)?saying\\s+(?:they'?re|they were|he'?s|she'?s)\\s+(?:from|with)\\b|" +
    // Claimed affiliation, in either order: "someone saying they're from the
    // IRS" and "a woman from the sheriff's office called".
    "\\b(?:say(?:s|ing)?|claim(?:s|ing)?|told me)\\b[^.?!]{0,40}" +
    "\\b(?:from|with)\\s+(?:the\\s+)?" + INSTITUTION + "\\b|" +
    "\\b(?:from|with)\\s+(?:the\\s+)?" + INSTITUTION + "\\b[^.?!]{0,60}" +
    // The tech-support script's opener is remote access, not a call, so the
    // contact verbs have to include it.
    "\\b(?:call(?:ed)?|phoned|knocked|emailed|texted|showed\\s+up" +
    "|remot(?:e|ed|ing)\\s+(?:in|into)|logged\\s+into|took\\s+control)\\b|" +
    // An agency credential that cannot actually be suspended. The phrase is
    // diagnostic of the government-impersonation robocall.
    "\\b(?:social\\s+security|ssn|medicare)\\s+(?:number\\s+|card\\s+)?" +
    "(?:was\\s+|has\\s+been\\s+|is\\s+|been\\s+)?(?:suspended|frozen|deactivated|compromised)\\b|" +
    // A stranger at the door or on the phone pressing for money.
    "\\bknocked\\s+on\\s+(?:my|the)\\s+door\\b|" +
    // "Claiming to be" is a standalone tell: it is how a user describes a
    // contact whose identity they already doubt. This catches bank
    // impersonation without putting bare "bank" in INSTITUTION.
    "\\bclaim(?:s|ing|ed)?\\s+to\\s+be\\b|\\bsaid\\s+(?:he|she|they)\\s+(?:was|were)\\s+from\\b|" +
    // An unsolicited prize. The ask that follows is always a fee.
    "\\bwon\\b[^.?!]{0,60}\\b(?:never\\s+entered|sweepstakes|lottery|prize\\s+draw)\\b|" +
    "\\bsweepstakes\\b[^.?!]{0,40}\\bnever\\s+entered\\b|" +
    // Met recently and online. "matched with" covers the dating-app opener
    // the romance script starts from.
    "\\bmet\\s+(?:him\\s+|her\\s+|them\\s+)?on\\s+(?:facebook|instagram|tinder|match|a dating app|the internet|online)\\b|" +
    "\\bmatched\\s+with\\b|\\bon\\s+a\\s+dating\\s+app\\b|\\bjust\\s+met\\b|" +
    // Contact arriving from an unverifiable identity: the family
    // impersonation opener. "her usual number" (scam-neg-008) does not match.
    "\\b(?:a\\s+)?(?:new|different|unknown)\\s+number\\b|" +
    "\\bnumber\\s+I\\s+don'?t\\s+recognize\\b|" +
    // Payment instructions redirected to an account that is new. This is the
    // business-email-compromise tell and it survives routine language, since
    // the script copies the routine amount on purpose.
    "\\bnew\\s+account\\b|" +
    "\\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\\b[^.?!]{0,40}" +
    "\\bcall(?:ed)?\\s+me\\s+crying\\b|" +
    "\\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\\b[^.?!]{0,60}" +
    "\\b(?:in\\s+jail|in\\s+trouble|in\\s+the\\s+hospital|arrested|stuck\\s+overseas)\\b",
    "i"
  );

  // --- Scam-narrative exemption -----------------------------------------
  // known_recipient_routine_transfer. The old detector attempted no scam
  // exemption and leaned on the 2-signal threshold, on the grounds that every
  // exemption negative in the first batch landed under 2 signals.
  // scam-neg-007 (a known contractor's final $4,000 by wire today) is the
  // counterexample: it carries exactly urgency + unusual_payment_channel, the
  // same pair as scam-pos-007, so the threshold cannot separate them.
  const ROUTINE_PAYEE =
    /\bsame\s+as\s+(?:i|we)\s+(?:usually|always|normally)\b|\blike\s+(?:he|she|they)\s+(?:always|usually|normally)\s+does?\b|\bas\s+usual\b|\bsame\s+account\b|\bsame\s+amount\b|\bthe\s+same\s+(?:guy|person|company|supplier|contractor|plumber|number)\b|\bsame\s+guy\b|\bevery\s+(?:month|quarter|week|year|payday)\b|\bsame\s+as\s+every\s+\w+\b|\bquarterly\b|\bfor\s+the\s+past\s+\w+\s+years?\b|\b(?:my|his|her|their|our)\s+usual\b|\bregular\s+(?:supplier|payee|contractor|plumber|vendor|cleaner)\b|\b(?:my|our)\s+(?:landlord|rent|mortgage\s+payment|utility\s+bill|electric\s+bill|water\s+bill|phone\s+bill|insurance\s+premium)\b/i;
  // professional_context: a bookkeeper, accountant, or business partner
  // handling a routine business payment the user already expects.
  const BUSINESS_PROFESSIONAL =
    /\b(?:bookkeeper|accountant|business partner|controller|cfo|comptroller|office manager|treasurer|payroll)\b/i;
  // Markers that the counterparty is not in fact established. These override
  // the routine language, so "the same guy who" cannot exempt a prompt that
  // also says "a new account". This is what keeps scam-pos-006 ("my business
  // partner's email says ... a new account") from exempting itself.
  const NEW_COUNTERPARTY =
    /\bjust\s+met\b|\bnever\s+met\b|\bmatched\s+with\b|\bon\s+a\s+dating\s+app\b|\bmet\s+(?:him\s+|her\s+|them\s+)?on\s+(?:facebook|instagram|tinder|match|the internet|online)\b|\bnew\s+account\b|\b(?:new|different|unknown)\s+number\b|\bnumber\s+I\s+don'?t\s+recognize\b|\bsomeone\s+(?:called|knocked|emailed|texted)\b/i;

  function scamSignals(prompt) {
    const signals = [];
    if (URGENCY.test(prompt)) signals.push("urgency");
    if (SECRECY.test(prompt)) signals.push("secrecy");
    if (UNUSUAL_PAYMENT_CHANNEL.test(prompt)) signals.push("unusual_payment_channel");
    if (UNFAMILIAR_AUTHORITY.test(prompt)) signals.push("unfamiliar_relative_or_authority");
    return signals;
  }

  // known_recipient_routine_transfer or professional_context. Both need the
  // absence of a new-counterparty marker: the scam scripts copy routine
  // language and routine amounts on purpose, so routine wording alone is not
  // enough to clear a prompt.
  function hasScamExemption(prompt) {
    if (NEW_COUNTERPARTY.test(prompt)) return false;
    return ROUTINE_PAYEE.test(prompt) || BUSINESS_PROFESSIONAL.test(prompt);
  }

  // Fold the curly apostrophe onto the straight one, as detector.js does.
  // Patterns here are written with the straight one ("don't tell",
  // "they're from the bank"), which are scam-narrative phrases a user is
  // likely to type or paste. This detector drives the red badge, so a
  // silent miss matters more here than on the framing cues.
  function normalize(text) {
    return text.replace(/\u2019/g, "'").replace(/\u2018/g, "'");
  }

  function predict(rawPrompt) {
    const prompt = normalize(rawPrompt);
    const stakes = stakesSignals(prompt);
    const stakesHit = stakes.length > 0 && !hasProfessionalReview(prompt);

    const scam = scamSignals(prompt);
    const scamHit = scam.length >= 2 && !hasScamExemption(prompt);

    let flagType = null;
    if (stakesHit) flagType = "stakes";
    else if (scamHit) flagType = "scam_narrative";

    return {
      shouldFlag: stakesHit || scamHit,
      signals: stakes.concat(scam),
      flagType,
    };
  }

  // docs/safety.md's tips, verbatim. Stakes picks health vs. money copy by
  // which signal fired; scam-narrative has one tip regardless of domain.
  const STAKES_TIPS = {
    medication_dosage: "Confirm this with a pharmacist or your doctor before taking it.",
    financial_transfer: "Confirm this with your bank using a number you already have, before sending anything.",
    legal_signing: "Confirm this with your bank using a number you already have, before sending anything.",
  };
  const SCAM_TIP = "Contact them directly using a number you already have, not one they gave you.";

  function tipsFor(result) {
    if (!result.shouldFlag) return [];
    if (result.flagType === "stakes") {
      const seen = new Set();
      for (const signal of result.signals) {
        if (STAKES_TIPS[signal]) seen.add(STAKES_TIPS[signal]);
      }
      return Array.from(seen);
    }
    if (result.flagType === "scam_narrative") return [SCAM_TIP];
    return [];
  }

  HowToChat.safetyDetector = { predict, tipsFor };
})();
