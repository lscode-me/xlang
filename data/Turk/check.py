#!/usr/bin/env python3
"""
Content-specific validation for Turk course.
Validates Turk-specific rules like ID format, Cyrillic in options, etc.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ============================================================================
# TURK-SPECIFIC VALIDATION CONFIGURATION
# ============================================================================
# ID pattern for Turk course: A1-001-0001, A2-003-0015, B1-002-0008
ID_PATTERN = re.compile(r"^(A1|A2|B1)-\d{3}-\d{4}$")
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")


def validate_word_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single word entry for Turk course.
    Returns (errors, warnings).
    
    Turk-specific rules:
    - ID must match pattern: (A1|A2|B1)-XXX-XXXX
    - Question should be a single word (warning if multiple)
    - Options must not contain Cyrillic characters
    - Question word should be present in explanation
    """
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}' (expected: A1-001-0001, A2-003-0015, etc.)")

    # 2. Question Validation
    question = entry.get("question")
    if not isinstance(question, str):
        errors.append(f"Line {line_num}: 'question' field must be a string")
    elif not question.strip():
        errors.append(f"Line {line_num}: 'question' field is empty")
    elif " " in question.strip():
        warnings.append(f"Line {line_num}: 'question' field contains multiple words: '{question}'")

    # 3. Options Validation
    options = entry.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append(f"Line {line_num}: 'options' must be a list of exactly 4 options")
    else:
        # Check for duplicates
        if len(set(options)) != 4:
            errors.append(f"Line {line_num}: 'options' options must be unique")
        
        # Check each option for Cyrillic (Turk-specific: options should be Turkish, not Russian)
        for opt in options:
            if not isinstance(opt, str):
                errors.append(f"Line {line_num}: 'options' option must be a string")
                continue
            if CYRILLIC_PATTERN.search(opt):
                errors.append(f"Line {line_num}: 'options' option '{opt}' contains Cyrillic characters (should be Turkish)")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
        errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")

    # 5. Explanation Validation (Turk-specific: must contain separator)
    explanation = entry.get("explanation", "")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append(f"Line {line_num}: 'explanation' field must be a non-empty string")
    elif "—" not in explanation and "-" not in explanation:
        errors.append(f"Line {line_num}: 'explanation' must contain at least one separator ('—' or '-')")
    
    # 6. Consistency Check (Turk-specific: Russian word should be in explanation)
    if isinstance(explanation, str) and isinstance(question, str) and question.lower() not in explanation.lower():
        warnings.append(f"Line {line_num}: 'question' word '{question}' not found in 'explanation'")

    # 7. Tags Validation
    tags = entry.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"Line {line_num}: 'tags' must be a list")

    return errors, warnings


def validate_file_words(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Validate a JSONL file for Turk-specific word rules.
    Returns (errors, warnings).
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
    """
    Run content-specific validation for Turk course.
    
    Args:
        repo_root: Repository root path
        course_id: Course ID (should be 'turk')
        content_type: Content type to validate ('words', 'phrases', 'grammar', or 'all')
    
    Returns:
        0 on success, 1 on failure
    """
    if course_id != "turk":
        # This module is only for Turk course
        return 0
    
    # Import here to avoid circular dependencies
    import sys
    import json
    sys.path.insert(0, str(repo_root / "build"))
    from check_data import get_course_config
    
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        print(f"❌ Course '{course_id}' not found in config.json")
        return 1
    
    course_name = course_config["name"]
    data_dir = repo_root / "data" / course_name
    
    # Find Words content type
    words_content = None
    for content in course_config.get("contents", []):
        if "Words" in content["id"]:
            words_content = content
            break
    
    if not words_content:
        print(f"⚠️  No Words content found for course '{course_id}'")
        return 0
    
    words_dir = data_dir / words_content["id"]
    
    if not words_dir.exists():
        print(f"❌ Directory not found: {words_dir}")
        return 1

    print(f"🔍 Validating Turk-specific rules in: {words_dir}")
    print("=" * 60)

    all_files = sorted(words_dir.glob("**/*.jsonl"))
    total_errors = 0
    files_with_issues = 0

    for filepath in all_files:
        errors, warnings = validate_file_words(filepath)
        if errors or warnings:
            files_with_issues += 1
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
        if files_with_issues > 0:
            print(f"✨ SUCCESS with warnings. Scanned {len(all_files)} files.")
        else:
            print(f"✨ SUCCESS. Scanned {len(all_files)} files. No issues found.")
        return 0


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Find repo root (go up from data/Turk/check.py)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    
    if len(sys.argv) < 2:
        print("❌ Usage: python check.py <course_id>")
        sys.exit(1)
    
    course_id = sys.argv[1]
    sys.exit(validate_content_specific(repo_root, course_id, "words"))

