#!/usr/bin/env python3
"""
Universal tool for checking and managing vocabulary JSONL files.
Handles format validation, shuffling, and deduplication for all courses.

Content-specific validations are handled by course-specific check modules
(e.g., data/Turk/check.py for Turk course).

Usage:
    ./check_data.py validate-questions <course_id>  # Validate question format (universal)
    ./check_data.py shuffle <course_id>             # Shuffle answers if distribution is unbalanced
    ./check_data.py remove-duplicates <course_id>   # Remove duplicate questions
    ./check_data.py check-all <course_id>           # Run all checks (validate + content-specific + shuffle)
    ./check_data.py fix-all <course_id>             # Run all checks and fixes (deduplicate + validate + content-specific + shuffle)
"""
import json
import random
import re
import sys
from pathlib import Path
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple, Set, Optional

# ============================================================================
# SHUFFLE CONFIGURATION
# ============================================================================
SHUFFLE_DEVIATION_THRESHOLD = 0.05  # 5% deviation from 25%
SHUFFLE_TARGET_RATIO = 0.25

# ============================================================================
# VALIDATION CONFIGURATION
# ============================================================================
# LLM junk patterns
LLM_JUNK_PATTERNS = [
    r"правильный ответ",
    r"вариант\s+\d+",
    r"as an ai",
    r"chatgpt",
    r"i'?m sorry",
    r"i can'?t (help|provide|assist|answer|do that|generate|create)",
    r"openai",
]

REQUIRED_FIELDS = {"id", "question", "options", "correct", "explanation"}
OPTIONAL_FIELDS = {"tags", "source"}


# ============================================================================
# SHUFFLE FUNCTIONS
# ============================================================================
def load_questions(filepath: Path) -> List[Dict[str, Any]]:
    """Load questions from JSONL file."""
    questions = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    questions.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"⚠️ Warning: Invalid JSON in {filepath}")
    return questions


