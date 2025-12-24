#!/usr/bin/env python3
"""
Simple HTTP server for development.
Serves the html/ma directory on port 8000.
"""
import http.server
import socketserver
import sys
from pathlib import Path


def main():
    """Start development server"""
    # Find repository root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    serve_dir = repo_root / "html" / "ma"
    
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
