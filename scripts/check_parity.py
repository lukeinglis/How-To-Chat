#!/usr/bin/env python3
"""Checks that the shipped JavaScript detectors and the Python detectors the
eval harness scores agree on every prompt in the corpus.

The project keeps two hand-mirrored copies of each detector:
extension/src/detector.js is what users run, eval/detectors/v0_heuristic.py is
what eval/run_eval.py measures (same for the safety pair). A precision number
from the harness only describes the shipped extension while those stay
behaviorally identical, so drift has to fail loudly rather than silently
invalidate the metric. See docs/decisions.md 2026-10-07.

Both detectors run over every prompt regardless of which cue a record was
written for, since they're pure functions of the text and more inputs means
more coverage. Labels are never read: this compares the two implementations
to each other, not to ground truth.

Parity only holds for behavior the corpus actually exercises. Verified by
mutation: deleting "\baita\b" from CUE3_VERDICT in the JS surfaces 157
mismatches, but dropping "say" from CUE7_AUTHORITY's alternation surfaces
none, because no prompt in the corpus says "most people say". Rare branches
can still drift silently, so a passing run is not proof the files are
identical, only that they agree everywhere it can be observed.

Exits 1 on any mismatch. Usage: python3 scripts/check_parity.py
"""
import glob
import json
import os
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DETECTORS_DIR = os.path.join(ROOT, "eval", "detectors")
JS_RUNNER = os.path.join(ROOT, "scripts", "parity_js_runner.js")

CORPUS_GLOBS = [
    os.path.join(ROOT, "data", "seed", "*.jsonl"),
    os.path.join(ROOT, "data", "seed", "safety", "*.jsonl"),
    os.path.join(ROOT, "data", "external", "converted", "*.jsonl"),
]

sys.path.insert(0, DETECTORS_DIR)
import v0_heuristic
import v0_heuristic_safety


def load_corpus():
    """Returns [{id, prompt, prior_turns}], ids namespaced by source file so
    records from different files can't collide."""
    records = []
    seen = set()
    for pattern in CORPUS_GLOBS:
        for path in sorted(glob.glob(pattern)):
            stem = os.path.splitext(os.path.basename(path))[0]
            with open(path, encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    line = line.strip()
                    if not line:
                        continue
                    record = json.loads(line)
                    prompt = record.get("prompt")
                    if not prompt:
                        continue
                    key = f"{stem}:{record.get('id', lineno)}"
                    if key in seen:
                        key = f"{key}#{lineno}"
                    seen.add(key)
                    records.append(
                        {
                            "id": key,
                            "prompt": prompt,
                            "prior_turns": record.get("prior_turns", []),
                        }
                    )
    return records


def predict_python(records):
    results = {}
    for record in records:
        framing = v0_heuristic.predict(record["prompt"], record["prior_turns"])
        safety = v0_heuristic_safety.predict(record["prompt"], record["prior_turns"])
        results[record["id"]] = {
            "framing": {
                "should_flag": framing["should_flag"] == "yes",
                "cues": list(framing.get("cues", [])),
            },
            "safety": {
                "should_flag": safety["should_flag"] == "yes",
                "signals": list(safety.get("signals", [])),
            },
        }
    return results


def predict_js(records):
    proc = subprocess.run(
        ["node", JS_RUNNER],
        input=json.dumps(records),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        sys.exit(f"JS runner failed:\n{proc.stderr.strip()}")
    return {r["id"]: r for r in json.loads(proc.stdout)}


def diff(record_id, kind, field, py_value, js_value, mismatches):
    if py_value != js_value:
        mismatches.append((record_id, kind, field, py_value, js_value))


def main():
    records = load_corpus()
    if not records:
        sys.exit("No prompts found. Check data/seed/ exists.")

    python_results = predict_python(records)
    js_results = predict_js(records)

    mismatches = []
    for record in records:
        rid = record["id"]
        py = python_results[rid]
        js = js_results[rid]
        for kind, field in (("framing", "cues"), ("safety", "signals")):
            diff(rid, kind, "should_flag", py[kind]["should_flag"], js[kind]["should_flag"], mismatches)
            diff(rid, kind, field, py[kind][field], js[kind][field], mismatches)

    print(f"Prompts compared: {len(records)}")
    print("Detectors: detector.js vs v0_heuristic.py, safety-detector.js vs v0_heuristic_safety.py")

    if not mismatches:
        print("\nParity OK: both implementations agree on every prompt.")
        return

    print(f"\nPARITY BROKEN: {len(mismatches)} mismatch(es)")
    for rid, kind, field, py_value, js_value in mismatches:
        print(f"\n  {rid} [{kind}.{field}]")
        print(f"    python: {py_value!r}")
        print(f"    js:     {js_value!r}")
        prompt = next(r["prompt"] for r in records if r["id"] == rid)
        print(f"    prompt: {prompt[:160]!r}")
    sys.exit(1)


if __name__ == "__main__":
    main()
