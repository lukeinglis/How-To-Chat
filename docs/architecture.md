# Architecture

## MVP
A Chrome extension (Manifest V3) that reads the chat input on chatgpt.com and shows a badge when the prompt contains a flaggable cue. Clicking the badge shows which cue fired and a static tip from `taxonomy.md`.

Not in the MVP: rewriting prompts, Claude and Gemini support, any network calls.

## Components

```
content script (per site)
  ├─ input watcher     finds the editor, reads text on input, debounced
  ├─ detector          heuristics → classifier (later) → cue list + should_flag
  └─ overlay           badge + popover, in a shadow root
site config            selectors per site, one file
```

## Design rules

**Read the editor, never write to it.** ChatGPT and Claude use ProseMirror; Gemini uses a similar rich editor. Injecting nodes into these editors corrupts their state. Grammarly learned this and moved to an overlay positioned with `Range.getClientRects()`. The MVP only needs a badge near the input, so it doesn't need text positions at all. Phrase highlighting (later) would use `getClientRects()`.

**Overlay lives in a shadow root.** The site's CSS can't affect it, and it doesn't touch the site's DOM beyond one host element.

**Never block sending.** No modals, no interception of Enter. A flag is information only.

**Nothing leaves the device.** Detection runs locally. This matters for trust with the target users and keeps costs at zero.

**Selectors in one config file.** The chat sites change their markup often. This is the part that will break.

**Precision over recall.** A false flag costs more than a missed one; over-flagging is what gets an extension uninstalled. Target at least 90% precision on the flag decision.

## Detection tiers

1. **Heuristics (v0).** Regex and keyword rules for cues 1, 4, 5, 6, 7, 8, 11. Runs on every debounced input. Zero dependencies.
2. **Fine-tuned classifier (v1).** A small encoder (ModernBERT or DeBERTa class, roughly 100-400 MB) running via transformers.js or ONNX Runtime Web on WebGPU or WASM. Handles cues 2, 3, 9, 10 and the exemption judgments. Chosen over Gemini Nano because it runs on any hardware, returns calibrated scores, is fast enough for every pause, and its version is ours (Nano can change in a Chrome update).
3. **Rewrite (post-MVP).** Gemini Nano via the Prompt API when available, a small WebLLM model as fallback, and an opt-in cloud call as the last resort. Only runs when the user clicks.

## Evals

1. **Detection eval** (`eval/`). Labeled prompts per `data/schema.json`. Reports precision and recall for the flag decision, per cue, and per exemption (false-positive breakdown). Borderline records are excluded from headline metrics.
2. **Impact eval** (later). Run flagged prompts and neutral versions through current ChatGPT, Claude, and Gemini and measure whether the flagged versions actually get more agreeable answers. This validates the cues on the models people actually use.
