#!/usr/bin/env python3
"""Detection eval harness. Scores a detector against labeled eval data and
reports precision/recall on the flag decision, per-cue recall, and
per-exemption false-positive rates, per docs/architecture.md's "Evals"
section.

Data sources:
- data/seed/*.jsonl: full records (prompt + label together).
- data/labels/*.jsonl: labels only, joined to prompts in
  data/external/converted/*.jsonl by id. Run scripts/validate_external.py
  first; this harness assumes that join is already clean and will warn
  and skip (not crash) on anything it can't resolve.

By default only review: "approved" records count, matching the project
rule that pending records aren't ground truth yet. Pass --include-pending
to sanity-check a batch before it's approved; those runs are clearly
marked and should not be treated as real numbers.

should_flag: "borderline" records are excluded from headline precision/
recall (per architecture.md) but reported separately.

Detectors live in eval/detectors/<name>.py and expose:
    def predict(prompt: str, prior_turns: list) -> dict:
        return {"should_flag": "yes" | "no", "cues": [1, 3, ...]}
"cues" is optional (default []); per-cue recall is only reported if a
detector actually emits cue predictions. predict() only receives the
prompt and prior turns, never the label, so a detector has no way to
read the answer off the record it's being scored against.

Usage:
    python3 eval/run_eval.py --detector baseline_all_no
    python3 eval/run_eval.py --detector baseline_all_yes --include-pending
    python3 eval/run_eval.py --list-detectors
"""
import argparse
import glob
import importlib
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SEED_DIR = os.path.join(ROOT, "data", "seed")
LABELS_DIR = os.path.join(ROOT, "data", "labels")
CONVERTED_DIR = os.path.join(ROOT, "data", "external", "converted")
DETECTORS_DIR = os.path.join(os.path.dirname(__file__), "detectors")

EXEMPTIONS = [
    "venting_no_decision",
    "deliberate_one_sided_task",
    "preference_as_constraint",
    "decision_made_execute",
    "invites_disagreement",
    "factual_lookup",
]


def read_jsonl(path):
    records = []
    with open(path) as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARNING: {os.path.relpath(path, ROOT)}:L{lineno}: invalid JSON: {e}")
    return records


def load_seed_records(include_pending):
    records = []
    for path in sorted(glob.glob(os.path.join(SEED_DIR, "*.jsonl"))):
        for r in read_jsonl(path):
            if r.get("review") != "approved" and not include_pending:
                continue
            records.append(r)
    return records


def load_external_records(include_pending):
    """Joins data/labels/*.jsonl against data/external/converted/*.jsonl by
    id. Labels with no matching converted prompt are skipped with a
    warning, not a crash: run scripts/validate_external.py to catch and
    fix those before relying on eval numbers."""
    prompt_by_id = {}
    for path in sorted(glob.glob(os.path.join(CONVERTED_DIR, "*.jsonl"))):
        for r in read_jsonl(path):
            if "id" in r and "prompt" in r:
                prompt_by_id[r["id"]] = r

    records = []
    skipped = 0
    for path in sorted(glob.glob(os.path.join(LABELS_DIR, "*.jsonl"))):
        for label in read_jsonl(path):
            if label.get("review") != "approved" and not include_pending:
                continue
            lid = label.get("id")
            converted = prompt_by_id.get(lid)
            if converted is None:
                print(
                    f"WARNING: label {lid!r} has no matching converted "
                    f"record; skipping (run scripts/validate_external.py)"
                )
                skipped += 1
                continue
            record = {
                "id": lid,
                "prompt": converted["prompt"],
                "prior_turns": converted.get("prior_turns", []),
                "should_flag": label["should_flag"],
                "cues": label.get("cues", []),
                "exemption": label.get("exemption"),
                "domain": label.get("domain"),
                "review": label.get("review"),
            }
            records.append(record)
    if skipped:
        print(f"WARNING: skipped {skipped} label(s) with no converted match\n")
    return records


def load_detector(name):
    if not os.path.isdir(DETECTORS_DIR):
        sys.exit(f"No detectors directory at {DETECTORS_DIR}")
    sys.path.insert(0, DETECTORS_DIR)
    try:
        module = importlib.import_module(name)
    except ImportError as e:
        available = list_detector_names()
        sys.exit(
            f"Could not load detector {name!r}: {e}\n"
            f"Available detectors: {', '.join(available) or '(none found)'}"
        )
    if not hasattr(module, "predict"):
        sys.exit(f"Detector {name!r} has no predict(prompt, prior_turns) function")
    return module


def list_detector_names():
    if not os.path.isdir(DETECTORS_DIR):
        return []
    names = []
    for path in sorted(glob.glob(os.path.join(DETECTORS_DIR, "*.py"))):
        base = os.path.basename(path)[:-3]
        if base.startswith("_"):
            continue
        names.append(base)
    return names


def safe_div(numer, denom):
    return numer / denom if denom else None


def fmt_rate(rate):
    return "N/A" if rate is None else f"{rate:.1%}"


