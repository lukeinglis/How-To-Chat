#!/usr/bin/env python3
"""Validates every file in data/external/converted/ against data/schema.json,
then joins data/labels/*.jsonl against the converted prompts: every label id
must exist, and every cue trigger must be an exact substring of that record's
prompt. Prints row counts per source, per notes "template:" tag, and per
label file. Usage: python3 scripts/validate_external.py
"""
import glob
import json
import os
import re
import sys
from collections import Counter

try:
    import jsonschema
except ImportError:
    jsonschema = None

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SCHEMA_PATH = os.path.join(ROOT, "data", "schema.json")
CONVERTED_DIR = os.path.join(ROOT, "data", "external", "converted")
LABELS_DIR = os.path.join(ROOT, "data", "labels")

TEMPLATE_TAG_RE = re.compile(r"template: ([^;]+)$")
LABEL_REQUIRED_FIELDS = {
    "id",
    "should_flag",
    "cues",
    "exemption",
    "domain",
    "rationale",
    "review",
}


def validate_record(record, schema, validator):
    if validator is not None:
        errors = sorted(validator.iter_errors(record), key=lambda e: e.path)
        return [e.message for e in errors]
    return manual_validate(record, schema)


def manual_validate(record, schema):
    """Minimal fallback if jsonschema isn't installed. Checks required
    fields, id pattern, and enums that matter most for this dataset."""
    errors = []
    for field in schema["required"]:
        if field not in record:
            errors.append(f"missing required field: {field}")
    if "id" in record and not re.match(
        r"^c\d{2}-(pos|neg|bord)-\d{3}$|^ext-[a-z0-9_]+-\d+$", record["id"]
    ):
        errors.append(f"id does not match pattern: {record['id']}")
    if record.get("should_flag") not in ("yes", "no", "borderline"):
        errors.append(f"bad should_flag: {record.get('should_flag')}")
    if record.get("domain") not in schema["properties"]["domain"]["enum"]:
        errors.append(f"bad domain: {record.get('domain')}")
    if record.get("review") not in ("approved", "pending"):
        errors.append(f"bad review: {record.get('review')}")
    allowed = set(schema["properties"].keys())
    extra = set(record.keys()) - allowed
    if extra:
        errors.append(f"unexpected fields: {sorted(extra)}")
    for cue in record.get("cues", []):
        if "cue" not in cue or "trigger" not in cue:
            errors.append(f"cue entry missing cue/trigger: {cue}")
    return errors


def validate_label(label, schema, prompt_by_id):
    """Checks a data/labels/ record: required fields, id exists in the
    converted data, and every trigger is an exact substring of that
    record's prompt."""
    errors = []
    missing = LABEL_REQUIRED_FIELDS - set(label.keys())
    if missing:
        errors.append(f"missing field(s): {sorted(missing)}")

    lid = label.get("id")
    if lid not in prompt_by_id:
        errors.append(f"id not found in any converted file: {lid}")
        return errors  # nothing left to check without a prompt to join against

    prompt = prompt_by_id[lid]

    if label.get("should_flag") not in ("yes", "no", "borderline"):
        errors.append(f"bad should_flag: {label.get('should_flag')}")
    if label.get("domain") not in schema["properties"]["domain"]["enum"]:
        errors.append(f"bad domain: {label.get('domain')}")
    if label.get("review") not in ("approved", "pending"):
        errors.append(f"bad review: {label.get('review')}")
    if label.get("exemption") not in schema["properties"]["exemption"]["enum"]:
        errors.append(f"bad exemption: {label.get('exemption')}")

    for cue in label.get("cues", []):
        if "cue" not in cue or "trigger" not in cue:
            errors.append(f"cue entry missing cue/trigger: {cue}")
            continue
        trigger = cue["trigger"]
        if trigger is not None and trigger not in prompt:
            errors.append(f"trigger not an exact substring of prompt: {trigger!r}")

    return errors


def main():
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    validator = None
    if jsonschema is not None:
        validator = jsonschema.Draft202012Validator(schema)
    else:
        print("(jsonschema not installed; using a minimal fallback checker)\n")

    files = sorted(glob.glob(os.path.join(CONVERTED_DIR, "*.jsonl")))
    if not files:
        print(f"No converted files found in {CONVERTED_DIR}")
        sys.exit(1)

    total_errors = 0
    source_counts = Counter()
    template_counts = Counter()  # (source, template) -> count
    prompt_by_id = {}

    for path in files:
        fname = os.path.basename(path)
        file_errors = 0
        with open(path) as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"{fname}:L{lineno}: invalid JSON: {e}")
                    file_errors += 1
                    continue
                errors = validate_record(record, schema, validator)
                for err in errors:
                    print(f"{fname}:L{lineno} [{record.get('id', '?')}]: {err}")
                file_errors += len(errors)

                if "id" in record and "prompt" in record:
                    prompt_by_id[record["id"]] = record["prompt"]

                source_counts[record.get("source", "?")] += 1
                notes = record.get("notes") or ""
                m = TEMPLATE_TAG_RE.search(notes)
                if m:
                    template_counts[(record.get("source", "?"), m.group(1))] += 1

        status = "OK" if file_errors == 0 else f"{file_errors} error(s)"
        print(f"{fname}: {status}")
        total_errors += file_errors

    print("\nRow counts per source:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

    print("\nRow counts per source x template:")
    for (source, template), count in sorted(template_counts.items()):
        print(f"  {source} / {template}: {count}")

    label_files = sorted(glob.glob(os.path.join(LABELS_DIR, "*.jsonl")))
    label_counts = Counter()  # (file, should_flag) -> count
    for path in label_files:
        fname = os.path.basename(path)
        file_errors = 0
        with open(path) as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    label = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"{fname}:L{lineno}: invalid JSON: {e}")
                    file_errors += 1
                    continue
                errors = validate_label(label, schema, prompt_by_id)
                for err in errors:
                    print(f"{fname}:L{lineno} [{label.get('id', '?')}]: {err}")
                file_errors += len(errors)
                label_counts[(fname, label.get("should_flag", "?"))] += 1

        status = "OK" if file_errors == 0 else f"{file_errors} error(s)"
        print(f"{fname}: {status}")
        total_errors += file_errors

    if label_files:
        print("\nLabel counts per file x should_flag:")
        for (fname, should_flag), count in sorted(label_counts.items()):
            print(f"  {fname} / {should_flag}: {count}")
    else:
        print(f"\nNo label files found in {os.path.relpath(LABELS_DIR, ROOT)}")

    if total_errors:
        print(f"\n{total_errors} total validation error(s)")
        sys.exit(1)
    print("\nAll records valid.")


if __name__ == "__main__":
    main()
