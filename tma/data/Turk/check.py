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
# ID patterns
ID_PATTERN = re.compile(r"^(A1|A2|B1)-\d{3}-\d{4}$")
QUIZ_ID_PATTERN = re.compile(r"^(L1|L2|L3)-\d{3}-\d{4}$")
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


def validate_quiz_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single quiz entry for Turk course.
    Returns (errors, warnings).
    
    Turk-specific rules for quizzes:
    - ID must match pattern: (L1|L2|L3)-XXX-XXXX
    - Question must NOT contain Cyrillic characters (should be Turkish)
    - Options must NOT contain Cyrillic characters (should be Turkish)
    - Explanation MUST contain Cyrillic characters (should be in Russian)
    - Explanation must contain separator ('—' or '-')
    """
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not QUIZ_ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}' (expected: L1-001-0001, L2-003-0015, etc.)")

    # 2. Question Validation
    question = entry.get("question")
    if not isinstance(question, str):
        errors.append(f"Line {line_num}: 'question' field must be a string")
    elif not question.strip():
        errors.append(f"Line {line_num}: 'question' field is empty")
    elif CYRILLIC_PATTERN.search(question):
        errors.append(f"Line {line_num}: 'question' field contains Cyrillic characters (should be Turkish)")

    # 3. Options Validation
    options = entry.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append(f"Line {line_num}: 'options' must be a list of exactly 4 options")
    else:
        # Check for duplicates
        if len(set(options)) != 4:
            errors.append(f"Line {line_num}: 'options' options must be unique")
        
        # Check each option for Cyrillic (should be Turkish)
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

    # 5. Explanation Validation (must contain separator and Russian Cyrillic characters)
    explanation = entry.get("explanation", "")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append(f"Line {line_num}: 'explanation' field must be a non-empty string")
    else:
        if "—" not in explanation and "-" not in explanation:
            errors.append(f"Line {line_num}: 'explanation' must contain at least one separator ('—' or '-')")
        if not CYRILLIC_PATTERN.search(explanation):
            warnings.append(f"Line {line_num}: 'explanation' should be in Russian, but no Cyrillic characters found")

    # 6. Tags Validation
    tags = entry.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"Line {line_num}: 'tags' must be a list")

    return errors, warnings


def validate_file_quizzes(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Validate a JSONL file for Turk-specific quiz rules.
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
                e, w = validate_quiz_entry(entry, i)
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
        content_type: Content type to validate ('words', 'quizzes', or 'all')
    
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
    
    # Find Word and Quiz contents
    words_content = None
    quizzes_content = None
    for content in course_config.get("contents", []):
        content_id_lower = content["id"].lower()
        if "words" in content_id_lower:
            words_content = content
        elif "quiz" in content_id_lower:
            quizzes_content = content
            
    total_errors = 0
    
    # 1. Validate Words (if category matches or is 'all')
    if words_content and content_type in ["words", "all"]:
        words_dir = data_dir / words_content.get("dir", words_content["id"])
        if words_dir.exists():
            print(f"🔍 Validating Turk-specific Words in: {words_dir}")
            print("=" * 60)
            
            all_files = sorted(words_dir.glob("**/*.jsonl"))
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
            
            if total_errors == 0:
                if files_with_issues > 0:
                    print(f"\n✨ Words validated with warnings. Scanned {len(all_files)} files.")
                else:
                    print(f"\n✨ Words validated successfully. Scanned {len(all_files)} files. No issues found.")
            print("-" * 60)
            
    # 2. Validate Quizzes (if category matches or is 'all')
    if quizzes_content and content_type in ["quizzes", "all"]:
        quizzes_dir = data_dir / quizzes_content.get("dir", quizzes_content["id"])
        if quizzes_dir.exists():
            print(f"🔍 Validating Turk-specific Quizzes in: {quizzes_dir}")
            print("=" * 60)
            
            all_files = sorted(quizzes_dir.glob("**/*.jsonl"))
            files_with_issues = 0
            quiz_errors = 0
            for filepath in all_files:
                errors, warnings = validate_file_quizzes(filepath)
                if errors or warnings:
                    files_with_issues += 1
                    rel_path = filepath.relative_to(repo_root)
                    print(f"\n📂 {rel_path}")
                    for err in errors:
                        print(f"  ❌ ERROR: {err}")
                    for warn in warnings:
                        print(f"  ⚠️  WARNING: {warn}")
                    quiz_errors += len(errors)
            
            total_errors += quiz_errors
            if quiz_errors == 0:
                if files_with_issues > 0:
                    print(f"\n✨ Quizzes validated with warnings. Scanned {len(all_files)} files.")
                else:
                    print(f"\n✨ Quizzes validated successfully. Scanned {len(all_files)} files. No issues found.")
            print("-" * 60)

    if total_errors > 0:
        print(f"\nFAILED. Found {total_errors} errors total.")
        return 1
    return 0


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Find repo root (go up from data/Turk/check.py)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    
    if len(sys.argv) < 2:
        print("❌ Usage: python check.py <course_id> [content_type]")
        sys.exit(1)
    
    course_id = sys.argv[1]
    content_type = sys.argv[2] if len(sys.argv) > 2 else "all"
    sys.exit(validate_content_specific(repo_root, course_id, content_type))