def save_questions(filepath: Path, questions: List[Dict[str, Any]]) -> None:
    """Save questions to JSONL file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")


def check_distribution(questions: List[Dict[str, Any]]) -> Dict[int, float]:
    """Calculate distribution of correct answers."""
    total = len(questions)
    if total == 0:
        return {}
    
    counts = Counter(q.get("correct") for q in questions)
    ratios = {k: counts.get(k, 0) / total for k in range(1, 5)}
    return ratios


def needs_shuffling(ratios: Dict[int, float]) -> bool:
    """Check if any option deviates more than threshold from target."""
    for opt in range(1, 5):
        ratio = ratios.get(opt, 0.0)
        deviation = abs(ratio - SHUFFLE_TARGET_RATIO)
        if deviation > SHUFFLE_DEVIATION_THRESHOLD:
            return True
    return False


def shuffle_question(question: Dict[str, Any]) -> Dict[str, Any]:
    """Shuffle options and update 'correct' index."""
    options = question.get("options", [])
    if len(options) != 4:
        return question
    
    # Get current correct answer string
    correct_idx = question.get("correct", 1) - 1  # 0-based
    if 0 <= correct_idx < len(options):
        correct_answer = options[correct_idx]
    else:
        return question

    # Shuffle
    random.shuffle(options)
    
    # Find new index
    new_correct_idx = options.index(correct_answer)
    
    # Update question
    question["options"] = options
    question["correct"] = new_correct_idx + 1  # 1-based
    
    return question


def process_shuffle_file(filepath: Path, max_iterations: int = 10) -> bool:
    """
    Process a single file for shuffling. 
    Repeats shuffling until distribution is balanced (within 5% threshold).
    
    Args:
        filepath: Path to JSONL file
        max_iterations: Maximum number of shuffle iterations (default: 10)
    
    Returns:
        True if file was modified, False otherwise
    """
    questions = load_questions(filepath)
    if not questions:
        return False

    ratios = check_distribution(questions)
    should_shuffle = needs_shuffling(ratios)
    
    # Format distribution
    dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in ratios.items()])
    display_path = f"{filepath.parent.name}/{filepath.name}"
    
    if not should_shuffle:
        print(f"  📊 {display_path}: {dist_str} -> ✅ Balanced")
        return False
    
    # Initial distribution message
    print(f"  📊 {display_path}: {dist_str} -> ⚠️  High deviation, SHUFFLING...")
    
    # Repeat shuffling until balanced or max iterations reached
    iteration = 0
    was_modified = False
    
    while iteration < max_iterations:
        iteration += 1
        
        # Shuffle all questions
        for q in questions:
            shuffle_question(q)
        
        # Check new distribution
        new_ratios = check_distribution(questions)
        
        if not needs_shuffling(new_ratios):
            # Distribution is now balanced
            new_dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in new_ratios.items()])
            print(f"     Iteration {iteration}: {new_dist_str} -> ✅ Balanced")
            save_questions(filepath, questions)
            return True
        
        # Still unbalanced, continue shuffling
        if iteration < max_iterations:
            new_dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in new_ratios.items()])
            print(f"     Iteration {iteration}: {new_dist_str} -> Still unbalanced, continuing...")
    
    # Max iterations reached
    final_ratios = check_distribution(questions)
    final_dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in final_ratios.items()])
    print(f"     Iteration {max_iterations}: {final_dist_str} -> ⚠️  Max iterations reached, saving current state")
    save_questions(filepath, questions)
    return True


# ============================================================================
# VALIDATION FUNCTIONS - QUESTIONS
# ============================================================================
def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())


def has_llm_junk(text: str) -> bool:
    """Check if text contains LLM junk markers."""
    text_lower = text.lower()
    for pattern in LLM_JUNK_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def validate_question(obj: dict, line_num: int, filepath: Path, all_ids: Set[str]) -> List[str]:
    """Validate a single question object. Returns list of errors."""
    errors = []
    
    # Check required fields
    missing_fields = REQUIRED_FIELDS - obj.keys()
    if missing_fields:
        errors.append(f"Missing required fields: {missing_fields}")
        return errors
    
    # Check extra unknown fields
    known_fields = REQUIRED_FIELDS | OPTIONAL_FIELDS
    extra_fields = set(obj.keys()) - known_fields
    if extra_fields:
        errors.append(f"Unknown fields: {extra_fields}")
    
    # Validate id
    question_id = obj.get("id", "")
    if not isinstance(question_id, str) or not question_id.strip():
        errors.append("Field 'id' must be a non-empty string")
    elif question_id in all_ids:
        errors.append(f"Duplicate id: '{question_id}'")
    else:
        all_ids.add(question_id)
    
    # Validate question
    question = obj.get("question", "")
    if not isinstance(question, str) or not question.strip():
        errors.append("Field 'question' must be a non-empty string")
    
    # Validate options
    options = obj.get("options", [])
    if not isinstance(options, list):
        errors.append("Field 'options' must be an array")
    elif len(options) != 4:
        errors.append(f"Field 'options' must have exactly 4 items, got {len(options)}")
    else:
        # Check each variant
        for i, variant in enumerate(options, 1):
            if not isinstance(variant, str) or not variant.strip():
                errors.append(f"Variant {i} in 'options' is empty or not a string")
            else:
                # Check for LLM junk (universal check)
                if has_llm_junk(variant):
                    errors.append(f"Variant {i} contains LLM junk: '{variant}'")
        
        # Check uniqueness
        if all(isinstance(v, str) for v in options):
            normalized = [normalize_text(v) for v in options]
            if len(set(normalized)) != len(normalized):
                errors.append(f"Variants in 'options' are not unique after normalization: {options}")
    
    # Validate correct
    correct = obj.get("correct")
    if not isinstance(correct, int):
        errors.append(f"Field 'correct' must be an integer, got {type(correct).__name__}")
    elif correct < 1 or correct > 4:
        errors.append(f"Field 'correct' must be 1-4, got {correct}")
    
    # Validate explanation
    explanation = obj.get("explanation", "")
    if not isinstance(explanation, str) or not explanation.strip():
        errors.append("Field 'explanation' must be a non-empty string")
    
    # Validate optional fields
    tags = obj.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errors.append("Field 'tags' must be an array")
        elif not all(isinstance(t, str) for t in tags):
            errors.append("All items in 'tags' must be strings")
    
    source = obj.get("source")
    if source is not None and not isinstance(source, str):
        errors.append("Field 'source' must be a string")
    
    return errors


def validate_jsonl_file_questions(filepath: Path, all_ids: Set[str]) -> Tuple[int, List[Tuple[int, List[str]]]]:
    """Validate a JSONL file for question format."""
    errors_list = []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    errors_list.append((line_num, [f"Invalid JSON: {e}"]))
                    continue
                
                errors = validate_question(obj, line_num, filepath, all_ids)
                if errors:
                    errors_list.append((line_num, errors))
    
    except Exception as e:
        errors_list.append((0, [f"Failed to read file: {e}"]))
    
    return len(errors_list), errors_list


# ============================================================================
# FILE DISCOVERY
# ============================================================================
def get_course_config(repo_root: Path, course_id: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific course from config.json"""
    config_path = repo_root / "data" / "config.json"
    if not config_path.exists():
        return None
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    for course in config.get("courses", []):
        if course["id"] == course_id:
            return course
    return None


