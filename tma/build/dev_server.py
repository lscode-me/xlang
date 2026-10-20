#!/usr/bin/env python3
"""
Simple HTTP server for development.
Serves the html/{dest_folder} directory on port 8000.
dest_folder is determined from course configuration.
"""
import http.server
import socketserver
import sys
import json
from pathlib import Path


def main():
    """Start development server"""
    # Find repository root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    # Get course_id from command-line argument
    if len(sys.argv) < 2:
        print("❌ Usage: python3 dev_server.py <course_id>")
        print("   Example: python3 dev_server.py turk")
        return 1
    
    course_id = sys.argv[1]
    
    # Load config to get dest_folder
    config_file = repo_root / "data" / "config.json"
    if not config_file.exists():
        print(f"❌ Config file not found: {config_file}")
        return 1
    
    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    # Find course configuration
    course_config = None
    for course in config.get("courses", []):
        if course["id"] == course_id:
            course_config = course
            break
    
    if not course_config:
        print(f"❌ Course '{course_id}' not found in config.json")
        return 1
    
    # Get dest_folder (use course_id as fallback)
    dest_folder = course_config.get("dest_folder", course_id)
    serve_dir = repo_root / "html" / dest_folder
    
    if not serve_dir.exists():
        print(f"❌ Directory not found: {serve_dir}")
        print("   Run build_site.py first to generate the site.")
        return 1
    
    PORT = 8000
    
    # Change to the directory to serve
    import os
    os.chdir(serve_dir)
    
    Handler = http.server.SimpleHTTPRequestHandler
    
    print(f"🚀 Starting development server...")
    print(f"   Serving: {serve_dir}")
    print(f"   URL: http://localhost:{PORT}")
    print(f"   Press Ctrl+C to stop\n")
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        return 0
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
