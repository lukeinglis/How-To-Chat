# How-To-Chat

A Chrome extension that reads your prompt before you send it and tells you, in plain language, when the answer you're about to get might be less honest or less safe than you think.

It runs entirely in your browser. Nothing you type is sent anywhere else.

## Why this matters

People are asking ChatGPT for medical decisions, financial moves, and relationship advice, and trusting the answer like it came from a professional who knows them. Two things make that risky:

1. **The model tends to agree with you.** Research on LLM sycophancy shows that how you phrase a question changes how much the model agrees with you, independent of whether you're right. Say "I'm sure X is true" and the model is more likely to confirm it than if you'd asked "is X true?" That's not a bug in one model, it's a broad pattern across them.
2. **Some questions carry real stakes no matter how the model answers.** "Can I take an extra dose if I forgot this morning's?" is dangerous to get a wrong or careless answer to, regardless of how it's asked.

Most people don't have a second opinion in the room when they're chatting with an AI at 11pm about their prescription, their retirement account, or a call from someone claiming to be their grandson. This extension is that second opinion: a quiet nudge to pause and check, not another thing demanding your attention.

## The dangers it's trying to catch

**A scam narrative.** Someone claiming to be a relative, a bank, the IRS, or tech support, asking for money or account access under pressure. These follow recognizable patterns: urgency ("right now," "today"), secrecy ("don't tell my spouse"), an unusual payment channel (gift cards, wire transfer, crypto), or an unfamiliar person claiming authority or a relationship. For example:

> "My grandson Jake just called me crying, saying he's in jail in Mexico and needs $3,000 sent in gift cards right now, and begged me not to tell his mom. Should I do this?"

> "Someone called saying they're from Microsoft and that my computer has a dangerous virus. They said I need to buy $500 in Google Play cards today and read them the numbers over the phone so they can fix it. Does that sound right?"

A model asked either of these will often just answer the literal question. The extension flags the narrative itself, regardless of how the model would respond.

**A high-stakes, hard-to-undo action.** Medication dosing, sending or transferring money, signing a legal or financial document. These get flagged whether you're asking in advance or already did it, because "I already sent it" is exactly when the warning is most needed, not least. For example:

> "I missed my blood pressure pill this morning. Is it okay if I just take two tonight to catch up?"

> "I want to wire $40,000 from my retirement account to my nephew so he can put a down payment on a house. Can you help me figure out the best way to send it today?"

If you mention that a doctor, pharmacist, banker, or lawyer has already reviewed this specific action, the extension backs off. It's not trying to second-guess a professional, just to catch the cases where there wasn't one.

**A leading question.** Even outside high-stakes territory, phrasing shapes the answer. Asking "I think my son's ADHD meds are doing more harm than good, what are the signs they aren't working?" invites a one-sided answer; "Be my hype man and tell me quitting my job to stream full-time is a great plan" assigns the model a role that can't push back even if it should.

## What the extension is

A Chrome extension for chatgpt.com. It watches the chat input as you type, runs two independent checks against the text, and shows a small badge near the input box if something's worth a second look. Click the badge for a one-line tip. It never edits your prompt and never blocks sending, a flag is information, not a gate.

## What it's looking for

Two separate things, checked independently:

**Framing cues.** How you're asking, not what you're asking about. Twelve patterns, drawn from sycophancy research, where the way a prompt is phrased tends to pull the model toward agreement instead of an honest read: asserting a stance as settled fact, appealing to what "everyone knows" or what an authority already said, assigning the model a supportive role ("be my hype man"), presenting only one side of a story, and others documented in [`docs/taxonomy.md`](docs/taxonomy.md).

**Safety flags.** What the prompt involves, independent of framing. A flat, naive question about a medication dose deviation is in scope even though it doesn't assert any belief at all. Two flags: **stakes** (medication dosing, money transfers, legal signing) and **scam narrative** (urgency, secrecy, an unusual payment channel, or an unfamiliar relative/authority, with two or more of those present). Documented in [`docs/safety.md`](docs/safety.md).

Safety flags take priority when both fire, they're the higher-stakes case, and get a red badge instead of amber.

## How it works

A content script watches the chat editor for input (debounced, since ChatGPT's editor doesn't fire normal input events on every change) and re-attaches automatically if the page swaps the editor out from under it. On each change, two detectors run against the current text:

- `detector.js` checks the 12 framing cues
- `safety-detector.js` checks the stakes and scam-narrative flags

Both are regex and keyword heuristics today, no model call, no network request. If either fires, an overlay renders a badge and popover in an isolated shadow root, so the extension never touches the page's own DOM beyond one host element and the site's CSS can't bleed into it or vice versa.

**What v0 does not do yet.** The heuristics catch phrasing patterns but don't yet reason about whether the flagged cue is actually load-bearing for the question being asked (tracked in [issue #2](../../issues/2)), and cue 2 has no detector yet ([issue #3](../../issues/3)). The extension itself only runs on chatgpt.com; Claude and Gemini support is planned but not built. Precision is the priority over recall here, a false flag costs more than a missed one, since over-flagging is what gets an extension uninstalled.

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
