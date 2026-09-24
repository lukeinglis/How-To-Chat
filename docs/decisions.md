# Decisions

Append-only. To change a decision, add a new entry that supersedes it.

| Date | Decision | Reason |
|---|---|---|
| 2026-09-24 | Chrome extension is the first surface | Where the target users already chat; one codebase covers three sites |
| 2026-09-24 | MVP is detection only; tips are static text per cue | Removes the generation model, editor writes, and most privacy risk; tips teach the habit |
| 2026-09-24 | ChatGPT first, then Claude and Gemini | Largest non-technical user base; add sites after the detector is tuned |
| 2026-09-24 | Overlay in a shadow root; never write to the editor; never block sending | Grammarly's experience with rich editors; uninstall risk |
| 2026-09-24 | All detection on-device | Trust with target users; zero cost |
| 2026-09-24 | Heuristics first, then a small fine-tuned classifier; Gemini Nano deferred to rewrites | Nano needs ~16 GB RAM, can change under us, and is a weak zero-shot classifier |
| 2026-09-24 | Precision first: at least 90% on the flag decision | False flags drive uninstalls |
| 2026-09-24 | Keep all 12 cues; extrapolated cues ship at a higher threshold | Cheap to keep; eval data decides what stays |
| 2026-09-24 | Flag rule: stance must bear on the question asked, and agreeing must skip a needed evaluation | Derived while reviewing seed examples; matches at-issueness research |
| 2026-09-24 | Every positive example has a matched hard negative | The classifier has to learn the framing, not the topic |
| 2026-09-24 | External benchmark data is for evaluation only, never training, and is not committed | Canary strings, licensing, contamination |
| 2026-09-24 | Start from published datasets, hand-write only the gaps | Hand-writing everything produced weak examples; published sets have matched variants and real posts |
