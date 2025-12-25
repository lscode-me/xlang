#!/usr/bin/env python3
"""
Removes duplicate questions from Vocabulary/{RU-TR_Phrases,RU-TR_Words,RU-TR_Grammar}/{A1,A2,B1}/*.jsonl files.
Duplicates are identified by comparing normalized 'ru' text within the same level.
Files are processed in order (001, 002, ...), keeping the first occurrence.
"""
import json
import re
import sys
from pathlib import Path
from typing import List, Dict, Set, Any


def normalize_text(text: str) -> str:
    """Normalize text for comparison: trim, lowercase, collapse spaces"""
    return re.sub(r"\s+", " ", text.strip().lower())


def load_questions(filepath: Path) -> List[Dict[str, Any]]:
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
    with open(filepath, "w", encoding="utf-8") as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")


def process_level(level_dir: Path) -> int:
    """
    Process all JSONL files in a level directory.
    Returns number of removed duplicates.
    """
    if not level_dir.exists():
        return 0

    print(f"📦 Processing Level: {level_dir.name}")
    
    # Process files in sorted order to keep earlier occurrences
    jsonl_files = sorted(level_dir.glob("*.jsonl"))
    
    seen_ru: Set[str] = set()
    total_removed = 0
    
    for filepath in jsonl_files:
        original_questions = load_questions(filepath)
        unique_questions = []
        file_removed = 0
        
        for q in original_questions:
            ru_text = q.get("ru", "")
            if not isinstance(ru_text, str):
                continue
                
            norm_ru = normalize_text(ru_text)
            
            if norm_ru in seen_ru:
                file_removed += 1
                # print(f"  Duplicate found: '{ru_text}' in {filepath.name}")
            else:
                seen_ru.add(norm_ru)
                unique_questions.append(q)
        
        if file_removed > 0:
            print(f"  ✂️  Removed {file_removed} duplicates from {filepath.name}")
            save_questions(filepath, unique_questions)
            total_removed += file_removed
        else:
            print(f"  ✅ {filepath.name} OK")
            
    return total_removed


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    vocab_dirs = ["RU-TR_Phrases", "RU-TR_Words", "RU-TR_Grammar"]
    total_duplicates = 0
    
    for vocab_name in vocab_dirs:
        base_dir = repo_root / "Vocabulary" / vocab_name
        
        if not base_dir.exists():
            print(f"⚠️  Directory not found: {base_dir}")
            continue
            
        print(f"🔍 Searching for duplicates in: {base_dir}")
        
        levels = ["A1", "A2", "B1"]
        
        for level in levels:
            level_dir = base_dir / level
            total_duplicates += process_level(level_dir)
        print()
        
    print("=" * 60)
    if total_duplicates > 0:
        print(f"🧹 Removed {total_duplicates} duplicate question(s) total.")
    else:
        print("✨ No duplicates found.")


if __name__ == "__main__":
    sys.exit(main())