def score(records, detector):
    """Runs the detector over every record and buckets results by ground
    truth should_flag. Returns headline (yes/no only), borderline
    predictions, and raw per-record predictions for downstream breakdowns.

    The detector only ever sees prompt + prior_turns, never should_flag/
    cues/exemption -- it has no way to read the answer off the record
    it's being scored against."""
    headline = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    borderline_preds = {"yes": 0, "no": 0}
    predictions = []  # (record, predicted_flag, predicted_cues)
    detector_emits_cues = False

    for r in records:
        result = detector.predict(r["prompt"], r.get("prior_turns", []))
        pred_flag = result.get("should_flag")
        if pred_flag not in ("yes", "no"):
            sys.exit(
                f"Detector returned invalid should_flag {pred_flag!r} for "
                f"record {r.get('id')}; must be 'yes' or 'no'"
            )
        pred_cues = result.get("cues") or []
        if pred_cues:
            detector_emits_cues = True
        predictions.append((r, pred_flag, pred_cues))

        gt = r["should_flag"]
        if gt == "borderline":
            borderline_preds[pred_flag] += 1
            continue
        if gt == "yes" and pred_flag == "yes":
            headline["tp"] += 1
        elif gt == "no" and pred_flag == "yes":
            headline["fp"] += 1
        elif gt == "yes" and pred_flag == "no":
            headline["fn"] += 1
        else:
            headline["tn"] += 1

    return headline, borderline_preds, predictions, detector_emits_cues


def per_cue_recall(predictions):
    """For each cue present in any ground-truth yes record, the fraction
    of those records where the detector's predicted cues included it."""
    rows = []
    for cue in range(1, 13):
        support = [
            (r, pred_cues)
            for r, pred_flag, pred_cues in predictions
            if r["should_flag"] == "yes"
            and any(c["cue"] == cue for c in r["cues"])
        ]
        if not support:
            continue
        detected = sum(1 for _, pred_cues in support if cue in pred_cues)
        rows.append((cue, detected, len(support)))
    return rows


def per_exemption_false_positives(predictions):
    """False-positive rate per exemption: among ground-truth "no" records
    carrying that exemption, how often the detector still predicted
    "yes". Records with should_flag "no" and no exemption go in a "none"
    bucket."""
    buckets = {}
    for r, pred_flag, _ in predictions:
        if r["should_flag"] != "no":
            continue
        key = r.get("exemption") or "none"
        fp, total = buckets.get(key, (0, 0))
        total += 1
        if pred_flag == "yes":
            fp += 1
        buckets[key] = (fp, total)
    return buckets


def print_report(records, detector_name, headline, borderline_preds, predictions, detector_emits_cues):
    yes_n = sum(1 for r in records if r["should_flag"] == "yes")
    no_n = sum(1 for r in records if r["should_flag"] == "no")
    bord_n = sum(1 for r in records if r["should_flag"] == "borderline")

    print(f"Detector: {detector_name}")
    print(f"Records scored: {len(records)} (yes={yes_n}, no={no_n}, borderline={bord_n})\n")

    tp, fp, fn, tn = headline["tp"], headline["fp"], headline["fn"], headline["tn"]
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = None
    if precision is not None and recall is not None and (precision + recall) > 0:
        f1 = 2 * precision * recall / (precision + recall)

    print("Headline (should_flag yes/no only, borderline excluded):")
    print(f"  precision: {fmt_rate(precision)}  (tp={tp}, fp={fp})")
    print(f"  recall:    {fmt_rate(recall)}  (tp={tp}, fn={fn})")
    print(f"  f1:        {fmt_rate(f1)}")
    print(f"  tn={tn}")

    if bord_n:
        print(
            f"\nBorderline ({bord_n} records, informational only, not in headline):"
            f" predicted yes={borderline_preds['yes']}, no={borderline_preds['no']}"
        )

    print("\nPer-cue recall (ground-truth yes records only):")
    if not detector_emits_cues:
        print("  detector does not emit cue-level predictions; skipped")
    else:
        rows = per_cue_recall(predictions)
        if not rows:
            print("  no ground-truth records carry any cue")
        for cue, detected, support in rows:
            print(f"  cue {cue:>2}: {fmt_rate(detected / support)}  ({detected}/{support})")

    print("\nFalse positives per exemption (ground-truth no records only):")
    buckets = per_exemption_false_positives(predictions)
    for key in EXEMPTIONS + ["none"]:
        if key not in buckets:
            continue
        fp, total = buckets[key]
        print(f"  {key}: {fmt_rate(safe_div(fp, total))}  ({fp}/{total})")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--detector", help="Name of a module under eval/detectors/ (without .py)")
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Include review:pending records. Not ground truth yet; for sanity-checking a batch before approval only.",
    )
    parser.add_argument("--list-detectors", action="store_true")
    args = parser.parse_args()

    if args.list_detectors:
        for name in list_detector_names():
            print(name)
        return

    if not args.detector:
        parser.error("--detector is required (use --list-detectors to see options)")

    detector = load_detector(args.detector)

    records = load_seed_records(args.include_pending) + load_external_records(args.include_pending)
    if not records:
        sys.exit(
            "No eligible records found. All labels may still be review:pending "
            "-- pass --include-pending to sanity-check anyway."
        )
    if args.include_pending:
        print("*** --include-pending set: this run includes unapproved labels and is not a real score ***\n")

    headline, borderline_preds, predictions, detector_emits_cues = score(records, detector)
    print_report(records, args.detector, headline, borderline_preds, predictions, detector_emits_cues)


if __name__ == "__main__":
    main()
