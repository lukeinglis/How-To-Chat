#!/usr/bin/env python3
"""Stratified audit sample for hand-labeling data/external/converted/*.jsonl.

Rather than a flat percentage of each source, this pulls a fixed number of
v0_heuristic-flagged rows (to audit precision: how many flagged rows are
actually should_flag "yes") and a fixed number of unflagged rows (to audit
recall: how many real positives the heuristic is missing) per source. Sample
size is capped by what's actually available in a source, not scaled to its
raw row count -- see the CLAUDE.md discussion this script implements.

v0_heuristic emits cues 1-8 and 11, so the stratification covers those. Cues
9 and 10 are the only ones it never predicts, so they will not be represented
here; those need separate random or keyword-based sampling to get labeling
coverage. The pools below are split on the detector's live output rather than
a hardcoded cue list, so this note going stale does not skew the sample.

Output goes to data/external/candidates/<source>.jsonl (gitignored, since it
carries prompt text -- same rule as data/external/converted/). Never commit
this output or copy it into data/labels/ directly; it's a worklist for the
labeling review loop, not labels.

Usage:
    python3 scripts/sample_external_for_labels.py --flagged 40 --unflagged 40 --seed 42
"""
import argparse
import glob
import json
import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONVERTED_DIR = os.path.join(ROOT, "data", "external", "converted")
CANDIDATES_DIR = os.path.join(ROOT, "data", "external", "candidates")

sys.path.insert(0, os.path.join(ROOT, "eval", "detectors"))
import v0_heuristic as det  # noqa: E402


def read_jsonl(path):
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flagged", type=int, default=40, help="Target flagged rows per source")
    parser.add_argument("--unflagged", type=int, default=40, help="Target unflagged rows per source")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    os.makedirs(CANDIDATES_DIR, exist_ok=True)
    rng = random.Random(args.seed)

    print(f"{'source':<28} {'rows':>7} {'flagged_pool':>12} {'unflagged_pool':>14} {'sampled_flag':>12} {'sampled_unflag':>14}")
    print("-" * 100)

    grand_total = 0
    for path in sorted(glob.glob(os.path.join(CONVERTED_DIR, "*.jsonl"))):
        name = os.path.basename(path)[:-6]
        records = read_jsonl(path)

        flagged_pool = []
        unflagged_pool = []
        for r in records:
            result = det.predict(r.get("prompt", ""), r.get("prior_turns", []))
            r["_heuristic_flag"] = result["should_flag"]
            r["_heuristic_cues"] = result.get("cues", [])
            (flagged_pool if result["should_flag"] == "yes" else unflagged_pool).append(r)

        n_flag = min(args.flagged, len(flagged_pool))
        n_unflag = min(args.unflagged, len(unflagged_pool))
        sampled = rng.sample(flagged_pool, n_flag) + rng.sample(unflagged_pool, n_unflag)
        rng.shuffle(sampled)

        out_path = os.path.join(CANDIDATES_DIR, f"{name}.jsonl")
        with open(out_path, "w") as f:
            for r in sampled:
                f.write(json.dumps(r) + "\n")

        grand_total += len(sampled)
        print(f"{name:<28} {len(records):>7} {len(flagged_pool):>12} {len(unflagged_pool):>14} {n_flag:>12} {n_unflag:>14}")

    print("-" * 100)
    print(f"Total candidates written: {grand_total}")
    print(f"Output dir: {os.path.relpath(CANDIDATES_DIR, ROOT)} (gitignored)")


if __name__ == "__main__":
    main()
