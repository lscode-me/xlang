#!/usr/bin/env python3
"""
Shuffles correct answers in JSONL files if the distribution of correct options (1-4)
deviates significantly (more than 5%) from the ideal uniform distribution (25%).
"""
import json
import random
import sys
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

# Threshold allowed deviation from 25% (0.25)
# If deviation > 0.05 (i.e. < 20% or > 30%), we shuffle.
DEVIATION_THRESHOLD = 0.05
TARGET_RATIO = 0.25


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


def check_distribution(questions: List[Dict[str, Any]]) -> Dict[int, float]:
    total = len(questions)
    if total == 0:
        return {}
    
    counts = Counter(q.get("correct") for q in questions)
    ratios = {k: counts.get(k, 0) / total for k in range(1, 5)}
    return ratios


def needs_shuffling(ratios: Dict[int, float]) -> bool:
    """Check if any option deviates more than the threshold from target."""
    for opt in range(1, 5):
        ratio = ratios.get(opt, 0.0)
        deviation = abs(ratio - TARGET_RATIO)
        if deviation > DEVIATION_THRESHOLD:
            return True
    return False


def shuffle_question(question: Dict[str, Any]) -> Dict[str, Any]:
    """Shuffle options and update 'correct' index."""
    tr_options = question.get("tr", [])
    if len(tr_options) != 4:
        return question
    
    # Get current correct answer string
    correct_idx = question.get("correct", 1) - 1 # 0-based
    if 0 <= correct_idx < len(tr_options):
        correct_answer = tr_options[correct_idx]
    else:
        # Fallback if index is invalid (should be caught by validator)
        return question

    # Shuffle
    random.shuffle(tr_options)
    
    # Find new index
    new_correct_idx = tr_options.index(correct_answer)
    
    # Update question
    question["tr"] = tr_options
    question["correct"] = new_correct_idx + 1 # 1-based
    
    return question


def process_file(filepath: Path) -> bool:
    """
    Process a single file. Returns True if file was modified.
    """
    questions = load_questions(filepath)
    if not questions:
        return False

    ratios = check_distribution(questions)
    
    should_shuffle = needs_shuffling(ratios)
    
    # Format current distribution for print
    dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in ratios.items()])
    
    display_path = f"{filepath.parent.name}/{filepath.name}"
    result_msg = f"  📊 {display_path}: {dist_str}"
    
    if should_shuffle:
        print(result_msg + " -> ⚠️  High deviation, SHUFFLING...")
        
        # Shuffle all questions
        for q in questions:
            shuffle_question(q)
            
        # Verify new distribution (it might still be random, but usually better)
        new_ratios = check_distribution(questions)
        new_dist_str = ", ".join([f"{k}: {v*100:.1f}%" for k, v in new_ratios.items()])
        print(f"     New dist: {new_dist_str}")
        
        save_questions(filepath, questions)
        return True
    else:
        print(result_msg + " -> ✅ Balanced")
        return False


def find_jsonl_files(base_dir: Path) -> List[Path]:
    patterns = [
        "Vocabulary/RU-TR_Phrases/A1/**/*.jsonl",
        "Vocabulary/RU-TR_Phrases/A2/**/*.jsonl",
        "Vocabulary/RU-TR_Phrases/B1/**/*.jsonl",
    ]
    files = []
    for pattern in patterns:
        files.extend(base_dir.glob(pattern))
    return sorted(files)


def main():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    print(f"🔍 Checking answer distribution in: {repo_root}")
    print(f"   Target: 25% ± {DEVIATION_THRESHOLD*100:.1f}% (20% - 30%)\n")
    
    jsonl_files = find_jsonl_files(repo_root)
    
    if not jsonl_files:
        print("⚠️  No JSONL files found.")
        return 0
    
    modified_count = 0
    for filepath in jsonl_files:
        if process_file(filepath):
            modified_count += 1
            
    print("\n" + "=" * 60)
    print(f"Done. Modified {modified_count} file(s).")


if __name__ == "__main__":
    sys.exit(main())