def find_jsonl_files(repo_root: Path, course_id: str, category: str = "all") -> List[Path]:
    """Find JSONL files based on course and category."""
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        return []
    
    course_name = course_config["name"]
    data_dir = repo_root / "data" / course_name
    
    if not data_dir.exists():
        return []
    
    files = []
    contents = course_config.get("contents", [])
    
    for content in contents:
        content_id = content["id"]
        
        # Filter by category if specified
        if category != "all":
            # Check if content matches category (flexible matching)
            if category == "words" and "Words" not in content_id:
                continue
            elif category == "phrases" and "Phrases" not in content_id:
                continue
            elif category == "grammar" and "Grammar" not in content_id:
                continue
        
        levels = content.get("levels", [])
        for level in levels:
            level_dir = data_dir / content_id / level
            if level_dir.exists():
                files.extend(level_dir.glob("**/*.jsonl"))
    
    return sorted(files)


# ============================================================================
# DEDUPLICATION FUNCTIONS
# ============================================================================
def process_level_duplicates(level_dir: Path) -> int:
    """Process all JSONL files in a level directory. Returns number of removed duplicates."""
    if not level_dir.exists():
        return 0

    print(f"📦 Processing Level: {level_dir.name}")
    
    # Process files in sorted order to keep earlier occurrences
    jsonl_files = sorted(level_dir.glob("*.jsonl"))
    
    seen_questions: Set[str] = set()
    total_removed = 0
    
    for filepath in jsonl_files:
        original_questions = load_questions(filepath)
        unique_questions = []
        file_removed = 0
        
        for q in original_questions:
            question_text = q.get("question", "")
            if not isinstance(question_text, str):
                continue
                
            norm_question = normalize_text(question_text)
            
            if norm_question in seen_questions:
                file_removed += 1
            else:
                seen_questions.add(norm_question)
                unique_questions.append(q)
        
        if file_removed > 0:
            print(f"  ✂️  Removed {file_removed} duplicates from {filepath.name}")
            save_questions(filepath, unique_questions)
            total_removed += file_removed
        else:
            print(f"  ✅ {filepath.name} OK")
            
    return total_removed


