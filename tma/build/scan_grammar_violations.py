import json
import glob
import os

def scan_grammar_files(root_dir):
    pattern = os.path.join(root_dir, '**', '*.jsonl')
    files = glob.glob(pattern, recursive=True)
    
    violations = []
    
    print(f"Scanning {len(files)} files in {root_dir}...")
    
    for file_path in files:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    question = data.get('question', '')
                    options = data.get('options', [])
                    
                    if not question or not options:
                        continue
                        
                    # Heuristic:
                    # 1. Question has >= 3 words (likely a sentence)
                    # 2. Options have only 1 word
                    # 3. Question does NOT contain placeholders like "..." or "___"
                    
                    q_words = question.split()
                    is_sentence_like = len(q_words) >= 3
                    has_placeholder = '...' in question or '___' in question or '…' in question
                    
                    # Check first option (assuming all options are similar structure as they should be)
                    # Use a safe check just in case options vary
                    opt_words = [opt.split() for opt in options]
                    avg_opt_len = sum(len(w) for w in opt_words) / len(opt_words) if opt_words else 0
                    
                    is_single_word_answer = avg_opt_len == 1.0
                    
                    if is_sentence_like and not has_placeholder and is_single_word_answer:
                        violations.append({
                            'file': file_path,
                            'line': line_num,
                            'id': data.get('id'),
                            'question': question,
                            'options': options
                        })
                        
                except json.JSONDecodeError:
                    print(f"Error decoding JSON in {file_path} at line {line_num}")
    
    return violations

if __name__ == "__main__":
    root_dir = "data/Turk/RU-TR_Grammar"
    violations = scan_grammar_files(root_dir)
    
    if violations:
        print(f"\nFound {len(violations)} potential violations:\n")
        for v in violations:
            print(f"File: {v['file']}:{v['line']}")
            print(f"ID: {v['id']}")
            print(f"Question: {v['question']}")
            print(f"Options: {v['options']}")
            print("-" * 40)
    else:
        print("\nNo violations found based on the heuristic.")
