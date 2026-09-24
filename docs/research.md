# Research

Evidence behind the taxonomy. Numbers are as reported by each source. Where a claim in `taxonomy.md` goes beyond these sources, it is marked as an extrapolation there.

## Framing and sycophancy

### Ask Don't Tell (UK AISI, Dubois et al., 2026)
[arXiv 2602.23971](https://arxiv.org/abs/2602.23971) · [blog](https://www.aisi.gov.uk/blog/ask-dont-tell-reducing-sycophancy-in-large-language-models-2)

Controlled study: 40 debatable yes/no questions, each converted into matched variants (question, statement, belief, conviction; first-person vs. third-person; affirmation vs. negation), 440 prompts total. Models: GPT-4o, GPT-5, Claude Sonnet 4.5. Two LLM graders.

- Questions produced near-zero sycophancy. Non-questions expressing the same claim produced a 24-percentage-point higher score on the grader scale.
- Sycophancy rose monotonically with certainty: statement < "I believe" < "I am convinced."
- First-person framing produced more sycophancy than third-person ("the user believes").
- Hobbies and social topics drew more sycophancy than medical and mental health topics. The framing effect held in all domains.
- GPT-4o was notably more sycophantic than GPT-5 and Sonnet 4.5.
- Converting a statement into a question before answering reduced sycophancy. The 2-step version (separate framer model) worked best. Both versions beat instructing the model "not to be sycophantic."
- Limits: synthetic single-turn prompts, topics without a correct answer, LLM-as-judge scoring.

**Used for:** cue 1, and the future rewrite feature.

### ELEPHANT (Cheng et al., ICLR 2026)
[arXiv 2505.13995](https://arxiv.org/abs/2505.13995) · [code](https://github.com/myracheng/elephant)

Social sycophancy defined as excessive preservation of the user's "face" (desired self-image). 11 models, four datasets.

- Models preserved face 45 percentage points more than humans on advice queries and on posts where the user was at fault.
- On advice queries (ICLR version): validated the user 72% vs. 22% for humans, avoided direct guidance 66% vs. 21%, accepted the user's framing 88% vs. 60%.
- Given both sides of a moral conflict, models told both parties they were not wrong in 48% of cases.
- Datasets: OEQ (3,027 advice queries), AITA-YTA (2,000 posts, poster at fault), SS (3,777 assumption-laden statements), AITA-NTA-FLIP (1,591 perspective pairs).

**Used for:** cues 2 and 3, and realistic negatives (OEQ).

### Accommodation (Cheng et al.)
[code](https://github.com/myracheng/accommodation)

Explains failures to challenge harmful beliefs as pragmatic accommodation. At-issueness (whether the assumption is the thing being asked about or just background), linguistic encoding, and source reliability all change whether models push back. A short intervention ("wait a minute") improved results.

**Used for:** the flag rule in `taxonomy.md`. The "stance must bear on the question asked" test is an at-issueness test.

### Towards Understanding Sycophancy (Sharma et al., Anthropic, 2023)
[arXiv 2310.13548](https://arxiv.org/abs/2310.13548) · [data](https://github.com/meg-tong/sycophancy-eval)

Showed sycophancy across free-form tasks: feedback that shifts when the user says they like, dislike, or wrote the text; answers that shift with the user's suggested answer; and answer changes after "Are you sure?" pushback. Also showed sycophancy is rewarded in human preference data.

**Used for:** cues 1, 4, 5.

### SycEval (Fanous et al., 2025)

ChatGPT-4o, Claude Sonnet, and Gemini 1.5 Pro on math (AMPS) and medical (MedQuad) questions under rebuttal.

- 58.19% of cases showed sycophancy (an answer change). This counts both directions.
- Progressive (moved to the correct answer): 43.52%. Regressive (moved to an incorrect answer): 14.66%.
- Preemptive rebuttals drew more sycophancy than in-context rebuttals.

**Used for:** cue 5. The regressive rate is the relevant number; pushback sometimes fixes real errors.

### Phare (Giskard, 2025)
[arXiv 2505.11365](https://arxiv.org/html/2505.11365) · [code](https://github.com/Giskard-AI/phare)

- Confident framing of a false claim cut debunking accuracy by up to 15% vs. unsure framing. 10 of 17 models were significantly affected.
- "Very confident" templates include authority and social proof: "My teacher, who's extremely smart, explained to me that...", "Many people seem to agree that... It means it must be true."
- System prompts asking for concise answers reduced resistance to misinformation.

**Used for:** cues 1, 7, 8.

### Political sycophancy: identity and opinion
[arXiv 2608.29198](https://arxiv.org/html/2608.29198)

Separates opinion-driven sycophancy (user states a view) from identity-driven sycophancy (user discloses an identity). Both shift political answers.

**Used for:** cue 6.

### SyPS: Sycophancy Prompt Sensitivity
[arXiv 2608.23837](https://arxiv.org/html/2608.23837)

Studies social framing cues (confidence, uncertainty, reassurance seeking, distress, "others agree") on ELEPHANT data. **Effect sizes not yet read.** Needed to firm up cue 7.

### Knowledge conflicts (Xie et al., ICLR 2024)
"Adaptive Chameleon or Stubborn Sloth." Models readily adopt coherent evidence supplied in context, even when it contradicts their own knowledge.

**Used for:** cue 11.

## Overall caveats

- Nearly all evidence comes from synthetic, single-turn prompts.
- Newer models show smaller effects (AISI). The impact eval must test current ChatGPT, Claude, and Gemini before thresholds are tuned.
- All of these datasets label model responses, not prompts. Prompt-level should-flag labels are ours to create.

## Implementation references

### Grammarly extension
- [Making Grammarly Feel Native On Every Website](https://www.grammarly.com/blog/engineering/making-grammarly-feel-native-on-every-website/): early versions wrapped text in nodes inside the editor, which corrupted text and broke editors (ProseMirror, Quill, Draft.js added ways to disable it). They moved to an overlay positioned with `Range.getClientRects()`, drawn outside the field.
- [On-Device AI at Scale](https://www.grammarly.com/blog/engineering/on-device-models-scale/): on-device grammar model under 300 MB; later a ~1B model at 210 tokens/s on M2.

### Chrome built-in AI
- [Built-in AI APIs](https://developer.chrome.com/docs/ai/built-in-apis): Prompt API (Gemini Nano) stable for extensions since Chrome 138, for web pages since Chrome 148. Rewriter and Writer APIs in origin trial.
- Hardware: roughly 22 GB free disk, and 16 GB RAM or a GPU with more than 4 GB VRAM. Many target users' machines will not qualify.
