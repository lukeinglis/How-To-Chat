# Safety flags

Separate from the 12 framing cues in `taxonomy.md`. The framing cues fire on how the user asks; these fire on what the prompt involves, independent of framing. See `docs/decisions.md` (2026-09-30) for why they're split out.

## The safety rule

> Flag when the prompt involves an action or narrative where an agreeable or literal answer could cause real-world harm that's hard to undo, whether or not the user's framing invites agreement.

No stance test, no at-issueness test. A flat, naive question ("can I take an extra dose if I forgot this morning's?") is in scope even though it asserts no belief.

## Stakes flag

Fires on an action with hard-to-reverse real-world consequences: medication dosing (deviating from label or prescription), sending or transferring money, or signing a legal or financial commitment. Applies whether the user is asking in advance or reporting the action already taken — reporting it as done does not exempt it.

v1 domain scope: health (medication dosage/interactions), money (transfers, signing).

Signals: `medication_dosage`, `financial_transfer`, `legal_signing`.

Tip: *"Confirm this with a pharmacist or your doctor before taking it."* (health) / *"Confirm this with your bank using a number you already have, before sending anything."* (money)

Exemption: `professional_directed` — the user states a named professional (doctor, pharmacist, banker, lawyer) already reviewed this specific action, not just gave general guidance in the past.

## Scam-narrative flag

Fires when the prompt relays a third party's narrative containing a known fraud pattern: urgency ("right now," "today only," "before the bank closes"), secrecy ("don't tell my spouse," "keep this between us"), an unusual payment channel (gift cards, wire transfer, cryptocurrency, cash pickup), or an unfamiliar or distressed relative/authority figure asking for money or account access. Flag when two or more elements are present, regardless of whether the user says they believe the story.

v1 domain scope: money, relationships (family-in-trouble narratives), work (vendor/business email compromise), other (tech-support and romance scams).

Signals: `urgency`, `secrecy`, `unusual_payment_channel`, `unfamiliar_relative_or_authority`.

Tip: *"Contact them directly using a number you already have, not one they gave you."*

Exemptions:
- `known_recipient_routine_transfer` — paying a long-established payee (a utility, a contractor already hired) through a normal channel.
- `professional_context` — a bookkeeper, accountant, or business partner discussing a routine business wire the user already expects.

## Don't inherit the framing exemptions

Neither safety flag uses `decision_made_execute`. For a framing cue, "I already decided" is a reason to back off — the decision is made and further pushback wastes the user's time. For a safety flag, "I already sent the money" or "I already took the extra dose" is exactly when the warning is most needed, not least. See `docs/decisions.md` (2026-09-30).
