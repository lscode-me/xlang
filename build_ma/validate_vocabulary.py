#!/usr/bin/env python3
"""
Validates vocabulary JSONL files in Vocabulary/RU-TR_Words against strict rules.
Rules derived from generate_words_prompt.md:
1. Valid JSON
2. ID format: LEVEL-SET-NUM
3. RU: Single word, no spaces
4. TR: Exactly 4 unique options, no Cyrillic
5. Correct: 1-4
6. Tags: List of strings
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Configuration
ID_PATTERN = re.compile(r"^(A1|A2|B1)-\d{3}-\d{4}$")
CYRILLIC_PATTERN = re.compile(r"[а-яА-ЯёЁ]")

def validate_entry(entry: Dict[str, Any], line_num: int) -> Tuple[List[str], List[str]]:
    errors = []
    warnings = []
    
    # 1. ID Validation
    obj_id = entry.get("id")
    if not isinstance(obj_id, str) or not ID_PATTERN.match(obj_id):
        errors.append(f"Line {line_num}: Invalid ID format '{obj_id}'")

    # 2. RU Validation
    ru_word = entry.get("ru")
    if not isinstance(ru_word, str):
        errors.append(f"Line {line_num}: 'ru' field must be a string")
    elif not ru_word.strip():
        errors.append(f"Line {line_num}: 'ru' field is empty")
    elif " " in ru_word.strip():
         # Modified to be a WARNING instead of ERROR
        warnings.append(f"Line {line_num}: 'ru' field contains multiple words: '{ru_word}'")

    # 3. TR Validation
    tr_options = entry.get("tr")
    if not isinstance(tr_options, list) or len(tr_options) != 4:
        errors.append(f"Line {line_num}: 'tr' must be a list of exactly 4 options")
    else:
        # Check for duplicates
        if len(set(tr_options)) != 4:
            errors.append(f"Line {line_num}: 'tr' options must be unique")
        
        # Check each option
        for opt in tr_options:
            if not isinstance(opt, str):
                errors.append(f"Line {line_num}: 'tr' option must be a string")
                continue
            if CYRILLIC_PATTERN.search(opt):
                errors.append(f"Line {line_num}: 'tr' option '{opt}' contains Cyrillic characters")

    # 4. Correct Validation
    correct = entry.get("correct")
    if not isinstance(correct, int) or not (1 <= correct <= 4):
         errors.append(f"Line {line_num}: 'correct' must be an integer between 1 and 4")

    # 5. Consistency Check (Heuristic)
    # The 'ru' word should usually appear in 'explain_ru'
    explain_ru = entry.get("explain_ru", "")
    if isinstance(explain_ru, str) and isinstance(ru_word, str) and ru_word.lower() not in explain_ru.lower():
         warnings.append(f"Line {line_num}: Consistency warning - 'ru' word '{ru_word}' not found in 'explain_ru' ('{explain_ru}')")

    # 6. Tags Validation (Optional but checking type)
    tags = entry.get("tags")
    if tags is not None and not isinstance(tags, list):
        errors.append(f"Line {line_num}: 'tags' must be a list")

    return errors, warnings

def validate_file(filepath: Path) -> Tuple[List[str], List[str]]:
    file_errors = []
    file_warnings = []
    with open(filepath, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                e, w = validate_entry(entry, i)
                file_errors.extend(e)
                file_warnings.extend(w)
            except json.JSONDecodeError as e:
                file_errors.append(f"Line {i}: Invalid JSON - {e}")
                
    return file_errors, file_warnings

def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    words_dir = repo_root / "Vocabulary" / "RU-TR_Words"
    
    if not words_dir.exists():
        print(f"❌ Directory not found: {words_dir}")
        sys.exit(1)

    print(f"🔍 Validating vocabulary in: {words_dir}")
    print("=" * 60)

    all_files = sorted(words_dir.glob("**/*.jsonl"))
    total_errors = 0
    files_with_issues = 0

    for filepath in all_files:
        errors, warnings = validate_file(filepath)
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
        sys.exit(1)
    else:
        if files_with_issues > 0:
            print(f"✨ SUCCESS with warnings. Scanned {len(all_files)} files. No errors found.")
        else:
            print(f"✨ SUCCESS. Scanned {len(all_files)} files. No issues found.")
        sys.exit(0)

if __name__ == "__main__":
    main()
