#!/usr/bin/env python3
"""
Validates question JSONL files in Vocabulary/RU-TR_{Words,Phrases}/{A1,A2,B1}/**/*.jsonl
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Set

# LLM junk patterns to detect
LLM_JUNK_PATTERNS = [
    r"правильный ответ",
    r"вариант\s+\d+",
    r"as an ai",
    r"chatgpt",
    r"i'?m sorry",
    r"i can'?t",
    r"openai",
]

REQUIRED_FIELDS = {"id", "ru", "tr", "correct", "explain_ru"}
OPTIONAL_FIELDS = {"tags", "source"}


def normalize_text(text: str) -> str:
    """Normalize text for comparison: trim, lowercase, collapse spaces"""
    return re.sub(r"\s+", " ", text.strip().lower())


def has_cyrillic(text: str) -> bool:
    """Check if text contains Cyrillic characters"""
    return bool(re.search(r"[а-яёА-ЯЁ]", text))


def has_llm_junk(text: str) -> bool:
    """Check if text contains LLM junk markers"""
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
        return errors  # Cannot continue validation
    
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
    
    # Validate ru
    ru = obj.get("ru", "")
    if not isinstance(ru, str) or not ru.strip():
        errors.append("Field 'ru' must be a non-empty string")
    
    # Validate tr
    tr = obj.get("tr", [])
    if not isinstance(tr, list):
        errors.append("Field 'tr' must be an array")
    elif len(tr) != 4:
        errors.append(f"Field 'tr' must have exactly 4 items, got {len(tr)}")
    else:
        # Check each variant
        for i, variant in enumerate(tr, 1):
            if not isinstance(variant, str) or not variant.strip():
                errors.append(f"Variant {i} in 'tr' is empty or not a string")
            else:
                # Check for Cyrillic
                if has_cyrillic(variant):
                    errors.append(f"Variant {i} contains Cyrillic: '{variant}'")
                # Check for LLM junk
                if has_llm_junk(variant):
                    errors.append(f"Variant {i} contains LLM junk: '{variant}'")
        
        # Check uniqueness of variants
        if all(isinstance(v, str) for v in tr):
            normalized = [normalize_text(v) for v in tr]
            if len(set(normalized)) != len(normalized):
                errors.append(f"Variants in 'tr' are not unique after normalization: {tr}")
    
    # Validate correct
    correct = obj.get("correct")
    if not isinstance(correct, int):
        errors.append(f"Field 'correct' must be an integer, got {type(correct).__name__}")
    elif correct < 1 or correct > 4:
        errors.append(f"Field 'correct' must be 1-4, got {correct}")
    
    # Validate explain_ru
    explain_ru = obj.get("explain_ru", "")
    if not isinstance(explain_ru, str) or not explain_ru.strip():
        errors.append("Field 'explain_ru' must be a non-empty string")
    elif "—" not in explain_ru and "-" not in explain_ru:
        errors.append("Field 'explain_ru' must contain at least one separator ('—' or '-')")
    
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


def validate_jsonl_file(filepath: Path, all_ids: Set[str]) -> Tuple[int, List[Tuple[int, List[str]]]]:
    """
    Validate a JSONL file.
    Returns (total_lines, errors_list) where errors_list is [(line_num, error_messages)]
    """
    errors_list = []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue  # Skip empty lines
                
                # Try to parse JSON
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    errors_list.append((line_num, [f"Invalid JSON: {e}"]))
                    continue
                
                # Validate the object
                errors = validate_question(obj, line_num, filepath, all_ids)
                if errors:
                    errors_list.append((line_num, errors))
    
    except Exception as e:
        errors_list.append((0, [f"Failed to read file: {e}"]))
    
    return len(errors_list), errors_list


def find_jsonl_files(base_dir: Path) -> List[Path]:
    """Find all .jsonl files in Vocabulary/RU-TR_{Words,Phrases,Grammar}/{A1,A2,B1}/**/*.jsonl"""
    patterns = [
        "Vocabulary/RU-TR_Words/A1/**/*.jsonl",
        "Vocabulary/RU-TR_Words/A2/**/*.jsonl",
        "Vocabulary/RU-TR_Words/B1/**/*.jsonl",
        "Vocabulary/RU-TR_Phrases/A1/**/*.jsonl",
        "Vocabulary/RU-TR_Phrases/A2/**/*.jsonl",
        "Vocabulary/RU-TR_Phrases/B1/**/*.jsonl",
        "Vocabulary/RU-TR_Grammar/A1/**/*.jsonl",
        "Vocabulary/RU-TR_Grammar/A2/**/*.jsonl",
        "Vocabulary/RU-TR_Grammar/B1/**/*.jsonl",
    ]
    
    files = []
    for pattern in patterns:
        files.extend(base_dir.glob(pattern))
    
    return sorted(files)


def main():
    """Main validation function"""
    # Find repository root (parent of build_ma)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    print(f"🔍 Searching for JSONL files in: {repo_root}")
    
    jsonl_files = find_jsonl_files(repo_root)
    
    if not jsonl_files:
        print("⚠️  No JSONL files found in Vocabulary/RU-TR_{Words,Phrases,Grammar}/{A1,A2,B1}")
        return 0
    
    print(f"📄 Found {len(jsonl_files)} file(s) to validate\n")
    
    # Separate ID tracking for Words, Phrases, and Grammar to allow same IDs in different categories
    words_ids: Set[str] = set()
    phrases_ids: Set[str] = set()
    grammar_ids: Set[str] = set()
    total_errors = 0
    files_with_errors = 0
    
    for filepath in jsonl_files:
        # Determine which ID set to use based on file path
        if "RU-TR_Words" in str(filepath):
            all_ids = words_ids
        elif "RU-TR_Grammar" in str(filepath):
            all_ids = grammar_ids
        else:
            all_ids = phrases_ids
        rel_path = filepath.relative_to(repo_root)
        print(f"Validating: {rel_path}")
        
        error_count, errors_list = validate_jsonl_file(filepath, all_ids)
        
        if errors_list:
            files_with_errors += 1
            total_errors += error_count
            print(f"  ❌ {error_count} error(s) found:")
            
            for line_num, errors in errors_list:
                if line_num == 0:
                    # File-level error
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


if __name__ == "__main__":
    sys.exit(main())