# ============================================================================
# CONTENT-SPECIFIC VALIDATION LOADER
# ============================================================================
def load_content_specific_validator(repo_root: Path, course_id: str) -> Optional[Any]:
    """
    Load content-specific validation module for a course.
    Looks for check.py in data/{course_name}/ directory.
    
    Returns:
        Module with validate_content_specific function, or None if not found
    """
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        return None
    
    course_name = course_config["name"]
    check_module_path = repo_root / "data" / course_name / "check.py"
    
    if not check_module_path.exists():
        return None
    
    # Import the module dynamically
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"{course_name}_check", check_module_path)
    if spec is None or spec.loader is None:
        return None
    
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ============================================================================
# COMMAND HANDLERS
# ============================================================================
def cmd_validate_questions(repo_root: Path, course_id: str):
    """Validate question format in all JSONL files."""
    print("🔍 Validating question format...\n")
    
    # Get course config to determine content types
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        print(f"❌ Course '{course_id}' not found in config.json")
        return 1
    
    # Build mapping of content_id to category (words, phrases, grammar, etc.)
    content_categories = {}
    for content in course_config.get("contents", []):
        content_id = content["id"]
        # Determine category from content_id (case-insensitive)
        if "word" in content_id.lower():
            content_categories[content_id] = "words"
        elif "grammar" in content_id.lower():
            content_categories[content_id] = "grammar"
        elif "phrase" in content_id.lower():
            content_categories[content_id] = "phrases"
        else:
            content_categories[content_id] = "other"
    
    jsonl_files = find_jsonl_files(repo_root, course_id, "all")
    
    if not jsonl_files:
        print("⚠️  No JSONL files found")
        return 0
    
    print(f"📄 Found {len(jsonl_files)} file(s) to validate\n")
    
    # Separate ID tracking for different categories
    category_ids: Dict[str, Set[str]] = defaultdict(set)
    total_errors = 0
    files_with_errors = 0
    
    for filepath in jsonl_files:
        # Determine category by checking which content_id is in the path
        current_category = "other"
        for content_id, category in content_categories.items():
            if content_id in str(filepath):
                current_category = category
                break
        
        all_ids = category_ids[current_category]
        
        rel_path = filepath.relative_to(repo_root)
        print(f"Validating: {rel_path}")
        
        error_count, errors_list = validate_jsonl_file_questions(filepath, all_ids)
        
        if errors_list:
            files_with_errors += 1
            total_errors += error_count
            print(f"  ❌ {error_count} error(s) found:")
            
            for line_num, errors in errors_list:
                if line_num == 0:
                    for err in errors:
                        print(f"    File: {err}")
                else:
                    print(f"    Line {line_num}:")
                    for err in errors:
                        print(f"      - {err}")
        else:
            print(f"  ✅ OK")
        
        print()
    
    # Summary
    print("=" * 60)
    if total_errors == 0:
        print(f"✅ All {len(jsonl_files)} file(s) validated successfully!")
        return 0
    else:
        print(f"❌ Validation failed:")
        print(f"   Files checked: {len(jsonl_files)}")
        print(f"   Files with errors: {files_with_errors}")
        print(f"   Total errors: {total_errors}")
        return 1


def cmd_validate_content_specific(repo_root: Path, course_id: str):
    """
    Run content-specific validation for a course.
    Looks for check.py in data/{course_name}/ directory.
    """
    validator_module = load_content_specific_validator(repo_root, course_id)
    
    if validator_module is None:
        # No content-specific validator found - this is OK
        return 0
    
    if not hasattr(validator_module, 'validate_content_specific'):
        print(f"⚠️  Content-specific validator found but missing validate_content_specific function")
        return 0
    
    return validator_module.validate_content_specific(repo_root, course_id, "all")


def cmd_shuffle(repo_root: Path, course_id: str):
    """Shuffle answers if distribution is unbalanced."""
    print(f"🔍 Checking answer distribution...")
    print(f"   Target: 25% ± {SHUFFLE_DEVIATION_THRESHOLD*100:.1f}% (20% - 30%)\n")
    
    jsonl_files = find_jsonl_files(repo_root, course_id, "all")
    
    if not jsonl_files:
        print("⚠️  No JSONL files found")
        return 0
    
    modified_count = 0
    for filepath in jsonl_files:
        if process_shuffle_file(filepath):
            modified_count += 1
            
    print("\n" + "=" * 60)
    print(f"Done. Modified {modified_count} file(s).")
    return 0


