# How-To-Chat

Tools to help non-technical users get better answers from LLMs.

## Project 1: Prompt framing checker

A Chrome extension that flags when a prompt is framed in a way that tends to get an agreeable answer instead of an honest one. For example, "I'm convinced X is the best option, right?" instead of "Is X the best option?"

Research on LLM sycophancy shows that how a prompt is phrased changes how much the model agrees with the user. Stated certainty, first-person conviction, built-in assumptions, and one-sided accounts all increase agreement. The extension watches the chat input, detects these cues, and shows a small badge with a plain-language tip. It never blocks sending and never edits the prompt.

**Status:** research and spec complete; building the eval set. No extension code yet.

**MVP scope**
- Detection only (no automatic rewrites)
- ChatGPT first, then Claude and Gemini
- Runs entirely on-device; prompts never leave the browser

## Repo map

| Path | Contents |
|---|---|
| `docs/research.md` | Papers, key findings, caveats |
| `docs/taxonomy.md` | The 12 cues, the flag rule, exemptions, user-facing tips |
| `docs/architecture.md` | Extension design and the reasoning behind it |
| `docs/decisions.md` | Dated decision log |
| `data/schema.json` | Eval record format |
| `data/sources.md` | External datasets, what each covers, how to fetch |
| `data/seed/` | Hand-written, reviewed eval examples |
| `data/external/` | Downloaded datasets (gitignored) |
| `scripts/` | Fetch and adapter scripts |
| `eval/` | Eval harness and results |
| `extension/` | Chrome extension |

## Getting the external data

```
./scripts/fetch_external.sh
```

See `data/sources.md` for datasets that need a manual download.
