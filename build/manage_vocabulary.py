#!/usr/bin/env python3
"""
Universal tool for managing vocabulary JSONL files.
Combines validation, shuffling, deduplication, and quality checks.

Usage:
    ./manage_vocabulary.py <course_id>                     # Required: check and fix everything for course
    ./manage_vocabulary.py validate-questions <course_id>  # Validate question format
    ./manage_vocabulary.py validate-words <course_id>      # Validate word entries (Words content only)
    ./manage_vocabulary.py shuffle <course_id>             # Shuffle answers if distribution is unbalanced
    ./manage_vocabulary.py remove-duplicates <course_id>   # Remove duplicate questions
    ./manage_vocabulary.py check-all <course_id>           # Run all checks (validate + shuffle)
    ./manage_vocabulary.py fix-all <course_id>             # Run all checks and fixes (deduplicate + validate + shuffle)
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
    r"i can'?t",
    r"openai",
]

REQUIRED_FIELDS = {"id", "question", "options", "correct", "explanation"}
OPTIONAL_FIELDS = {"tags", "source"}

# Vocabulary-specific patterns
ID_PATTERN = re.compile(r"^(A1|A2|B1)-\d{3}-\d{4}$")
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")


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


def process_shuffle_file(filepath: Path) -> bool:
    """Process a single file for shuffling. Returns True if file was modified."""
    questions = load_questions(filepath)
    if not questions:
        return False

    ratios = check_distribution(questions)
    should_shuffle = needs_shuffling(ratios)
    
    # Format distribution
    dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in ratios.items()])
    display_path = f"{filepath.parent.name}/{filepath.name}"
    result_msg = f"  📊 {display_path}: {dist_str}"
    
    if should_shuffle:
        print(result_msg + " -> ⚠️  High deviation, SHUFFLING...")
        
        # Shuffle all questions
        for q in questions:
            shuffle_question(q)
            
        # Verify new distribution
        new_ratios = check_distribution(questions)
        new_dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in new_ratios.items()])
        print(f"     New dist: {new_dist_str}")
        
        save_questions(filepath, questions)
        return True
    else:
        print(result_msg + " -> ✅ Balanced")
        return False


# ============================================================================
# VALIDATION FUNCTIONS - QUESTIONS
# ============================================================================
def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())


def has_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters."""
    return bool(re.search(r"[а-яёА-ЯЁ]", text))


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
                # Check for Cyrillic
                if has_cyrillic(variant):
                    errors.append(f"Variant {i} contains Cyrillic: '{variant}'")
                # Check for LLM junk
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
    elif "—" not in explanation and "-" not in explanation:
        errors.append("Field 'explanation' must contain at least one separator ('—' or '-')")
    
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
# VALIDATION FUNCTIONS - WORDS (any Words content type)
# ============================================================================
def validate_word_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    """Validate a single word entry. Returns (errors, warnings)."""
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}'")

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
        
        # Check each option
        for opt in options:
            if not isinstance(opt, str):
                errors.append(f"Line {line_num}: 'options' option must be a string")
                continue
            if CYRILLIC_PATTERN.search(opt):
                errors.append(f"Line {line_num}: 'options' option '{opt}' contains Cyrillic characters")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
        errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")

    # 5. Consistency Check
    explanation = entry.get("explanation", "")
    if isinstance(explanation, str) and isinstance(question, str) and question.lower() not in explanation.lower():
        warnings.append(f"Line {line_num}: 'question' word '{question}' not found in 'explanation'")

    # 6. Tags Validation
    tags = entry.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"Line {line_num}: 'tags' must be a list")

    return errors, warnings


def validate_file_words(filepath: Path) -> Tuple[List[str], List[str]]:
    """Validate a JSONL file for word-specific rules."""
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


def cmd_validate_words(repo_root: Path, course_id: str):
    """Validate word entries for any Words content type."""
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

    print(f"🔍 Validating vocabulary in: {words_dir}")
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
    """Run all checks (validate + shuffle)."""
    print("=" * 60)
    print("STEP 1: Validate Questions")
    print("=" * 60)
    result1 = cmd_validate_questions(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 2: Validate Words (Words content only)")
    print("=" * 60)
    result2 = cmd_validate_words(repo_root, course_id)
    
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
        print("❌ Word validation failed")
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
    """Run all checks and fixes (deduplicate + validate + shuffle)."""
    print("=" * 60)
    print("STEP 1: Remove Duplicates")
    print("=" * 60)
    cmd_remove_duplicates(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 2: Validate Questions")
    print("=" * 60)
    result1 = cmd_validate_questions(repo_root, course_id)
    
    print("\n")
    print("=" * 60)
    print("STEP 3: Validate Words (Words content only)")
    print("=" * 60)
    result2 = cmd_validate_words(repo_root, course_id)
    
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
        print("❌ Word validation failed")
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
        print("❌ Usage: python manage_vocabulary.py <command> <course_id>")
        print("   Commands: validate-questions, validate-words, shuffle, remove-duplicates, check-all, fix-all")
        print("   Example: python manage_vocabulary.py fix-all turk")
        return 1
    
    command = args[0]
    course_id = args[1]
    
    if command not in ["validate-questions", "validate-words", "shuffle", "remove-duplicates", "check-all", "fix-all"]:
        print(f"❌ Unknown command: {command}")
        print("   Valid commands: validate-questions, validate-words, shuffle, remove-duplicates, check-all, fix-all")
        return 1
    
    commands = {
        "validate-questions": cmd_validate_questions,
        "validate-words": cmd_validate_words,
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
