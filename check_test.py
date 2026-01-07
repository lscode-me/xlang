#!/usr/bin/env python3
"""
CLI tool for reviewing and managing test questions.
Usage:
  ./check_test.py av ruavwords A1 2  # Review file 002.jsonl
  ./check_test.py av ruavwords A1 q  # Review quarantine
"""

import sys
import json
import os
from pathlib import Path


def load_config():
    """Load the config.json file."""
    config_path = Path(__file__).parent / "data" / "config.json"
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_content_path(config, course_id, content_id, level):
    """Find the directory path for the given course/content/level."""
    for course in config['courses']:
        if course['id'] == course_id:
            for content in course['contents']:
                if content['id'] == content_id:
                    # Build path: data/{course_name}/{content_dir}/{level}/
                    course_name = course['name']
                    content_dir = content['dir']
                    path = Path(__file__).parent / "data" / course_name / content_dir / level
                    return path, content
    return None, None


def load_jsonl(file_path):
    """Load questions from a JSONL file."""
    questions = []
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    questions.append(json.loads(line))
    return questions


def save_jsonl(file_path, questions):
    """Save questions to a JSONL file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        for q in questions:
            f.write(json.dumps(q, ensure_ascii=False) + '\n')


def display_question(question, index, total):
    """Display a question in a readable format."""
    print("\n" + "="*80)
    print(f"Question {index}/{total}")
    print("="*80)
    print(f"ID: {question.get('id', 'N/A')}")
    print()
    
    # Display question content
    for key, value in question.items():
        if key == 'id':
            continue
        if isinstance(value, list):
            print(f"{key}:")
            for i, item in enumerate(value, 1):
                print(f"  {i}. {item}")
        else:
            print(f"{key}: {value}")
    print("="*80)


def review_file_mode(dir_path, file_num):
    """Review questions from a specific file."""
    file_name = f"{file_num:03d}.jsonl"
    file_path = dir_path / file_name
    quarantine_path = dir_path / "quarantine.jsonl"
    
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist.")
        return
    
    questions = load_jsonl(file_path)
    if not questions:
        print(f"No questions found in {file_path}")
        return
    
    quarantine_questions = load_jsonl(quarantine_path)
    remaining_questions = []
    
    # Store source file info for restoration
    current_file_name = file_name
    
    print(f"\nReviewing {len(questions)} questions from {file_name}")
    print("Commands:")
    print("  [Enter] - Keep question and continue")
    print("  d - Delete question (move to quarantine)")
    print("  w - Save changes and quit")
    print("  q - Quit without saving")
    
    for idx, question in enumerate(questions, 1):
        display_question(question, idx, len(questions))
        
        while True:
            response = input("\nAction ([Enter] to keep, 'd' to delete, 'w' to save & quit, 'q' to quit): ").strip().lower()
            
            if response == 'q':
                print("\nQuitting without saving changes...")
                return
            elif response == 'w':
                print("\nSaving changes and quitting...")
                remaining_questions.append(question)
                remaining_questions.extend(questions[idx:])
                save_jsonl(file_path, remaining_questions)
                if quarantine_questions:
                    save_jsonl(quarantine_path, quarantine_questions)
                print(f"✅ Saved! Kept: {len(remaining_questions)}, Quarantined: {len(quarantine_questions)}")
                return
            elif response == 'd':
                print("❌ Moving to quarantine...")
                # Add source file metadata for restoration
                question['_source_file'] = current_file_name
                question['_original_position'] = idx - 1  # 0-based index
                quarantine_questions.append(question)
                break
            elif response == '':
                print("✓ Keeping question...")
                remaining_questions.append(question)
                break
            else:
                print("Invalid input. Press [Enter] to keep, 'd' to delete, 'w' to save & quit, or 'q' to quit.")
    
    # Save results
    save_jsonl(file_path, remaining_questions)
    if quarantine_questions:
        save_jsonl(quarantine_path, quarantine_questions)
    
    print(f"\n✅ Review complete!")
    print(f"Kept: {len(remaining_questions)} questions")
    print(f"Quarantined: {len(quarantine_questions)} questions")
    print(f"Quarantine file: {quarantine_path}")


def get_all_files(dir_path):
    """Get all numbered JSONL files in directory."""
    files = []
    for f in sorted(dir_path.glob("*.jsonl")):
        if f.name != "quarantine.jsonl" and f.stem.isdigit():
            files.append(f)
    return files


def get_next_id(questions):
    """Get the next available ID for questions."""
    if not questions:
        return 1
    # Convert all IDs to integers for comparison
    ids = []
    for q in questions:
        qid = q.get('id', 0)
        if isinstance(qid, str):
            try:
                ids.append(int(qid))
            except ValueError:
                ids.append(0)
        else:
            ids.append(qid)
    
    max_id = max(ids) if ids else 0
    return max_id + 1


def review_quarantine_mode(dir_path):
    """Review questions from quarantine."""
    quarantine_path = dir_path / "quarantine.jsonl"
    
    if not quarantine_path.exists():
        print(f"No quarantine file found at {quarantine_path}")
        return
    
    quarantine_questions = load_jsonl(quarantine_path)
    if not quarantine_questions:
        print("Quarantine is empty.")
        return
    
    print(f"\nReviewing {len(quarantine_questions)} questions from quarantine")
    print("Commands:")
    print("  [Enter] - Keep in quarantine")
    print("  r - Restore question (move back to JSONL files)")
    print("  w - Save changes and quit")
    print("  q - Quit without saving")
    
    remaining_in_quarantine = []
    to_restore = []
    
    for idx, question in enumerate(quarantine_questions, 1):
        display_question(question, idx, len(quarantine_questions))
        
        while True:
            response = input("\nAction ([Enter] to keep, 'r' to restore, 'w' to save & quit, 'q' to quit): ").strip().lower()
            
            if response == 'q':
                print("\nQuitting without saving changes...")
                return
            elif response == 'w':
                print("\nSaving changes and quitting...")
                remaining_in_quarantine.append(question)
                remaining_in_quarantine.extend(quarantine_questions[idx:])
                break
            elif response == 'r':
                print("✓ Marking for restoration...")
                to_restore.append(question)
                break
            elif response == '':
                print("Keeping in quarantine...")
                remaining_in_quarantine.append(question)
                break
            else:
                print("Invalid input. Press [Enter] to keep, 'r' to restore, 'w' to save & quit, or 'q' to quit.")
        
        if response == 'w' or response == 'q':
            break
    
    # Restore questions to JSONL files
    if to_restore:
        print(f"\nRestoring {len(to_restore)} questions...")
        
        # Group questions by source file
        by_file = {}
        for question in to_restore:
            source_file = question.get('_source_file', None)
            if source_file:
                if source_file not in by_file:
                    by_file[source_file] = []
                by_file[source_file].append(question)
            else:
                # If no source file info, restore to last file
                if 'unknown' not in by_file:
                    by_file['unknown'] = []
                by_file['unknown'].append(question)
        
        # Get all existing files for unknown sources
        files = get_all_files(dir_path)
        if not files:
            files = [dir_path / "001.jsonl"]
            save_jsonl(files[0], [])
        
        # Restore to original files
        for source_file, questions_to_restore in by_file.items():
            if source_file == 'unknown':
                # Add to last file
                target_file = files[-1]
                target_questions = load_jsonl(target_file)
                
                # Add to end for unknown sources
                for question in questions_to_restore:
                    question.pop('_source_file', None)
                    question.pop('_original_position', None)
                    target_questions.append(question)
            else:
                # Add to original file at original position
                target_file = dir_path / source_file
                if not target_file.exists():
                    # File was deleted, create it
                    target_questions = []
                else:
                    target_questions = load_jsonl(target_file)
                
                # Sort by original position to maintain order
                questions_to_restore.sort(key=lambda q: q.get('_original_position', 999999))
                
                # Insert questions at their original positions
                for question in questions_to_restore:
                    original_pos = question.pop('_original_position', None)
                    question.pop('_source_file', None)
                    
                    if original_pos is not None and original_pos <= len(target_questions):
                        # Insert at original position
                        target_questions.insert(original_pos, question)
                    else:
                        # Add to end if position is invalid
                        target_questions.append(question)
            
            # Save file
            save_jsonl(target_file, target_questions)
            print(f"✓ Restored {len(questions_to_restore)} questions to {target_file.name}")
    
    # Save updated quarantine
    if remaining_in_quarantine:
        save_jsonl(quarantine_path, remaining_in_quarantine)
    elif quarantine_path.exists():
        # Remove empty quarantine file
        quarantine_path.unlink()
    
    print(f"\n✅ Quarantine review complete!")
    print(f"Restored: {len(to_restore)} questions")
    print(f"Remaining in quarantine: {len(remaining_in_quarantine)} questions")


def main():
    if len(sys.argv) != 5:
        print("Usage:")
        print("  ./check_test.py <course_id> <content_id> <level> <file_num>")
        print("  ./check_test.py <course_id> <content_id> <level> q")
        print("\nExamples:")
        print("  ./check_test.py av ruavwords A1 2    # Review file 002.jsonl")
        print("  ./check_test.py av ruavwords A1 q    # Review quarantine")
        sys.exit(1)
    
    course_id = sys.argv[1]
    content_id = sys.argv[2]
    level = sys.argv[3]
    file_arg = sys.argv[4]
    
    # Load config and find path
    config = load_config()
    dir_path, content = find_content_path(config, course_id, content_id, level)
    
    if dir_path is None:
        print(f"Error: Could not find path for {course_id}/{content_id}/{level}")
        sys.exit(1)
    
    if not dir_path.exists():
        print(f"Error: Directory {dir_path} does not exist")
        sys.exit(1)
    
    print(f"Working directory: {dir_path}")
    
    # Route to appropriate mode
    if file_arg.lower() == 'q':
        review_quarantine_mode(dir_path)
    else:
        try:
            file_num = int(file_arg)
            review_file_mode(dir_path, file_num)
        except ValueError:
            print(f"Error: Invalid file number '{file_arg}'. Use a number or 'q' for quarantine.")
            sys.exit(1)


if __name__ == "__main__":
    main()
