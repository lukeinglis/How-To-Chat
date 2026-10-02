# Demo video script

Silent, caption-driven, smooth continuous footage (recorded in Cap, Studio
Mode). No narration, no talking head. Three live examples on chatgpt.com
with the extension loaded, each ending on the badge firing.

## Shot list

| # | Shot | On screen | Caption |
|---|---|---|---|
| 0 | Cold open | Blank ChatGPT compose box | "How you ask shapes the answer you get." |
| 1 | p1 | Type p1 into the compose box, let the badge appear | "This signals the answer you expect." |
| 2 | p2 | Type the setup line, send, get a reply, then type the pushback line and let the badge appear | "If you have a reason, include it. Otherwise ask the model to explain its answer instead of just switching." |
| 3 | p3 | Type p3 into the compose box, let the red badge appear | "Contact them directly using a number you already have, not one they gave you." |
| 4 | End card | Extension icon / name | "How-To-Chat. It never blocks sending. A flag is information, not a gate." |

## Prompts

**p1 — medical, cue 1 (leading stance), amber badge**

> I have a rash on my left arm, I think its because I got my flu shot earlier this week.

**p2 — mental health, cue 5 (pushback without a new reason), amber badge**

Two turns. Only the second line is flagged, and only because there's a
prior turn in the thread — this is meant to show the extension tracking
context, not just scoring a single message in isolation.

Setup (not flagged):
> I've been having panic attacks a couple times a week for the last month, is that something i need to get checked out for

Pushback (flagged):
> are you sure, i still think its just caffeine making my heart race

**p3 — scam narrative, red badge**

> My grandson needs me to buy 500 dollars in apple gift cards today. He said I can buy them online and then just send him the codes. Can you help me?

Note: without "today" this doesn't flag (only one of the two required scam
signals fires). Tracked in [issue #13](../../issues/13) as a possible gap
in the 2-signal floor for scam-narrative detection.

## Notes

- Keep typing speed and cadence natural; don't let Cap's auto-zoom linger so long on the text that it reads as staged.
- p2 is the only multi-turn shot; cut from the setup reply straight into the pushback line so the sequence doesn't drag.
- Red badge on p3 should get a beat longer on screen than the amber badges, since it's the highest-stakes example.
