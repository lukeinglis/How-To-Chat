# CLAUDE.md

Chrome extension that flags prompts framed to get an agreeable answer from an LLM. The target users are non-technical people using ChatGPT, Claude, and Gemini. Read `README.md` for the overview.

## Read before working
- `docs/taxonomy.md`: the 12 cues and **the flag rule**. Every labeling decision goes through the flag rule.
- `docs/decisions.md`: settled decisions. Don't reopen one without new evidence. To change one, add a superseding entry; never edit old rows.
- `data/schema.json`: eval record format. Validate every JSONL file against it.

## Hard constraints
- The extension never writes to the chat editor, never blocks sending, and makes no network calls.
- UI renders in a shadow root. Per-site selectors live in one config file.
- Precision first: at least 90% precision on the flag decision before raising recall.
- External datasets (`data/external/`) are for evaluation only. Never train on them, never commit them, never copy their rows into `data/seed/`.

## Data rules
- Every positive example gets a matched hard negative (`pair`), ideally near word-for-word, differing only in framing.
- `cues` records what is present; `should_flag` is the final call after exemptions. A record can have cues and `should_flag: "no"`.
- `trigger` must be an exact substring of `prompt`.
- New hand-written examples are `review: "pending"` until Luke approves them. Don't mark anything approved yourself.
- Prefer realistic prompts: how a non-technical adult would actually type. Avoid trivia, benchmark phrasing, and templates.
- Strip "AITA for" titles from ELEPHANT posts before use.

## Working style
- Luke prefers going section by section. For labeling work, show a small batch (5-10) for review before generating more.
- Writing: no em dashes, direct prose, specific numbers, don't oversell.

## Roadmap
1. Adapters: convert Sharma, ELEPHANT, Phare, Perez into the schema (`scripts/`). Tag each record with its source.
2. Sample and relabel external data against the flag rule; hand-write the gaps (cues 2, 6-12, exemption negatives).
3. Eval harness (`eval/`): precision/recall on the flag decision, per cue, and false positives per exemption. Borderline excluded from headline metrics.
4. Heuristic detector (v0) for cues 1, 4, 5, 6, 7, 8, 11, 12.
5. Extension shell on chatgpt.com: input watcher, detector, badge.
6. Fine-tuned small classifier (v1), trained on generated data, never on external eval data.
7. Impact eval: do flagged prompts actually get more agreeable answers from current models?

## Open items
- Confirm `c02-pos-005` / `c02-neg-005` (gluten pair), currently pending.
- Read SyPS (arXiv 2608.23837) effect sizes to firm up cue 7.
- Check ELEPHANT's data license.
- Ask the AISI authors whether the 440 Ask Don't Tell prompts are available.
- Decide how to weight realistic vs. benchmark-style prompts in metrics.
