<p align="center">
  <img src="extension/icons/icon-128.png" alt="How-To-Chat logo" width="96">
</p>

# How-To-Chat

A Chrome extension that reads your prompt before you send it and tells you, in plain language, when the answer you're about to get might be less honest or less safe than you think.

It runs entirely in your browser. Nothing you type is sent anywhere else.

## Why this matters

If you have a friend or family member who comes to you saying "ChatGPT said this," "ChatGPT agreed with me," or "ChatGPT told me I was right," you've probably learned to ask the follow-up: what did you actually ask it, and how did you phrase it? How you ask shapes what you get back, and most people have no reason to know that.

People are asking ChatGPT for medical decisions, financial moves, and relationship advice, and trusting the answer like it came from a professional who knows them. Two things make that risky:

1. **The model tends to agree with you.** Research on LLM sycophancy shows that how you phrase a question changes how much the model agrees with you, independent of whether you're right. Say "I'm sure X is true" and the model is more likely to confirm it than if you'd asked "is X true?" That's not a bug in one model, it's a broad pattern across them.
2. **Some questions carry real stakes no matter how the model answers.** "Can I take an extra dose if I forgot this morning's?" is dangerous to get a wrong or careless answer to, regardless of how it's asked.

Most people don't have someone looking over their shoulder when they're chatting with an AI at 11pm about their prescription, their retirement account, or a call from someone claiming to be their grandson, and asking them about it afterward is too late. This extension is built to be that voice for them: the "wait, what did you actually ask it" question, asked automatically, before they hit send.

## The dangers it's trying to catch

**The main one: a leading question.** How you ask shapes the answer you get. Asking "I think my son's ADHD meds are doing more harm than good, what are the signs they aren't working?" invites a one-sided answer instead of an honest read. "Be my hype man and tell me quitting my job to stream full-time is a great plan" assigns the model a role that can't push back even if it should. "I'm 100% sure my Civic just needs a new battery, not an alternator, confirm that's it" pressures a confirmation instead of a real diagnosis. None of these are lies, they're just phrased in a way that makes agreement the path of least resistance, and that's the pattern this extension is built to catch.

**A narrower case: a high-stakes, hard-to-undo action.** Separately, a few specific actions get flagged regardless of how the question is phrased, because a wrong or careless answer is expensive to undo: medication dosing, sending or transferring money, signing a legal or financial document. For example, "I missed my blood pressure pill this morning, is it okay if I just take two tonight to catch up?" If you mention that a doctor, pharmacist, banker, or lawyer already reviewed this specific action, the extension backs off.

The extension also has a narrower, experimental check for scam narratives relayed from a third party (a caller claiming to be a relative or a bank, asking for gift cards or a wire transfer under pressure). It's a smaller part of the project and may not stick around in its current form, the core focus here is framing, not fraud detection.

## What the extension is

A Chrome extension for chatgpt.com. It watches the chat input as you type, runs two independent checks against the text, and shows a small badge near the input box if something's worth a second look. Click the badge for a one-line tip. It never edits your prompt and never blocks sending, a flag is information, not a gate.

## What it's looking for

Two separate things, checked independently:

**Framing cues (the main mechanism).** How you're asking, not what you're asking about. Twelve patterns, drawn from sycophancy research, where the way a prompt is phrased tends to pull the model toward agreement instead of an honest read: asserting a stance as settled fact, appealing to what "everyone knows" or what an authority already said, assigning the model a supportive role ("be my hype man"), presenting only one side of a story, and others documented in [`docs/taxonomy.md`](docs/taxonomy.md).

**Safety flags (a narrower add-on).** A small, separate set of checks on what the prompt involves rather than how it's phrased: a **stakes** flag for medication dosing, money transfers, and legal signing, and an experimental **scam narrative** flag for third-party stories with signs of fraud (urgency, secrecy, an unusual payment channel, an unfamiliar relative or authority). Documented in [`docs/safety.md`](docs/safety.md); scope and future here are still under discussion.

Safety flags get a red badge instead of amber and take priority when both fire.

## How it works

A content script watches the chat editor for input (debounced, since ChatGPT's editor doesn't fire normal input events on every change) and re-attaches automatically if the page swaps the editor out from under it. On each change, two detectors run against the current text:

- `detector.js` checks the 12 framing cues
- `safety-detector.js` checks the stakes and scam-narrative flags

Both are regex and keyword heuristics today, no model call, no network request. If either fires, an overlay renders a badge and popover in an isolated shadow root, so the extension never touches the page's own DOM beyond one host element and the site's CSS can't bleed into it or vice versa.

**What v0 does not do yet.** The heuristics catch phrasing patterns but don't yet reason about whether the flagged cue is actually load-bearing for the question being asked (tracked in [issue #2](../../issues/2)). The extension itself only runs on chatgpt.com; Claude and Gemini support is planned but not built ([issue #20](../../issues/20), [issue #21](../../issues/21)). Precision is the priority over recall here, a false flag costs more than a missed one, since over-flagging is what gets an extension uninstalled.

## Installing it locally

Not published to the Chrome Web Store yet. To load it unpacked for local testing:

1. Clone this repo.
2. Open `chrome://extensions` in Chrome.
3. Turn on **Developer mode** (top right).
4. Click **Load unpacked** and select the `extension/` folder.
5. Open chatgpt.com and start typing in the chat box.

## Repo map

| Path | Contents |
|---|---|
| `docs/research.md` | Papers, key findings, caveats |
| `docs/taxonomy.md` | The 12 framing cues, the flag rule, exemptions, user-facing tips |
| `docs/safety.md` | The stakes and scam-narrative safety flags, the safety rule |
| `docs/architecture.md` | Extension design and the reasoning behind it |
| `docs/decisions.md` | Dated decision log |
| `docs/demo-script.md` | Demo video shot list, prompts, and captions |
| `data/schema.json` | Eval record format for the 12 framing cues |
| `data/schema_safety.json` | Eval record format for the safety flags |
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