def cmd_check_all(repo_root: Path, course_id: str):
    """Run all checks (validate + content-specific + shuffle)."""
    print("=" * 60)
    print("STEP 1: Validate Questions (Universal)")
    print("=" * 60)
    result1 = cmd_validate_questions(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 2: Content-Specific Validation")
    print("=" * 60)
    result2 = cmd_validate_content_specific(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 3: Shuffle Answers")
    print("=" * 60)
    result3 = cmd_shuffle(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    if result1 != 0:
        print("❌ Question validation failed")
        return 1
    if result2 != 0:
        print("❌ Content-specific validation failed")
        return 1
    
    print("✅ All checks passed!")
    return 0


def cmd_remove_duplicates(repo_root: Path, course_id: str):
    """Remove duplicate questions from JSONL files."""
    course_config = get_course_config(repo_root, course_id)
    if not course_config:
        print(f"❌ Course '{course_id}' not found in config.json")
        return 1
    
    course_name = course_config["name"]
    data_dir = repo_root / "data" / course_name
    contents = course_config.get("contents", [])
    total_duplicates = 0
    
    for content in contents:
        content_id = content["id"]
        content_dir = data_dir / content_id
        
        if not content_dir.exists():
            print(f"⚠️  Directory not found: {content_dir}")
            continue
            
        print(f"🔍 Searching for duplicates in: {content_dir}")
        
        levels = content.get("levels", [])
        
        for level in levels:
            level_dir = content_dir / level
            total_duplicates += process_level_duplicates(level_dir)
        print()
        
    print("=" * 60)
    if total_duplicates > 0:
        print(f"🧹 Removed {total_duplicates} duplicate question(s) total.")
        return 0
    else:
        print("✨ No duplicates found.")
        return 0


def cmd_fix_all(repo_root: Path, course_id: str):
    """Run all checks and fixes (deduplicate + validate + content-specific + shuffle)."""
    print("=" * 60)
    print("STEP 1: Remove Duplicates")
    print("=" * 60)
    cmd_remove_duplicates(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 2: Validate Questions (Universal)")
    print("=" * 60)
    result1 = cmd_validate_questions(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 3: Content-Specific Validation")
    print("=" * 60)
    result2 = cmd_validate_content_specific(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 4: Shuffle Answers")
    print("=" * 60)
    result3 = cmd_shuffle(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    
    if result1 != 0:
        print("❌ Question validation failed")
        return 1
    if result2 != 0:
        print("❌ Content-specific validation failed")
        return 1
    if result3 != 0:
        print("❌ Shuffle failed")
        return 1
    
    print("✅ All checks and fixes completed!")
    return 0


# ============================================================================
# MAIN
# ============================================================================
def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    # Parse arguments: <command> <course_id>
    # Both are required
    args = sys.argv[1:]
    
    if len(args) < 2:
        print("❌ Usage: python check_data.py <command> <course_id>")
        print("   Commands: validate-questions, validate-content, shuffle, remove-duplicates, check-all, fix-all")
        print("   Example: python check_data.py fix-all turk")
        return 1
    
    command = args[0]
    course_id = args[1]
    
    if command not in ["validate-questions", "validate-content", "shuffle", "remove-duplicates", "check-all", "fix-all"]:
        print(f"❌ Unknown command: {command}")
        print("   Valid commands: validate-questions, validate-content, shuffle, remove-duplicates, check-all, fix-all")
        return 1
    
    commands = {
        "validate-questions": cmd_validate_questions,
        "validate-content": cmd_validate_content_specific,
        "shuffle": cmd_shuffle,
        "remove-duplicates": cmd_remove_duplicates,
        "check-all": cmd_check_all,
        "fix-all": cmd_fix_all,
    }
    
    if command not in commands:
        print(f"❌ Unknown command: {command}")
        print(__doc__)
        return 1
    
    print(f"📚 Course: {course_id}\n")
    return commands[command](repo_root, course_id)


if __name__ == "__main__":
    sys.exit(main())
