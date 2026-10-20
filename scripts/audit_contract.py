"""Check declared question coverage, artifacts, and explicit text-result bindings.

This standard-library audit does not assess scientific validity, prose quality,
unmarked numbers, PDF/image contents, or whether the declared questions exhaust
the original problem. It never evaluates a code expression from a contract.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

STAGES = ("problem", "data", "model_selection", "implementation", "validation", "paper", "submission", "complete")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*\Z")
MARKER = re.compile(r"<!--\s*(/?)\s*(answer|result):([A-Za-z][A-Za-z0-9_.-]*)\s*-->")
MARKER_START = re.compile(r"<!--\s*/?\s*(?:answer|result):")
PLACEHOLDER = re.compile(r"\b(?:TODO|TBD|待填|待核验)\b|待填|待核验", re.IGNORECASE)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        require(key not in result, f"DUPLICATE_JSON_KEY {key}")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError(f"NONFINITE_JSON {value}")


def finite_tree(value: object) -> None:
    if isinstance(value, float):
        require(math.isfinite(value), "NONFINITE_JSON number")
    elif isinstance(value, dict):
        for child in value.values():
            finite_tree(child)
    elif isinstance(value, list):
        for child in value:
            finite_tree(child)


def read_json(path: Path) -> object:
    value = json.loads(path.read_text(encoding="utf-8-sig"),
                       object_pairs_hook=unique_object, parse_constant=reject_constant)
    finite_tree(value)
    return value


def no_links(path: Path) -> None:
    for part in (path, *path.parents):
        try:
            attributes = part.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(attributes.st_mode)
                and not (getattr(attributes, "st_file_attributes", 0) & 0x400),
                f"LINK_PATH_REJECTED {part.name}")


def safe_path(root: Path, value: object) -> Path:
    require(isinstance(value, str) and bool(value.strip()), "INVALID_RELATIVE_PATH empty or non-string")
    require(not any(character in value for character in ("\\", ":", "\x00")), f"INVALID_RELATIVE_PATH {value}")
    parts = value.split("/")
    require(not any(part in ("", ".", "..") for part in parts), f"PATH_ESCAPE_OR_AMBIGUOUS {value}")
    require(not Path(value).is_absolute(), f"ABSOLUTE_PATH {value}")
    target = root.joinpath(*parts)
    require(target.is_relative_to(root), f"PATH_ESCAPE {value}")
    no_links(target)
    return target


def text(value: object, name: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"INVALID_STRING {name}")
    return value


def identifier(value: object, name: str) -> str:
    require(isinstance(value, str) and bool(ID.fullmatch(value)), f"INVALID_ID {name}")
    return value


def fields(row: object, required: set[str], optional: set[str], name: str) -> dict:
    require(isinstance(row, dict), f"INVALID_OBJECT {name}")
    require(required <= row.keys(), f"MISSING_FIELDS {name}: {sorted(required - row.keys())}")
    require(row.keys() <= required | optional, f"UNKNOWN_FIELDS {name}: {sorted(row.keys() - required - optional)}")
    return row


def stage_index(row: dict) -> int:
    require(row["from_stage"] in STAGES[:-1], "INVALID_FROM_STAGE")
    return STAGES.index(row["from_stage"])


def pointer(document: object, path: object) -> object:
    require(isinstance(path, str) and (path == "" or path.startswith("/")), "INVALID_JSON_POINTER")
    current = document
    for raw in path.split("/")[1:] if path else []:
        require(not re.search(r"~(?![01])", raw), f"INVALID_JSON_POINTER_ESCAPE {path}")
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            require(bool(re.fullmatch(r"0|[1-9][0-9]*", token)), f"INVALID_ARRAY_INDEX {path}")
            require(int(token) < len(current), f"POINTER_MISSING {path}")
            current = current[int(token)]
        elif isinstance(current, dict):
            require(token in current, f"POINTER_MISSING {path}")
            current = current[token]
        else:
            raise ValueError(f"POINTER_MISSING {path}")
    return current


def format_value(value: object, specification: str) -> str:
    if specification == "integer":
        require(type(value) in (int, float) and float(value).is_integer(), "FORMAT_INTEGER_TYPE")
        return str(int(value))
    if specification.startswith("fixed:"):
        digits = int(specification.split(":")[1])
        require(type(value) in (int, float), "FORMAT_FIXED_TYPE")
        rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN)
        return f"{rounded:.{digits}f}"
    if specification == "json":
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False, sort_keys=True)
    require(specification == "string" and isinstance(value, str), "FORMAT_STRING_TYPE")
    return value


def extract(text_value: str, filename: str) -> tuple[list[dict], list[str]]:
    tokens = list(MARKER.finditer(text_value))
    errors = []
    if len(tokens) != len(MARKER_START.findall(text_value)):
        errors.append(f"MALFORMED_BINDING file={filename}")
    stack, spans = [], []
    for match in tokens:
        closing, kind, key = match.groups()
        if not closing:
            if any(entry[1] == kind for entry in stack):
                errors.append(f"NESTED_BINDING file={filename} kind={kind}")
            stack.append((match, kind, key))
            continue
        if not stack or (stack[-1][1], stack[-1][2]) != (kind, key):
            errors.append(f"UNBALANCED_BINDING file={filename} kind={kind} key={key}")
            continue
        opening, _, _ = stack.pop()
        spans.append({"kind": kind, "key": key, "start": opening.start(), "end": match.end(),
                      "content": text_value[opening.end():match.start()].strip(), "file": filename})
    for _, kind, key in stack:
        errors.append(f"UNCLOSED_BINDING file={filename} kind={kind} key={key}")
    return spans, errors


def audit(root: Path, stage: str, contract_name: str | None) -> tuple[str, list[str], dict[str, int]]:
    no_links(root)
    require(root.is_dir(), "PROJECT_ROOT_MISSING")
    if contract_name is None:
        state_path = root / "project-state.json"
        if state_path.exists():
            no_links(state_path)
            state = read_json(state_path)
            require(isinstance(state, dict), "INVALID_PROJECT_STATE")
            if "task_contract" in state:
                contract_name = text(state["task_contract"], "task_contract")
        if contract_name is None:
            no_links(root / "task-contract.json")
            if not (root / "task-contract.json").exists():
                return "LEGACY_UNCHECKED", [], {}
            contract_name = "task-contract.json"
    contract_path = safe_path(root, contract_name)
    require(contract_path.is_file(), f"DECLARED_CONTRACT_MISSING {contract_name}")
    contract = fields(read_json(contract_path),
                      {"schema_version", "questions", "required_artifacts", "results", "documents"},
                      {"description"}, "contract")
    require(contract["schema_version"] == "1.0.0", "UNSUPPORTED_CONTRACT_SCHEMA")
    for name in ("questions", "required_artifacts", "results", "documents"):
        require(isinstance(contract[name], list), f"INVALID_ARRAY {name}")
    require(bool(contract["questions"]), "EMPTY_QUESTIONS fill the task contract before advancing")
    require(bool(contract["documents"]), "EMPTY_DOCUMENTS")
    active = STAGES.index(stage)
    errors, question_ids, result_keys, documents = [], set(), set(), {}
    for row in contract["documents"]:
        fields(row, {"path", "from_stage"}, {"result_occurrences"}, "document")
        safe_path(root, row["path"])
        stage_index(row)
        require(row["path"] not in documents, f"DUPLICATE_DOCUMENT {row['path']}")
        require(Path(row["path"]).suffix.lower() in (".md", ".txt"), "DOCUMENT_TYPE only md and txt are scanned")
        if "result_occurrences" in row:
            require(isinstance(row["result_occurrences"], dict)
                    and all(isinstance(key, str) and type(count) is int and count >= 0
                            for key, count in row["result_occurrences"].items()), "INVALID_RESULT_OCCURRENCES")
        documents[row["path"]] = row
    for row in contract["required_artifacts"]:
        fields(row, {"path", "from_stage"}, set(), "artifact")
        local = safe_path(root, row["path"])
        if stage_index(row) <= active and not local.is_file():
            errors.append(f"MISSING_CONTRACT_ARTIFACT {row['path']}")
    for row in contract["results"]:
        fields(row, {"key", "source_file", "pointer", "format", "unit", "scope", "run_id_pointer", "run_id", "source_sha256", "from_stage"},
               {"identity_guards"}, "result")
        key = identifier(row["key"], "result.key")
        require(key not in result_keys, f"DUPLICATE_RESULT_KEY {key}")
        result_keys.add(key)
        safe_path(root, row["source_file"])
        stage_index(row)
        for name in ("unit", "scope", "run_id", "run_id_pointer"):
            text(row[name], "result." + name)
        require(isinstance(row["pointer"], str), "INVALID_JSON_POINTER")
        require(isinstance(row["format"], str) and
                (row["format"] in ("integer", "json", "string") or re.fullmatch(r"fixed:(?:[0-9]|1[0-2])", row["format"])), "INVALID_FORMAT")
        require(isinstance(row["source_sha256"], str) and bool(re.fullmatch(r"[a-fA-F0-9]{64}", row["source_sha256"])), "INVALID_SOURCE_HASH")
        require(isinstance(row.get("identity_guards", []), list), "INVALID_IDENTITY_GUARDS")
        for guard in row.get("identity_guards", []):
            fields(guard, {"pointer", "equals"}, set(), "identity_guard")
            require(isinstance(guard["pointer"], str), "INVALID_GUARD_POINTER")
    for row in contract["questions"]:
        fields(row, {"id", "prompt", "answer_file", "answer_marker", "required_result_keys", "from_stage"}, set(), "question")
        key = identifier(row["id"], "question.id")
        require(key not in question_ids, f"DUPLICATE_QUESTION_ID {key}")
        question_ids.add(key)
        text(row["prompt"], "question.prompt")
        require(not PLACEHOLDER.search(row["prompt"]), f"PLACEHOLDER_QUESTION {key}")
        identifier(row["answer_marker"], "question.answer_marker")
        safe_path(root, row["answer_file"])
        require(row["answer_file"] in documents, f"UNDECLARED_ANSWER_DOCUMENT {key}")
        due = stage_index(row)
        require(stage_index(documents[row["answer_file"]]) <= due, f"ANSWER_DOCUMENT_DUE_AFTER_QUESTION {key}")
        require(isinstance(row["required_result_keys"], list)
                and all(isinstance(k, str) and k in result_keys for k in row["required_result_keys"]), f"UNKNOWN_REQUIRED_RESULT {key}")
        require(len(set(row["required_result_keys"])) == len(row["required_result_keys"]), f"DUPLICATE_REQUIRED_RESULT {key}")
        for result in contract["results"]:
            if result["key"] in row["required_result_keys"]:
                require(stage_index(result) <= due, f"RESULT_DUE_AFTER_QUESTION {key}")
    markers = [row["answer_marker"] for row in contract["questions"]]
    require(len(set(markers)) == len(markers), "DUPLICATE_ANSWER_MARKER")
    for row in documents.values():
        require(set(row.get("result_occurrences", {})) <= result_keys, "UNKNOWN_OCCURRENCE_RESULT_KEY")
    expected = {}
    for row in contract["results"]:
        if stage_index(row) > active:
            continue
        try:
            path = safe_path(root, row["source_file"])
            require(path.is_file(), f"RESULT_SOURCE_MISSING key={row['key']}")
            require(hashlib.sha256(path.read_bytes()).hexdigest().lower() == row["source_sha256"].lower(), f"STALE_RESULT_SOURCE key={row['key']}")
            source = read_json(path)
            require(pointer(source, row["run_id_pointer"]) == row["run_id"], f"RUN_ID_CONFLICT key={row['key']}")
            for guard in row.get("identity_guards", []):
                require(pointer(source, guard["pointer"]) == guard["equals"], f"RESULT_IDENTITY_CONFLICT key={row['key']}")
            expected[row["key"]] = format_value(pointer(source, row["pointer"]), row["format"])
        except (ValueError, OSError, UnicodeError) as error:
            errors.append(str(error))
    spans = []
    for name, row in documents.items():
        if stage_index(row) > active:
            continue
        path = safe_path(root, name)
        if not path.is_file():
            errors.append(f"MISSING_CONTRACT_DOCUMENT {name}")
            continue
        found, marker_errors = extract(path.read_text(encoding="utf-8-sig"), name)
        spans.extend(found)
        errors.extend(marker_errors)
        if "result_occurrences" in row:
            actual_counts = {}
            for span in found:
                if span["kind"] == "result":
                    actual_counts[span["key"]] = actual_counts.get(span["key"], 0) + 1
            for key in actual_counts.keys() | row["result_occurrences"].keys():
                expected_count = row["result_occurrences"].get(key, 0)
                actual_count = actual_counts.get(key, 0)
                if expected_count != actual_count:
                    errors.append(f"RESULT_OCCURRENCE_CONFLICT file={name} key={key} expected={expected_count} actual={actual_count}")
    references = [span for span in spans if span["kind"] == "result"]
    for span in spans:
        if span["kind"] == "answer" and span["key"] not in markers:
            errors.append(f"UNKNOWN_ANSWER_MARKER {span['key']}")
    for span in references:
        key = span["key"]
        if key not in result_keys:
            errors.append(f"UNKNOWN_RESULT_KEY {key} file={span['file']}")
        elif key in expected and span["content"] != expected[key]:
            errors.append(f"RESULT_TEXT_CONFLICT key={key} file={span['file']} expected={expected[key]!r} actual={span['content']!r}")
    for key in expected:
        if not any(span["key"] == key for span in references):
            errors.append(f"MISSING_RESULT_REFERENCE key={key}")
    due_questions = 0
    for row in contract["questions"]:
        if stage_index(row) > active:
            continue
        due_questions += 1
        answers = [span for span in spans if span["kind"] == "answer" and span["key"] == row["answer_marker"]]
        if len(answers) != 1 or answers[0]["file"] != row["answer_file"]:
            errors.append(f"QUESTION_UNANSWERED_OR_AMBIGUOUS id={row['id']}")
            continue
        answer = answers[0]
        content = MARKER.sub("", answer["content"]).strip()
        if not content or PLACEHOLDER.search(content):
            errors.append(f"EMPTY_OR_PLACEHOLDER_ANSWER id={row['id']}")
        for key in row["required_result_keys"]:
            if not any(span["key"] == key and span["file"] == answer["file"]
                       and answer["start"] < span["start"] < span["end"] < answer["end"] for span in references):
                errors.append(f"QUESTION_RESULT_MISSING id={row['id']} key={key}")
    counters = {"DECLARED_QUESTIONS": len(question_ids), "ACTIVE_QUESTIONS": due_questions,
                "ACTIVE_RESULTS": len(expected), "CHECKED_RESULT_REFERENCES": sum(span["key"] in expected for span in references),
                "DOCUMENTS_WITHOUT_OCCURRENCE_CONTRACT": sum("result_occurrences" not in row for row in documents.values())}
    return "FAIL" if errors else "PASS", errors, counters


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--stage", choices=STAGES, default="validation")
    parser.add_argument("--contract")
    args = parser.parse_args()
    try:
        root = Path(os.path.abspath(args.project_root))
        status, errors, counters = audit(root, args.stage, args.contract)
    except (ValueError, OSError, UnicodeError, TypeError, KeyError, ArithmeticError) as error:
        status, errors, counters = "FAIL", [str(error)], {}
    print(f"CONTRACT_STATUS={status}")
    print("CONTRACT_SCOPE=DECLARED_QUESTIONS_ARTIFACTS_AND_TEXT_BINDINGS_ONLY")
    print("SCIENTIFIC_AND_HUMAN_REVIEW=NOT_EVALUATED")
    print("UNBOUND_PROSE_PDF_AND_IMAGE_CONTENT=NOT_SCANNED")
    for name, value in counters.items():
        print(f"{name}={value}")
    for error in errors:
        print(f"CONTRACT_ERROR={error}")
    return int(status == "FAIL")


if __name__ == "__main__":
    sys.exit(main())
