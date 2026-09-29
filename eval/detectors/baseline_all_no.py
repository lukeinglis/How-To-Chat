"""Trivial baseline: never flags anything. Recall floor of 0; gives the
harness something real to score before v0 heuristics exist."""


def predict(prompt, prior_turns):
    return {"should_flag": "no", "cues": []}
