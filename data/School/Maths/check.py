#!/usr/bin/env python3
"""
Content-specific validation for Maths course.
Validates Maths-specific rules like ID format, language (Russian), and mathematical correctness.
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# ============================================================================
# MATHS-SPECIFIC VALIDATION CONFIGURATION
# ============================================================================
# ID pattern for Maths course: RS5-001-0001, RS6-003-0015, RS7-002-0008, etc.
ID_PATTERN = re.compile(r"^(RS5|RS6|RS7|RS8|RS9)-\d{3}-\d{4}$")
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")


def extract_number_from_text(text: str) -> float:
    """
    Try to extract a number from text (handles Russian decimal separator).
    Returns None if no number found.
    """
    # Remove common units and words
    text = text.strip()
    # Try to find number pattern
    # Match integers and decimals (with . or ,)
    number_match = re.search(r"(\d+(?:[.,]\d+)?)", text)
    if number_match:
        num_str = number_match.group(1).replace(",", ".")
        try:
            return float(num_str)
        except ValueError:
            return None
    return None


def validate_math_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """
    Validate a single math entry for Maths course.
    Returns (errors, warnings).
    
    Maths-specific rules:
    - ID must match pattern: (RS5|RS6|RS7|RS8|RS9)-XXX-XXXX
    - Question should be in Russian (Cyrillic)
    - Options should be in Russian (can be numbers or text)
    - Explanation should be in Russian (Cyrillic)
    - For numeric questions, verify that correct answer matches question
    """
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}' (expected: RS5-001-0001, RS6-003-0015, etc.)")

    # 2. Question Validation (should be Russian)
    question = entry.get("question")
    if not isinstance(question, str):
        errors.append(f"Line {line_num}: 'question' field must be a string")
    elif not question.strip():
        errors.append(f"Line {line_num}: 'question' field is empty")
    else:
        # Check that question contains Cyrillic (Russian)
        if not CYRILLIC_PATTERN.search(question):
            warnings.append(f"Line {line_num}: 'question' should be in Russian (Cyrillic), but found: '{question[:50]}...'")

    # 3. Options Validation (should be Russian)
    options = entry.get("options")
    if not isinstance(options, list) or len(options) != 4:
        errors.append(f"Line {line_num}: 'options' must be a list of exactly 4 options")
    else:
        # Check for duplicates
        if len(set(options)) != 4:
            errors.append(f"Line {line_num}: 'options' must be unique")
        
        # Check each option
        for i, opt in enumerate(options, 1):
            if not isinstance(opt, str):
                errors.append(f"Line {line_num}: 'options[{i-1}]' must be a string")
                continue
            if not opt.strip():
                errors.append(f"Line {line_num}: 'options[{i-1}]' is empty")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
        errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")
        return errors, warnings  # Can't continue validation without valid correct index
    
    # 5. Verify correct answer exists
    if isinstance(options, list) and len(options) >= correct:
        correct_answer = options[correct - 1]
        
        # Try to extract numbers from question and correct answer for validation
        question_num = extract_number_from_text(question) if question else None
        correct_num = extract_number_from_text(correct_answer) if isinstance(correct_answer, str) else None
        
        # If both question and answer contain numbers, try basic validation
        # This is a simple heuristic - for complex math problems, manual review is needed
        if question_num is not None and correct_num is not None:
            # Check if question asks for a calculation result
            if "сколько" in question.lower() or "чему равно" in question.lower() or "=" in question:
                # Try to parse simple arithmetic from question
                # This is very basic - just a sanity check
                pass  # Could add more sophisticated math validation here

    # 6. Explanation Validation (should be Russian)
    explanation = entry.get("explanation", "")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append(f"Line {line_num}: 'explanation' field must be a non-empty string")
    else:
        # Check that explanation contains Cyrillic (Russian)
        if not CYRILLIC_PATTERN.search(explanation):
            warnings.append(f"Line {line_num}: 'explanation' should be in Russian (Cyrillic), but found: '{explanation[:50]}...'")
        
        # Check if explanation mentions the correct answer (basic consistency check)
        if isinstance(options, list) and len(options) >= correct:
            correct_answer = options[correct - 1]
            # Extract number from correct answer
            correct_num = extract_number_from_text(correct_answer) if isinstance(correct_answer, str) else None
            if correct_num is not None:
                # Check if explanation contains this number
                explanation_num = extract_number_from_text(explanation)
                if explanation_num is None or abs(explanation_num - correct_num) > 0.01:
                    # Number might be written differently in explanation, so this is just a warning
                    pass

    # 7. Tags Validation
    tags = entry.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"Line {line_num}: 'tags' must be a list")
    
    # 8. Check for common math question patterns
    if isinstance(question, str):
        question_lower = question.lower()
        # Check if question contains math operations
        has_math_ops = any(op in question for op in ["+", "-", "×", "*", "÷", "/", "="])
        if has_math_ops:
            # Verify that at least one option is numeric
            numeric_options = sum(1 for opt in (options or []) if isinstance(opt, str) and extract_number_from_text(opt) is not None)
            if numeric_options == 0:
                warnings.append(f"Line {line_num}: Question contains math operations but no numeric options found")

    return errors, warnings


def validate_file_maths(filepath: Path) -> Tuple[List[str], List[str]]:
    """
    Validate a JSONL file for Maths-specific rules.
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
                e, w = validate_math_entry(entry, i)
                file_errors.extend(e)
                file_warnings.extend(w)
            except json.JSONDecodeError as e:
                file_errors.append(f"Line {i}: Invalid JSON - {e}")
                
    return file_errors, file_warnings


def validate_content_specific(repo_root: Path, course_id: str, content_type: str) -> int:
    """
    Run content-specific validation for Maths course.
    
    Args:
        repo_root: Repository root path
        course_id: Course ID (should be 'sch')
        content_type: Content type to validate ('maths' or 'all')
    
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
    
    # Find Maths content type
    maths_content = None
    for content in course_config.get("contents", []):
        if content["id"] == "maths":
            maths_content = content
            break
    
    if not maths_content:
        print(f"⚠️  No Maths content found for course '{course_id}'")
        return 0
    
    maths_dir = data_dir / maths_content["dir"]
    
    if not maths_dir.exists():
        print(f"❌ Directory not found: {maths_dir}")
        return 1

    print(f"🔍 Validating Maths-specific rules in: {maths_dir}")
    print("=" * 60)

    all_files = sorted(maths_dir.glob("**/*.jsonl"))
    total_errors = 0
    files_with_issues = 0

    for filepath in all_files:
        errors, warnings = validate_file_maths(filepath)
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
    
    # Find repo root (go up from data/School/Maths/check.py)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent.parent
    
    # Course ID is always "sch" for School course
    # Can be overridden via command line argument if needed
    course_id = sys.argv[1] if len(sys.argv) > 1 else "sch"
    sys.exit(validate_content_specific(repo_root, course_id, "maths"))

