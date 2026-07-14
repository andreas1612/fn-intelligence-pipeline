"""Distribution: output plugins, one per channel.

Mirrors src/collectors/ for intake. Collectors bring items in, the deterministic
core (triage, review, matching) sits in the middle, and distribute sends the
result out. Nothing here calls a model and nothing here bypasses the human gate.
"""
