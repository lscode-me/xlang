#!/usr/bin/env python3
"""
Content-specific validation for EnWords course.
Validates EnWords-specific rules like ID format, language of questions (Russian) and options (English).
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ============================================================================
# ENWORDS-SPECIFIC VALIDATION CONFIGURATION
# ============================================================================
# ID pattern for EnWords course: A1-001-0001, A2-003-0015
ID_PATTERN = re.compile(r"^(A1|A2)-\d{3}-\d{4}$")
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")
LATIN_PATTERN = re.compile(r"[a-zA-Z]")


def validate_word_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single word entry for EnWords course.
    Returns (errors, warnings).
    
    EnWords-specific rules:
    - ID must match pattern: (A1|A2)-XXX-XXXX
    - Question should be a single Russian word (Cyrillic)
    - Options must be in English (Latin, no Cyrillic)
    - Explanation should be in Russian (Cyrillic)
    """
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}' (expected: A1-001-0001, A2-003-0015, etc.)")

    # 2. Question Validation (should be a single Russian word)
    question = entry.get("question")
    if not isinstance(question, str):
        errors.append(f"Line {line_num}: 'question' field must be a string")
    elif not question.strip():
        errors.append(f"Line {line_num}: 'question' field is empty")
    else:
        # Check that question contains Cyrillic (Russian)
        if not CYRILLIC_PATTERN.search(question):
            errors.append(f"Line {line_num}: 'question' should be in Russian (Cyrillic), but found: '{question}'")
        # Check that it's a single word (warning if multiple)
        word_count = len(question.strip().split())
        if word_count > 1:
            warnings.append(f"Line {line_num}: 'question' contains multiple words: '{question}' (expected a single word)")

    # 3. Options Validation (should be English, no Cyrillic)
    options = entry.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append(f"Line {line_num}: 'options' must be a list of exactly 4 options")
    else:
        # Check for duplicates
        if len(set(options)) != 4:
            errors.append(f"Line {line_num}: 'options' must be unique")
        
        # Check each option for Cyrillic (should be English only)
        for i, opt in enumerate(options, 1):
            if not isinstance(opt, str):
                errors.append(f"Line {line_num}: 'options[{i-1}]' must be a string")
                continue
            if CYRILLIC_PATTERN.search(opt):
                errors.append(f"Line {line_num}: 'options[{i-1}]' '{opt}' contains Cyrillic characters (should be English)")
            # Check that option contains at least some Latin letters (English)
            if opt.strip() and not LATIN_PATTERN.search(opt):
                warnings.append(f"Line {line_num}: 'options[{i-1}]' '{opt}' doesn't contain Latin letters (might not be English)")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
        errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")

    # 5. Explanation Validation (should be Russian)
    explanation = entry.get("explanation", "")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append(f"Line {line_num}: 'explanation' field must be a non-empty string")
    else:
        # Check that explanation contains Cyrillic (Russian)
        if not CYRILLIC_PATTERN.search(explanation):
            warnings.append(f"Line {line_num}: 'explanation' should be in Russian (Cyrillic), but found: '{explanation[:50]}...'")

    # 6. Tags Validation
    tags = entry.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"Line {line_num}: 'tags' must be a list")

    return errors, warnings


def validate_file_words(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Validate a JSONL file for EnWords-specific rules.
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
    Run content-specific validation for EnWords course.
    
    Args:
        repo_root: Repository root path
        course_id: Course ID (should be 'sch')
        content_type: Content type to validate ('words' or 'all')
    
    Returns:
        0 on success, 1 on failure
    """
    if course_id != "sch":
        # This module is only for School course
        return 0
    
    # Import here to avoid circular dependencies
    import sys
    sys.path.insert(0, str(repo_root / "build"))
    from check_data import get_course_config
    
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        print(f"❌ Course '{course_id}' not found in config.json")
        return 1
    
    course_name = course_config["name"]
    data_dir = repo_root / "data" / course_name
    
    # Find EnWords content type
    words_content = None
    for content in course_config.get("contents", []):
        if content["id"] == "enwords":
            words_content = content
            break
    
    if not words_content:
        print(f"⚠️  No EnWords content found for course '{course_id}'")
        return 0
    
    words_dir = data_dir / words_content["dir"]
    
    if not words_dir.exists():
        print(f"❌ Directory not found: {words_dir}")
        return 1

    print(f"🔍 Validating EnWords-specific rules in: {words_dir}")
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
    
    # Find repo root (go up from data/School/EnWords/check.py)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent.parent
    
    # Course ID is always "sch" for School course
    # Can be overridden via command line argument if needed
    course_id = sys.argv[1] if len(sys.argv) > 1 else "sch"
    sys.exit(validate_content_specific(repo_root, course_id, "words"))

