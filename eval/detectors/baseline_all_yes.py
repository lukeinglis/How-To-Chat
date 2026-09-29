"""Trivial baseline: always flags. Precision equals the should_flag:yes
prevalence in whatever data is scored; recall ceiling of 100%."""


def predict(prompt, prior_turns):
    return {"should_flag": "yes", "cues": []}
