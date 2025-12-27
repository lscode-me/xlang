#!/usr/bin/env python3
"""
Content-specific validation for School course.
Orchestrates validation for all School subjects: EnGrammar, EnPhrases, EnWords, Maths.
"""
import sys
from pathlib import Path
from typing import List, Tuple


def validate_content_specific(repo_root: Path, course_id: str, content_type: str) -> int:
    """
    Run content-specific validation for School course.
    Calls validation for each subject: EnGrammar, EnPhrases, EnWords, Maths.
    
    Args:
        repo_root: Repository root path
        course_id: Course ID (should be 'sch')
        content_type: Content type to validate ('all' or specific subject)
    
    Returns:
        0 on success, 1 on failure
    """
    if course_id != "sch":
        # This module is only for School course
        return 0
    
    # Import subject-specific validators
    script_dir = Path(__file__).resolve().parent
    
    validators = []
    
    # EnGrammar validator
    grammar_check = script_dir / "EnGrammar" / "check.py"
    if grammar_check.exists():
        validators.append(("EnGrammar", grammar_check))
    
    # EnPhrases validator
    phrases_check = script_dir / "EnPhrases" / "check.py"
    if phrases_check.exists():
        validators.append(("EnPhrases", phrases_check))
    
    # EnWords validator
    words_check = script_dir / "EnWords" / "check.py"
    if words_check.exists():
        validators.append(("EnWords", words_check))
    
    # Maths validator
    maths_check = script_dir / "Maths" / "check.py"
    if maths_check.exists():
        validators.append(("Maths", maths_check))
    
    if not validators:
        print("⚠️  No subject-specific validators found")
        return 0
    
    print(f"🔍 Validating School course subjects...")
    print("=" * 60)
    
    total_errors = 0
    
    # Run each validator
    for subject_name, check_path in validators:
        # Skip if content_type is specified and doesn't match
        if content_type != "all":
            subject_lower = subject_name.lower()
            if content_type.lower() not in subject_lower:
                continue
        
        print(f"\n📚 {subject_name}")
        print("-" * 60)
        
        # Import and run the validator module
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"{subject_name}_check", check_path)
        if spec is None or spec.loader is None:
            print(f"  ⚠️  Failed to load validator for {subject_name}")
            continue
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'validate_content_specific'):
            result = module.validate_content_specific(repo_root, course_id, content_type)
            if result != 0:
                total_errors += 1
        else:
            print(f"  ⚠️  Validator for {subject_name} missing validate_content_specific function")
    
    print("\n" + "=" * 60)
    if total_errors > 0:
        print(f"FAILED. {total_errors} subject(s) had errors.")
        return 1
    else:
        print(f"✨ SUCCESS. All subjects validated successfully.")
        return 0


if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Find repo root (go up from data/School/check.py)
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    
    # Course ID is always "sch" for School course
    # Can be overridden via command line argument if needed
    course_id = sys.argv[1] if len(sys.argv) > 1 else "sch"
    content_type = sys.argv[2] if len(sys.argv) > 2 else "all"
    
    sys.exit(validate_content_specific(repo_root, course_id, content_type))

