#!/usr/bin/env python3
"""
Content-specific validation for Astronomy course.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ID pattern for Astronomy course: I1-001-0001, I2-003-0015, etc.
ID_PATTERN = re.compile(r"^(I1|I2)-\d{3}-\d{4}$")
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")


def validate_astronomy_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single astronomy entry.
    """
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}' (expected: I1-XXX-XXXX, I2-XXX-XXXX)")

    # 2. Question Validation
    question = entry.get("question")
    if not isinstance(question, str) or not question.strip():
        errors.append(f"Line {line_num}: 'question' field must be a non-empty string")
    elif not CYRILLIC_PATTERN.search(question):
        warnings.append(f"Line {line_num}: 'question' should be in Russian (Cyrillic)")

    # 3. Options Validation
    options = entry.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append(f"Line {line_num}: 'options' must be a list of exactly 4 options")
    else:
        if len(set(options)) != 4:
            errors.append(f"Line {line_num}: 'options' must be unique")
        for i, opt in enumerate(options):
            if not isinstance(opt, str) or not opt.strip():
                errors.append(f"Line {line_num}: option {i} must be a non-empty string")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
        errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")
    
    # 5. Explanation Validation
    explanation = entry.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append(f"Line {line_num}: 'explanation' field must be a non-empty string")
    elif not CYRILLIC_PATTERN.search(explanation):
        warnings.append(f"Line {line_num}: 'explanation' should be in Russian (Cyrillic)")

    return errors, warnings


def validate_file_astronomy(filepath: Path) -> Tuple[List[str], List[str]]:
    file_errors = []
    file_warnings = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line: continue
            try:
                entry = json.loads(line)
                e, w = validate_astronomy_entry(entry, i)
                file_errors.extend(e)
                file_warnings.extend(w)
            except json.JSONDecodeError as e:
                file_errors.append(f"Line {i}: Invalid JSON - {e}")
    return file_errors, file_warnings


def validate_content_specific(repo_root: Path, course_id: str, content_type: str) -> int:
    if course_id != "sch": return 0
    import sys
    sys.path.insert(0, str(repo_root / "build"))
    from check_data import get_course_config
    course_config = get_course_config(repo_root, course_id)
    if not course_config: return 1
    
    data_dir = repo_root / "data" / course_config["name"]
    astronomy_dir = data_dir / "Astronomy"
    if not astronomy_dir.exists(): return 0
    
    print(f"🔍 Validating Astronomy-specific rules in: {astronomy_dir}")
    all_files = sorted(astronomy_dir.glob("**/*.jsonl"))
    total_errors = 0
    for filepath in all_files:
        errors, warnings = validate_file_astronomy(filepath)
        if errors or warnings:
            print(f"\n📂 {filepath.relative_to(repo_root)}")
            for err in errors: print(f"  ❌ ERROR: {err}")
            for warn in warnings: print(f"  ⚠️  WARNING: {warn}")
            total_errors += len(errors)
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    import sys
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent.parent
    sys.path.insert(0, str(repo_root))
    sys.exit(validate_content_specific(repo_root, "sch", "astronomy"))
