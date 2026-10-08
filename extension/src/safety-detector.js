// Port of eval/detectors/v0_heuristic_safety.py. Keep the two in sync: this
// is the detector actually shipped, that one is what the eval harness
// scores. Separate from detector.js because the safety flags (docs/safety.md)
// use their own rule and vocab, not the 12 framing cues.
//
// This file drives the red badge and it is currently below the project's 90%
// precision bar: 77.8% precision and 82.4% recall over 35 records. Read the
// Python module's docstring before changing anything here; it lists five
// known defects, each pinned to a record. The one most likely to be seen by a
// real user is that any "send $N" fires the stakes flag regardless of amount
// or recipient, so "send $5 to my sister on Venmo" shows the badge.
window.HowToChat = window.HowToChat || {};

(function () {
  const SENTENCE_SPLIT = /(?<=[.?!])\s+/;

  // --- Stakes signals ---------------------------------------------------

  const MED_DOSE_DEVIATION =
    /\bdoubl(?:e|ing)\s+up\b|\b(?:take|taking|took)\s+(?:a\s+)?(?:double|triple|extra|two|three)\b.{0,30}\b(?:catch\s*(?:back\s+)?up|tonight|dose|pill)\b|\bskip(?:ping)?\s+(?:a|my|the)\s+(?:dose|pill)\b/i;
  const MED_INTERACTION =
    /\bstart(?:ing)?\s+(?:taking\s+)?(?:a\s+)?(?:daily\s+)?[a-z\-]+\s+(?:too\b|alongside\b|along with\b|together with\b|as well\b)/i;

  const FINANCIAL_TRANSFER =
    /\b(?:wire|wiring|transfer(?:ring)?|mov(?:e|ing)|send(?:ing)?)\s+\$[\d,]+|\bcash(?:ing)?\s+out\s+(?:my\s+)?(?:entire\s+)?(?:401k|401\(k\)|ira|retirement)\b/i;

  const LEGAL_SIGNING =
    /\bsign(?:ing)?\s+(?:the\s+)?paperwork\b|\b(?:get|got)\s+it\s+signed\b|\bsign\s+it\b|\breverse\s+mortgage\b/i;

  const PROFESSIONAL =
    /\b(?:doctor|nurse|physician|cardiologist|pharmacist|financial advisor|advisor|accountant|attorney|lawyer|bank(?:er)?)\b/i;
  const REVIEW_LANGUAGE =
    /\balready\b|\bwalked me through\b|\bwent through\b|\bline by line\b|\bsaid it'?s fine\b|\bthinks? it makes sense\b|\bagreed\b|\bran the (?:full )?numbers\b|\bmonitoring\b|\bgiven my (?:specific )?numbers\b|\bconfirmed\b|\bsigned off\b/i;

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

  function stakesSignals(prompt) {
    const signals = [];
    if (MED_DOSE_DEVIATION.test(prompt) || MED_INTERACTION.test(prompt)) signals.push("medication_dosage");
    if (FINANCIAL_TRANSFER.test(prompt)) signals.push("financial_transfer");
    if (LEGAL_SIGNING.test(prompt)) signals.push("legal_signing");
    return signals;
  }

  // --- Scam-narrative signals --------------------------------------------

  const URGENCY =
    /\bright now\b|\bright away\b|\bwithin the hour\b|\burgent(?:ly)?\b|\btoday\b|\bimmediately\b|\bas soon as possible\b|\basap\b/i;

  const SECRECY =
    /\bnot\s+(?:to\s+)?(?:tell|mention)\b|\bdon'?t\s+(?:tell|mention)\b|\bkeep\s+(?:this|it)\s+(?:between us|a secret|secret|quiet)\b|\bbetween (?:us|you and me)\b/i;

  const UNUSUAL_PAYMENT_CHANNEL =
    /\bgift cards?\b|\b(?:google play|apple|itunes|amazon|steam)\s+(?:gift\s+)?cards?\b|\bwire(?:d|ing)?\s+(?:him|her|them|it|to|\$)|\bwire transfer\b|\bcrypto(?:currency)?\b|\bbitcoin\b|\bcash pickup\b|\bmoneygram\b|\bwestern union\b/i;

  const UNFAMILIAR_AUTHORITY =
    /\bsomeone\s+(?:called\s+)?saying\s+(?:they'?re|they were|he'?s|she'?s)\s+(?:from|with)\b|\bmet\s+(?:him\s+|her\s+|them\s+)?on\s+(?:facebook|instagram|tinder|match|the internet|online)\b|\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\b[^.?!]{0,40}\bcall(?:ed)?\s+me\s+crying\b|\b(?:grandson|granddaughter|nephew|niece|son|daughter|grandchild)\b[^.?!]{0,60}\b(?:in\s+jail|in\s+trouble|in\s+the\s+hospital|arrested|stuck\s+overseas)\b/i;

  function scamSignals(prompt) {
    const signals = [];
    if (URGENCY.test(prompt)) signals.push("urgency");
    if (SECRECY.test(prompt)) signals.push("secrecy");
    if (UNUSUAL_PAYMENT_CHANNEL.test(prompt)) signals.push("unusual_payment_channel");
    if (UNFAMILIAR_AUTHORITY.test(prompt)) signals.push("unfamiliar_relative_or_authority");
    return signals;
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
    const scamHit = scam.length >= 2;

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
