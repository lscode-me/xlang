#!/usr/bin/env python3
"""
Build static Telegram Mini App for language learning quizzes.

This is the main entry point for building the quiz site.
It uses the Builder class to orchestrate the build process.

Usage:
    python build_site.py <course_id>
    
Example:
    python build_site.py turk  # Build 'turk' course
    python build_site.py sch   # Build 'sch' course
"""
import sys
from pathlib import Path

from builder import SiteBuilder


def main():
    """Main entry point"""
    try:
        # Find repository root
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent
        
        # Parse command-line arguments
        if len(sys.argv) < 2:
            print("\u274c Usage: python build_site.py <course_id> [--debug]")
            print("   Example: python build_site.py turk")
            print("   Example: python build_site.py turk --debug")
            return 1
        
        course_id = sys.argv[1]
        debug_mode = '--debug' in sys.argv
        
        if debug_mode:
            print("🔍 Debug mode enabled - storage info will be displayed")
        
        # Create builder and run build
        builder = SiteBuilder(repo_root, course_id, debug_mode=debug_mode)
        return builder.build()
        
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
