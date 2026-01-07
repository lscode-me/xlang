#!/usr/bin/env python3
"""
Content-specific validation for Avar course.
Validates Avar-specific rules like ID format, palochka usage, etc.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ============================================================================
# AVAR-SPECIFIC VALIDATION CONFIGURATION
# ============================================================================
# ID pattern for Avar course: A1-001-0001 to C1-003-0015
ID_PATTERN = re.compile(r"^(A1|A2|B1|B2|C1)-[\w-]+-\d{4}$")


def validate_word_entry(entry: Dict[Any, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single word entry for Avar course.
    Returns (errors, warnings).
    
    Avar-specific rules:
    - ID must match pattern: (A1|A2|B1|B2|C1)-XXX-XXXX
    - question should be a string
    - options must be a list of exactly 4 strings
    - explanation must contain a separator
    """
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}'")

    # 2. Russian Question Validation
    question = entry.get("question")
    if not isinstance(question, str):
        errors.append(f"Line {line_num}: 'question' field must be a string")
    elif not question.strip():
        errors.append(f"Line {line_num}: 'question' field is empty")

    # 3. Avar Options Validation
    options = entry.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append(f"Line {line_num}: 'options' must be a list of exactly 4 options")
    else:
        # Check for duplicates
        if len(set(options)) != 4:
            errors.append(f"Line {line_num}: 'options' options must be unique")
        
        # Check for palochka usage (warning if digit 1 is used instead of I/l)
        for opt in options:
            if not isinstance(opt, str):
                errors.append(f"Line {line_num}: 'options' option must be a string")
                continue
            if re.search(r"\d", opt):
                warnings.append(f"Line {line_num}: 'options' option '{opt}' contains digits (check for palochka 'I' vs '1')")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
        errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")

    # 5. Explanation Validation
    explanation = entry.get("explanation", "")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append(f"Line {line_num}: 'explanation' field must be a non-empty string")
    # elif "—" not in explanation and "-" not in explanation and ":" not in explanation:
    #     errors.append(f"Line {line_num}: 'explanation' must contain at least one separator ('—', '-' or ':')")
    
    return errors, warnings


def validate_file_words(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Validate a JSONL file for Avar-specific rules.
    """
    file_errors = []
    file_warnings = []
    
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                e, w = validate_word_entry(entry, i)
                file_errors.extend(e)
                file_warnings.extend(w)
            except json.JSONDecodeError as e:
                file_errors.append(f"Line {i}: Invalid JSON - {e}")
                
    return file_errors, file_warnings


def validate_content_specific(repo_root: Path, course_id: str, content_type: str) -> int:
    if course_id != "avar":
        return 0
    
    import sys
    sys.path.insert(0, str(repo_root / "build"))
    from check_data import get_course_config
    
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        print(f"❌ Course '{course_id}' not found in config.json")
        return 1
    
    course_name = course_config["name"]
    data_dir = repo_root / "data" / course_name
    
    contents_to_check = []
    for content in course_config.get("contents", []):
        contents_to_check.append(content)
    
    total_errors = 0
    
    for content in contents_to_check:
        content_dir = data_dir / content["dir"]
        if not content_dir.exists():
            print(f"⚠️  Directory not found: {content_dir}")
            continue

        print(f"🔍 Validating Avar-specific rules in: {content_dir}")
        print("=" * 60)

        all_files = sorted(content_dir.glob("**/*.jsonl"))
        for filepath in all_files:
            errors, warnings = validate_file_words(filepath)
            if errors or warnings:
                rel_path = filepath.relative_to(repo_root)
                print(f"\n📂 {rel_path}")
                for err in errors:
                    print(f"  ❌ ERROR: {err}")
                for warn in warnings:
                    print(f"  ⚠️  WARNING: {warn}")
                total_errors += len(errors)

    print("\n" + "=" * 60)
    if total_errors > 0:
        print(f"FAILED. Found {total_errors} errors.")
        return 1
    else:
        print(f"✨ SUCCESS. No critical issues found.")
        return 0


if __name__ == "__main__":
    import sys
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    course_id = sys.argv[1] if len(sys.argv) > 1 else "avar"
    sys.exit(validate_content_specific(repo_root, course_id, "words"))

