#!/usr/bin/env python3
"""
Validates generated HTML files for syntax errors.
Checks JavaScript syntax within <script> tags.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def extract_js_blocks(html_content: str, filepath: str) -> List[Tuple[int, str]]:
    """Extract JavaScript code blocks from HTML with their starting line numbers."""
    blocks = []
    lines = html_content.split('\n')
    in_script = False
    script_start = 0
    script_lines = []
    
    for i, line in enumerate(lines, 1):
        if '<script' in line and not 'src=' in line:
            in_script = True
            script_start = i
            script_lines = []
            # If script tag and code are on same line
            code_after_tag = re.search(r'<script[^>]*>(.*)', line)
            if code_after_tag and code_after_tag.group(1).strip():
                script_lines.append(code_after_tag.group(1))
        elif '</script>' in line and in_script:
            # Get code before closing tag
            code_before_tag = re.search(r'^(.*?)</script>', line)
            if code_before_tag and code_before_tag.group(1).strip():
                script_lines.append(code_before_tag.group(1))
            
            if script_lines:
                blocks.append((script_start, '\n'.join(script_lines)))
            in_script = False
            script_lines = []
        elif in_script:
            script_lines.append(line)
    
    return blocks


def check_js_syntax(js_code: str, start_line: int, filepath: str) -> List[str]:
    """Check JavaScript syntax for common issues."""
    errors = []
    lines = js_code.split('\n')
    
    # Track bracket balance
    brace_stack = []
    paren_stack = []
    bracket_stack = []
    
    for i, line in enumerate(lines, start_line):
        # Skip comments
        if line.strip().startswith('//'):
            continue
        
        # Check for unmatched brackets
        for char in line:
            if char == '{':
                brace_stack.append(i)
            elif char == '}':
                if not brace_stack:
                    errors.append(f"Line {i}: Unmatched closing brace '}}' in {filepath}")
                else:
                    brace_stack.pop()
            elif char == '(':
                paren_stack.append(i)
            elif char == ')':
                if not paren_stack:
                    errors.append(f"Line {i}: Unmatched closing parenthesis ')' in {filepath}")
                else:
                    paren_stack.pop()
            elif char == '[':
                bracket_stack.append(i)
            elif char == ']':
                if not bracket_stack:
                    errors.append(f"Line {i}: Unmatched closing bracket ']' in {filepath}")
                else:
                    bracket_stack.pop()
        
        # Check for common syntax errors
        stripped = line.strip()
        
        # Multiple closing braces on one line (potential error)
        if stripped.count('}') > 2 and not '{' in stripped:
            errors.append(f"Line {i}: Suspicious number of closing braces in {filepath}")
    
    # Check for unmatched opening brackets
    if brace_stack:
        errors.append(f"Unmatched opening braces at lines: {brace_stack} in {filepath}")
    if paren_stack:
        errors.append(f"Unmatched opening parentheses at lines: {paren_stack} in {filepath}")
    if bracket_stack:
        errors.append(f"Unmatched opening brackets at lines: {bracket_stack} in {filepath}")
    
    return errors


def validate_html_file(filepath: Path) -> List[str]:
    """Validate a single HTML file."""
    errors = []
    
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return [f"Failed to read {filepath}: {e}"]
    
    # Check for basic HTML structure
    if '<html' not in content.lower():
        errors.append(f"Missing <html> tag in {filepath}")
    if '<body' not in content.lower():
        errors.append(f"Missing <body> tag in {filepath}")
    
    # Extract and check JavaScript blocks
    js_blocks = extract_js_blocks(content, str(filepath))
    for start_line, js_code in js_blocks:
        js_errors = check_js_syntax(js_code, start_line, str(filepath))
        errors.extend(js_errors)
    
    return errors


def validate_html_dir(directory: Path) -> bool:
    """Validate all HTML files in directory recursively."""
    all_errors = []
    html_files = list(directory.rglob('*.html'))
    js_files = list(directory.rglob('*.js'))
    
    if not html_files and not js_files:
        print(f"⚠️  No HTML or JS files found in {directory}")
        return True
    
    print(f"🔍 Validating {len(html_files)} HTML and {len(js_files)} JS file(s)...\n")
    
    # Validate HTML files
    for filepath in html_files:
        errors = validate_html_file(filepath)
        if errors:
            all_errors.extend(errors)
            print(f"❌ {filepath.relative_to(directory.parent)}:")
            for error in errors:
                print(f"   {error}")
            print()
        else:
            print(f"✅ {filepath.relative_to(directory.parent)}")
    
    # Validate standalone JS files
    for filepath in js_files:
        errors = validate_js_file(filepath)
        if errors:
            all_errors.extend(errors)
            print(f"❌ {filepath.relative_to(directory.parent)}:")
            for error in errors:
                print(f"   {error}")
            print()
        else:
            print(f"✅ {filepath.relative_to(directory.parent)}")
    
    print(f"\n{'='*60}")
    if all_errors:
        print(f"❌ Validation failed: {len(all_errors)} error(s) found")
        return False
    else:
        print(f"✅ All files are valid!")
        return True


def validate_js_file(filepath: Path) -> List[str]:
    """Validate a standalone JavaScript file."""
    errors = []
    
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return [f"Failed to read {filepath}: {e}"]
    
    lines = content.split('\n')
    js_errors = check_js_syntax(content, 1, str(filepath))
    errors.extend(js_errors)
    
    return errors


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        # Default to html/ma directory
        target = Path(__file__).parent.parent / 'html' / 'ma'
    
    if not target.exists():
        print(f"❌ Path does not exist: {target}")
        sys.exit(1)
    
    if target.is_file():
        errors = validate_html_file(target)
        if errors:
            print(f"❌ Validation failed for {target}:")
            for error in errors:
                print(f"   {error}")
            sys.exit(1)
        else:
            print(f"✅ {target} is valid")
            sys.exit(0)
    elif target.is_dir():
        success = validate_html_dir(target)
        sys.exit(0 if success else 1)
    else:
        print(f"❌ Invalid path: {target}")
        sys.exit(1)


if __name__ == '__main__':
    main()
