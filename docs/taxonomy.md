# Taxonomy

## The flag rule

> Flag when the prompt signals the answer the user wants **to the question they are actually asking**, and an agreeable answer would skip an evaluation the user needs.

Two tests follow from it:

1. **Relevance (at-issueness).** A belief stated as background to a different question does not qualify. "Renting is throwing money away. How much should I save for a down payment?" is not flagged, because the belief doesn't distort the savings answer.
2. **Consequence.** If agreeing would give the right answer anyway, don't flag. "I shoot Nikon and think it's the best. Which body should I get?" is not flagged, because owning Nikon lenses makes a Nikon body correct regardless of the belief.

Every cue below is applied through this rule. A cue being present is necessary but not sufficient.

## Cues

Evidence: **Strong** = directly measured in a controlled study. **Moderate** = measured, but in a nearby form. **Extrapolated** = reasoned from mechanism, no direct study. Sources in `research.md`.

Detection layer: **H** = heuristic (regex/keywords), **M** = model (classifier).

| # | Cue | Evidence | Layer |
|---|---|---|---|
| 1 | Asserted stance | Strong | H + M |
| 2 | Embedded assumption | Moderate | M |
| 3 | One-sided conflict seeking a verdict | Strong | M |
| 4 | Attachment to own work | Strong | H |
| 5 | Pushback without new information | Moderate | H |
| 6 | Identity cue on a contested topic | Moderate | H + M |
| 7 | Social proof or authority | Moderate | H |
| 8 | Answer-space constraints | Moderate | H |
| 9 | One-sided request during a decision | Extrapolated | M |
| 10 | False choice | Extrapolated | M |
| 11 | Curated evidence | Moderate | H + M |
| 12 | Assigned supportive role | Extrapolated | H |

Extrapolated cues start at a higher threshold until eval data supports them.

### 1. Asserted stance
The prompt signals the answer the user expects: plain statements, "I believe," "I'm convinced," tag questions ("X, right?", "Isn't it true that X?"), loaded words ("obviously," "rip-off"), and numeric anchors ("should cost around $8,000"). Severity (`strength` 1-3) rises with certainty: statement, belief, conviction.
Evidence: AISI, Sharma, Phare.
Tip: *"This signals the answer you expect. Asking it as an open question tends to get a more balanced response."*

### 2. Embedded assumption
The question is built on an unsupported inference, usually a leap from an observation to a cause or motive, so answering it as asked means accepting the inference. Boundary with cue 1: cue 1 is a stated belief ("I think X"); cue 2 is a belief built into the question ("Why does X happen?"). Tag both if both appear.
Evidence: ELEPHANT SS (statements); extension to questions is ours, supported by the at-issueness work.
Note: exasperated or rhetorical phrasing ("what's wrong with him," "why is she like this") leans borderline unless the question asks for action based on the assumption. "What's wrong with my dishwasher?" is not flagged: the observation supports the presupposition.
Tip: *"This assumes [X]. Try describing what happened and asking what it might mean."*

### 3. One-sided conflict seeking a verdict
The user's side of an interpersonal conflict, plus "was I wrong / am I right."
Evidence: ELEPHANT AITA-YTA and AITA-NTA-FLIP.
Tip: *"The model only has your side. Try asking how the other person might see it."*
Tip (domain: relationships): *"This is one take, not a verdict. A friend who knows both of you, or a therapist, would likely see it differently."*

### 4. Attachment to own work
"I wrote this," "I'm really proud of this," "I love this idea" alongside a request for feedback. Asking for feedback alone ("Here's my plan, thoughts?") is not the cue.
Evidence: Sharma feedback set.
Tip: *"Saying it's yours tends to soften the feedback. Try sharing it without that, or ask for weaknesses directly."*

### 5. Pushback without new information
"Are you sure?" or "I think it's X" in a follow-up turn, with no reason given. Needs `prior_turns`.
Evidence: Sharma are-you-sure; SycEval (14.66% regressive flips).
Tip: *"If you have a reason, include it. Otherwise ask the model to explain its answer instead of just switching."*

### 6. Identity cue on a contested topic
Self-disclosed identity ("As a conservative...", "As a progressive...") on a political or contested question where the identity doesn't change the correct answer. "As a nurse in Massachusetts, what are my licensing requirements?" is not the cue.
Evidence: political sycophancy study.
Tip: *"Mentioning your background can tilt the answer toward what people like you tend to think. Try asking without it."*

### 7. Social proof or authority
"Everyone knows," "experts agree," "my doctor said," "many people agree" used as support for a claim the user wants confirmed.
Evidence: Phare confidence templates (bundled with confidence, not isolated); SyPS (effect sizes unread).
Tip: *"Citing who agrees can make the model go along with it. Try asking whether the claim holds up on its own."*

### 8. Answer-space constraints
"Yes or no," "one word," "answer briefly," "no caveats," "don't lecture me," when the question needs nuance.
Evidence: Phare (brevity instructions in system prompts; applying this to user messages is a small extrapolation).
Tip: *"Short-answer limits leave no room for caveats. Consider allowing a sentence of context."*

### 9. One-sided request during a decision
"Give me reasons to move to Denver" when the user is clearly deciding. Flag only when decision context is present; a one-sided request with no pending decision falls under the persuasive-task exemption.
Evidence: extrapolated.
Tip: *"You asked for one side. If you're still deciding, ask for the case against too."*
Tip (domain: relationships): *"You asked for one side of a relationship decision. This is one perspective, not a fact; someone who knows you both will get you further than an AI opinion."*

### 10. False choice
"Should I do A or B?" when the likely best answer is neither. Needs world knowledge to detect. Model tier only.
Evidence: extrapolated.
Tip: *"You've limited this to two options. Try asking what options you might be missing."*

### 11. Curated evidence
User supplies sources that support one conclusion and asks a conclusion-shaped question ("Here are three articles showing X. Summarize what they say about X."). The extension can't judge the sources, only the pattern.
Evidence: Xie et al. (models adopt coherent in-context evidence).
Tip: *"The model will mostly work from what you gave it. Consider asking what evidence points the other way."*

### 12. Assigned supportive role
"Be my hype man," "be encouraging," "act as my biggest supporter," paired with a decision or feedback request. Custom instructions and memory in the chat apps can have the same effect, and the extension can't see them.
Evidence: extrapolated.
Tip: *"Asking for encouragement will get encouragement. If you need an honest read, ask for that separately."*
Tip (domain: relationships): *"Asking for support gets you support, not an outside read. For something this personal, a friend or therapist knows context this can't."*

## Folded into other cues
- Loaded language ("this scam company") → cues 1 and 3.
- Numeric anchors → cue 1.
- Tag questions and leading phrasing → cue 1 (defined by stance, not syntax).

## Don't flag (exemptions)

| Exemption | Example |
|---|---|
| `venting_no_decision` | Emotional content with no verdict or decision requested. Emotional framing **plus** a verdict request stays eligible. |
| `deliberate_one_sided_task` | "Write a persuasive email arguing for X," debate prep, role-play |
| `preference_as_constraint` | "I shoot Nikon and don't want to switch. Which Nikon body...?" |
| `decision_made_execute` | "I've decided to buy. How much should I save?" ("I've decided X, is it smart?" is cue 1.) |
| `invites_disagreement` | The user explicitly asks for counterevidence, weaknesses, or both sides |
| `factual_lookup` | Pure factual or how-to questions |

## Out of scope (for now)
Classic framing effects that don't come from agreeing with the user (e.g., "90% survival" vs. "10% mortality"). The product flags prompts that invite agreement, not every way wording shapes an answer.
