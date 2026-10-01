// Port of eval/detectors/v0_heuristic.py. Keep the two in sync: this is
// the detector actually shipped, that one is what the eval harness scores.
// Covers the H-layer cues (docs/taxonomy.md): 1, 4, 5, 6, 7, 8, 11, 12, plus
// phrase-only proxies for cues 2 and 3 (see CUE2_EMBEDDED_ASSUMPTION and
// CUE3_VERDICT below -- both are M-layer per the taxonomy, added here on
// empirical grounds).
window.HowToChat = window.HowToChat || {};

(function () {
  const SENTENCE_SPLIT = /(?<=[.?!])\s+/;
  const QUOTED_SPEECH = /"[^"]*"|\u201c[^\u201d]*\u201d/g;
  const HEDGE = /\bnot sure\b|\bnot certain\b|\bunsure\b|\bnot convinced\b/i;

  const SOFT_STANCE =
    /\bi (?:really )?(?:think|believe)\b|\bi (?:really |absolutely )?(?:like|love|dislike|hate) (?:this|it|the)\b|\bi'?m (?:pretty|fairly|mostly|reasonably) (?:sure|confident|convinced)\b/i;
  const HARD_STANCE = [
    /\bi know for a fact\b/i,
    /\bi'?m (?:totally |completely |absolutely )?(?:100%\s*)?(?:sure|convinced)\b/i,
    /,?\s*right\?/i,
    /isn'?t it(?:\s+true)?\??$/i,
    /\bobviously\b/i,
    /\bshould (?:cost|be) (?:around |about )?\$[\d,]+/i,
  ];

  // Cue 2 is taxonomy.md's M-layer only (the real cue is an unsupported
  // inference baked into the question; a regex can't judge the inference
  // itself). This matches only a handful of surface phrasings that reliably
  // carry it ("must mean", "must be -ing", "which X caused", "now that I'm
  // diagnosed/intolerant/allergic", "like mine did"). Added on empirical
  // grounds: 5/6 recall against data/seed/cue02.jsonl, 0 new false positives
  // across the eval corpus.
  const CUE2_EMBEDDED_ASSUMPTION =
    /\bmust\s+mean\b|\bmust\s+be\s+\w+ing\b|\b(?:which|what)\b.{0,30}\b(?:caused|causes|triggered|triggers)\b|\b(?:which|what)\b.{0,30}\b(?:gave|give|gives)\b\s+(?:this|that|it)\b|\bnow\s+that\s+(?:i'?m|i'?ve|i\s+am|i\s+have)\b.{0,30}\b(?:intolerant|allergic|diagnosed)\b|\blike\s+(?:mine|his|hers|theirs)\s+did\b/i;

  // Real cue 3 is a one-sided-conflict narrative plus a verdict request; a
  // regex can't judge one-sidedness. This matches only the verdict-request
  // phrase ("was I wrong for X", "am I the asshole"). Empirically clean:
  // 171/175 recall against the ELEPHANT AITA labels, 0 new false positives
  // across all should_flag=no records in the eval corpus.
  const CUE3_VERDICT =
    /\b(?:was|would|am)\s+i\s+(?:be\s+|being\s+)?(?:wrong|unreasonable|overreacting|over-reacting|the\s+asshole|an?\s+asshole|ungrateful|selfish|petty|in\s+the\s+wrong|out\s+of\s+line|weird)\b|\bis\s+it\s+wrong\s+(?:of\s+me|for\s+me|that\s+i|to)\b|\baita\b|\bwibta\b/i;

  const IDENTITY_TOPICS =
    "conservative|liberal|progressive|republican|democrat|libertarian|" +
    "socialist|feminist|christian|muslim|atheist|pro-life|pro-choice";
  // "as a conservative" phrasing is rare in practice; real self-identification
  // reads "I'm a lifelong conservative" or "I am a 55-year-old conservative
  // male", so the self-ID pattern looks for the identity word within a short,
  // clause-bounded window after "I'm"/"I am" rather than requiring "as a".
  const CUE6_AS_A = new RegExp(`\\bas an?\\s+(?:${IDENTITY_TOPICS})\\b`, "i");
  const CUE6_SELF_ID = new RegExp(`\\bi'?(?:m| am)\\b[^.,!?;]{0,40}?\\b(?:${IDENTITY_TOPICS})\\b`, "i");
  const CUE6_VOTED = /\bi'?(?:ve| have) always voted (?:republican|democrat)\b/i;

  function hasCue6(prompt) {
    return CUE6_AS_A.test(prompt) || CUE6_SELF_ID.test(prompt) || CUE6_VOTED.test(prompt);
  }

  const CUE4_ATTACHMENT =
    /\bi (?:wrote|made|created|built|designed) this\b|\bi'?m (?:really |so |quite )?proud of (?:this|it)\b|\bi love this (?:idea|poem|plan|design|essay|code|story|draft)\b/i;
  const CUE4_FEEDBACK_REQUEST =
    /\bthoughts\?|\bwhat do you think\b|\bfeedback\b|\bcritique\b|\breview (?:this|it)\b|\bhow (?:is|do you like) (?:it|this)\b/i;

  const CUE5_PUSHBACK = /\bare you sure\b|\bi (?:still )?(?:think|believe) (?:it'?s|it is|that'?s|that is)\b/i;
  const CUE5_JUSTIFICATION =
    /\bbecause\b|\bsince\b|\bhere'?s why\b|\bactually,?\b|\bi (?:checked|found|looked|read|verified)\b|\baccording to\b|\bthe reason is\b/i;

  const CUE7_AUTHORITY =
    /\beveryone knows\b|\bexperts agree\b|\bmy doctor said\b|\bmany people agree\b|\ball my friends (?:say|think|agree)\b|\bmost people (?:believe|think|say)\b/i;

  const CUE8_ANSWER_SPACE =
    /\byes or no\b|\bone word\b|\bin (?:one|a single) word\b|\banswer briefly\b|\bno caveats\b|\bdon'?t (?:lecture me|give me a lecture)\b/i;

  // Negative lookahead excludes "articles describing how [a mechanism
  // works]": a neutral, uncontested factual explanation, not a one-sided
  // claim (see data/seed/cue11.jsonl neg-008 vs pos-001, which otherwise
  // share identical surface phrasing).
  const CUE11_SOURCES =
    /\bhere(?:'s| is| are) (?:\d+|a|an|some|several|many|few|couple of|two|three|four|five|six)\s+(?:articles?|sources?|studies|links?|papers?)\b(?!\s+describing\s+how\b)/i;
  const CUE11_CONCLUSION_ASK = /\bsummarize\b|\bwhat (?:do|does) (?:they|this|these) (?:say|show|prove|confirm)\b/i;

  const CUE12_SUPPORTIVE_ROLE =
    /\bbe my hype ?man\b|\bbe my cheerleader\b|\bact as my (?:biggest supporter|cheerleader|hype ?man)\b|\bbe (?:encouraging|supportive)\b|\bonly (?:positive|supportive) feedback\b|\bdon'?t be (?:negative|critical|harsh)\b/i;

  const INVITES_DISAGREEMENT =
    /\bpush back\b|\bplay devil'?s advocate\b|\bbrutally honest\b|\b(?:strong(?:est)? )?argument (?:against|that (?:it'?s|they'?re|that'?s) wrong)\b|\bcounterargument\b|\bsteel ?man\b|\bprove me wrong\b|\bconvince me (?:otherwise|i'?m wrong)\b|\btell me if i'?m wrong\b|\bif (?:you think )?i'?m wrong\b|\bif you (?:see|spot|notice) a (?:real )?problem\b|\bplease say so\b/i;

  // factual_lookup exemption: a pure factual or how-to question, not a
  // leading framing. Checked only when cue 2 hasn't also fired, since an
  // embedded assumption inside a "how do I" question is still the cue it's
  // naming (data/seed/cue02.jsonl pos-004: "how do I find an advisor who
  // won't lose my money like mine did" is cue 2, not a neutral lookup).
  const FACTUAL_LOOKUP =
    /^\s*(?:how (?:do|can|should) i\b|how to\b)|\bwhat(?:'?s| is| are) (?:the )?(?:best|most) ways? to\b|\bwhat other (?:paths|options) are\b|\bmost (?:time[- ]efficient|efficient) way (?:of|to)\b|\bis it legal to\b|\bwhat(?:'?s| is) the (?:safe|correct|normal|typical|recommended)\b.{0,25}\b(?:temperature|dose|dosage|amount|level)\b|\bwhat(?:'?s| is) the (?:freezing|boiling) point\b|\bquick factual question\b|\bseparately,/i;

  function hasCue1(prompt) {
    const stripped = prompt.replace(QUOTED_SPEECH, "");
    for (const sentence of stripped.split(SENTENCE_SPLIT)) {
      if (SOFT_STANCE.test(sentence) && !HEDGE.test(sentence)) return true;
      if (HARD_STANCE.some((pattern) => pattern.test(sentence))) return true;
    }
    return false;
  }

  function hasCue5(prompt, priorTurns) {
    if (!priorTurns || priorTurns.length === 0) return false;
    return CUE5_PUSHBACK.test(prompt) && !CUE5_JUSTIFICATION.test(prompt);
  }

  function predict(prompt, priorTurns) {
    const cues = [];
    if (hasCue1(prompt)) cues.push(1);
    if (CUE2_EMBEDDED_ASSUMPTION.test(prompt)) cues.push(2);
    if (CUE3_VERDICT.test(prompt)) cues.push(3);
    if (CUE4_ATTACHMENT.test(prompt) && CUE4_FEEDBACK_REQUEST.test(prompt)) cues.push(4);
    if (hasCue5(prompt, priorTurns)) cues.push(5);
    if (hasCue6(prompt)) cues.push(6);
    if (CUE7_AUTHORITY.test(prompt)) cues.push(7);
    if (CUE8_ANSWER_SPACE.test(prompt)) cues.push(8);
    if (CUE11_SOURCES.test(prompt) && CUE11_CONCLUSION_ASK.test(prompt)) cues.push(11);
    if (CUE12_SUPPORTIVE_ROLE.test(prompt)) cues.push(12);

    if (cues.length && INVITES_DISAGREEMENT.test(prompt)) {
      return { shouldFlag: false, cues };
    }
    if (cues.length && !cues.includes(2) && FACTUAL_LOOKUP.test(prompt)) {
      return { shouldFlag: false, cues };
    }
    return { shouldFlag: cues.length > 0, cues };
  }

  // docs/taxonomy.md's per-cue tips, verbatim.
  const TIPS = {
    1: "This signals the answer you expect. Asking it as an open question tends to get a more balanced response.",
    2: "This assumes a cause or motive that isn't confirmed. Try describing what happened and asking what it might mean.",
    3: "The model only has your side. Try asking how the other person might see it.",
    4: "Saying it's yours tends to soften the feedback. Try sharing it without that, or ask for weaknesses directly.",
    5: "If you have a reason, include it. Otherwise ask the model to explain its answer instead of just switching.",
    6: "Mentioning your background can tilt the answer toward what people like you tend to think. Try asking without it.",
    7: "Citing who agrees can make the model go along with it. Try asking whether the claim holds up on its own.",
    8: "Short-answer limits leave no room for caveats. Consider allowing a sentence of context.",
    11: "The model will mostly work from what you gave it. Consider asking what evidence points the other way.",
    12: "Asking for encouragement will get encouragement. If you need an honest read, ask for that separately.",
  };

  HowToChat.detector = { predict, tips: TIPS };
})();
