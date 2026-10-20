#!/usr/bin/env python3
"""
Site builder module - handles the build logic for quiz sites.
Separates build orchestration from template generation.
"""
import json
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict

import check_data as vocab
from template_engine import TemplateEngine


class SiteBuilder:
    """Builds static quiz site from data and templates"""
    
    def __init__(self, repo_root: Path, course_id: str, debug_mode: bool = False):
        """
        Initialize builder
        
        Args:
            repo_root: Repository root path
            course_id: Course identifier from config.json
            debug_mode: Enable debug panel in catalog page
        """
        self.repo_root = repo_root
        self.course_id = course_id
        self.debug_mode = debug_mode
        self.course_config = None
        self.course_name = None
        self.data_dir = None
        
        # Initialize template engine
        templates_dir = repo_root / "build" / "templates"
        self.template_engine = TemplateEngine(templates_dir)
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from config.json"""
        config_path = self.repo_root / "data" / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def get_course_config(self) -> Dict[str, Any]:
        """Get configuration for the current course"""
        config = self.load_config()
        for course in config.get("courses", []):
            if course["id"] == self.course_id:
                return course
        raise ValueError(f"Course '{self.course_id}' not found in config.json")
    
    def validate_config(self) -> bool:
        """
        Validate config.json for safe identifiers
        
        Returns:
            True if validation passed, False otherwise
        """
        print("🔍 Validating config.json...")
        
        config = self.load_config()
        has_errors = False
        
        # Safe pattern: lowercase letters, numbers, hyphen, underscore
        safe_id_pattern = re.compile(r'^[a-z0-9_-]+$')
        # Safe pattern for levels: letters and numbers (e.g., A1, A2, RS5)
        safe_level_pattern = re.compile(r'^[a-zA-Z0-9]+$')
        
        for course in config.get("courses", []):
            course_id = course.get("id", "")
            
            # Validate course ID
            if not safe_id_pattern.match(course_id):
                print(f"❌ Invalid course id '{course_id}': must contain only lowercase letters, numbers, hyphens, and underscores")
                has_errors = True
            
            # Validate content IDs and levels
            for content in course.get("contents", []):
                content_id = content.get("id", "")
                
                if not safe_id_pattern.match(content_id):
                    print(f"❌ Invalid content id '{content_id}' in course '{course_id}': must contain only lowercase letters, numbers, hyphens, and underscores")
                    has_errors = True
                
                # Validate levels
                for level in content.get("levels", []):
                    if not safe_level_pattern.match(level):
                        print(f"❌ Invalid level '{level}' in content '{content_id}': must contain only letters and numbers")
                        has_errors = True
        
        if has_errors:
            print("\n❌ Config validation failed. Please fix identifiers to use only safe characters.")
            print("   - Course/content IDs: lowercase letters, numbers, hyphens, underscores (a-z0-9_-)")
            print("   - Levels: letters and numbers (A1, A2, B1, RS5, etc.)")
            return False
        
        print("✅ Config validation passed\n")
        return True
    
    def get_course_data_dir(self) -> Tuple[Path, str]:
        """
        Get data directory and folder name for the course
        
        Returns:
            Tuple of (data_dir_path, course_name)
        """
        if self.course_config is None:
            self.course_config = self.get_course_config()
        
        course_name = self.course_config["name"]
        data_dir = self.repo_root / "data" / course_name
        
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        return data_dir, course_name
    
    def load_questions_from_jsonl(self, filepath: Path) -> List[Dict[str, Any]]:
        """Load questions from a JSONL file"""
        questions = []
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    questions.append(obj)
                except json.JSONDecodeError:
                    continue
        return questions
    
    def find_jsonl_files(self, content_dir: str, levels: List[str]) -> Dict[str, List[Path]]:
        """
        Find all JSONL files organized by level
        
        Args:
            content_dir: Content directory name (e.g., 'RU-TR_Words')
            levels: List of levels to search for (e.g., ['A1', 'A2', 'B1'])
            
        Returns:
            Dictionary mapping level to list of JSONL file paths
        """
        structure = defaultdict(list)
        
        for level in levels:
            level_dir = self.data_dir / content_dir / level
            if not level_dir.exists():
                continue
            
            for jsonl_file in level_dir.glob("**/*.jsonl"):
                structure[level].append(jsonl_file)
        
        return structure
    
    def validate_data(self, contents: List[Dict[str, Any]]) -> bool:
        """
        Validate all JSONL files
        
        Args:
            contents: List of content configurations
            
        Returns:
            True if validation passed, False otherwise
        """
        print("🔍 Running validation...")
        
        # Run validation with separate ID tracking for each content type
        content_ids_map = {}
        for content in contents:
            content_id = content["id"]
            content_ids_map[content_id] = set()
        
        # Find all JSONL files for validation
        all_jsonl_files = []
        for content in contents:
            content_id = content["id"]
            content_dir = content.get("dir", content_id)
            levels = content.get("levels", [])
            for level in levels:
                level_dir = self.data_dir / content_dir / level
                if level_dir.exists():
                    for jsonl_file in level_dir.glob("**/*.jsonl"):
                        all_jsonl_files.append((jsonl_file, content_id))
        
        if not all_jsonl_files:
            print("⚠️  No JSONL files found. Nothing to build.")
            return False
        
        has_errors = False
        for filepath, content_id in all_jsonl_files:
            all_ids = content_ids_map[content_id]
            _, errors_list = vocab.validate_jsonl_file_questions(filepath, all_ids)
            if errors_list:
                has_errors = True
                print(f"❌ Validation failed for {filepath.relative_to(self.repo_root)}")
        
        if has_errors:
            print("\n❌ Validation failed. Fix errors before building.")
            return False
        
        print("✅ Validation passed\n")
        return True
    
    def prepare_output_dir(self, dest_folder: str) -> Path:
        """
        Prepare output directory (clean and create)
        
        Args:
            dest_folder: Destination folder name
            
        Returns:
            Path to output directory
        """
        output_dir = self.repo_root / "html" / dest_folder
        print(f"📁 Cleaning output directory: {output_dir}")
        
        # Clean output directory efficiently
        if output_dir.exists():
            # Save .gitkeep if exists
            gitkeep_path = output_dir / '.gitkeep'
            gitkeep_exists = gitkeep_path.exists()
            
            # Remove entire directory
            shutil.rmtree(output_dir)
            
            # Recreate directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Restore .gitkeep if it existed
            if gitkeep_exists:
                gitkeep_path.touch()
        else:
            output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir
    
    def generate_assets(self, output_dir: Path, quiz_length: int):
        """
        Generate CSS and JS assets
        
        Args:
            output_dir: Output directory path
            quiz_length: Number of questions per quiz
        """
        print("📝 Generating assets...")
        
        assets_dir = output_dir / "assets"
        assets_dir.mkdir(exist_ok=True)
        
        # Generate CSS (static file, no templating needed)
        css_content = self.template_engine.get_static_file('app.css')
        (assets_dir / "app.css").write_text(css_content, encoding="utf-8")
        
        # Generate JS with template variable
        js_content = self.template_engine.render_app_js(quiz_length=quiz_length)
        (assets_dir / "app.js").write_text(js_content, encoding="utf-8")
        
        # Generate storage.js (includes storage keys and storage logic)
        storage_content = self.template_engine.get_static_file('storage.js')
        (assets_dir / "storage.js").write_text(storage_content, encoding="utf-8")
    
    def build_quiz_pages(self, output_dir: Path, contents: List[Dict[str, Any]], 
                        quiz_length: int) -> Dict[str, Dict[str, List[Path]]]:
        """
        Build all quiz pages
        
        Args:
            output_dir: Output directory path
            contents: List of content configurations
            quiz_length: Number of questions per quiz
            
        Returns:
            Content structures dictionary
        """
        print("🏗️  Building quiz pages...")
        
        content_structures = {}
        
        for content in contents:
            content_id = content["id"]
            content_dir = content.get("dir", content_id)
            content_name = content["name"]
            levels = content.get("levels", [])
            
            # Find JSONL files for this content type
            structure = self.find_jsonl_files(content_dir, levels)
            content_structures[content_id] = structure
            
            # Generate quiz pages for each level
            for level, files in structure.items():
                # Create directory for this level
                quiz_dir = output_dir / content_id / level
                quiz_dir.mkdir(parents=True, exist_ok=True)
                
                # Load and combine all questions from all files in this level
                all_questions = []
                for jsonl_file in files:
                    questions = self.load_questions_from_jsonl(jsonl_file)
                    all_questions.extend(questions)
                
                # Save combined questions.json
                questions_json_path = quiz_dir / "questions.json"
                with open(questions_json_path, "w", encoding="utf-8") as f:
                    json.dump(all_questions, f, ensure_ascii=False, indent=2)
                
                # Generate quiz HTML using template engine
                content_emoji = content.get("emoji", "📚")
                quiz_html = self.template_engine.render_quiz_page(
                    content_id=content_id,
                    level=level,
                    questions_count=len(all_questions),
                    type_label=content_name,
                    content_emoji=content_emoji
                )
                (quiz_dir / "index.html").write_text(quiz_html, encoding="utf-8")
                
                print(f"  ✓ {content_name}/{level} ({len(all_questions)} questions from {len(files)} file(s))")
        
        return content_structures
    
    def build_catalog_page(self, output_dir: Path, 
                          content_structures: Dict[str, Dict[str, List[Path]]]):
        """
        Build catalog/index page
        
        Args:
            output_dir: Output directory path
            content_structures: Dictionary of content structures
        """
        print("📋 Generating catalog page...")
        
        course_icon = self.course_config.get("icon", "📚")
        course_description = self.course_config.get("description", "")
        contents = self.course_config.get("contents", [])
        
        # Build sections data for template
        sections = []
        for content in contents:
            content_id = content["id"]
            content_name = content["name"]
            levels_list = content.get("levels", [])
            
            structure = content_structures.get(content_id, {})
            
            # Generate level cards for this content type
            level_cards = []
            for level in levels_list:
                if level in structure:
                    level_cards.append({
                        'href': f"{content_id}/{level}/index.html",
                        'level': level,
                        'content_id': content_id
                    })
            
            if level_cards:
                sections.append({
                    'name': content_name,
                    'level_cards': level_cards
                })
        
        # Render catalog page using template engine
        catalog_html = self.template_engine.render_catalog_page(
            course_name=self.course_name,
            course_description=course_description,
            course_icon=course_icon,
            sections=sections,
            debug_mode=self.debug_mode
        )
        (output_dir / "index.html").write_text(catalog_html, encoding="utf-8")
    
    def build(self) -> int:
        """
        Main build method - orchestrates the entire build process
        
        Returns:
            0 on success, 1 on failure
        """
        try:
            print(f"🔍 Building course: {self.course_id}")
            
            # Validate config.json first
            if not self.validate_config():
                return 1
            
            # Load course configuration
            self.course_config = self.get_course_config()
            self.course_name = self.course_config["name"]
            dest_folder = self.course_config.get("dest_folder", self.course_id)
            contents = self.course_config.get("contents", [])
            quiz_length = self.course_config.get("quiz_length", 5)
            
            print(f"   Name: {self.course_name}")
            print(f"   Destination: html/{dest_folder}/")
            print(f"   Contents: {len(contents)}")
            print()
            
            # Get course data directory
            self.data_dir, _ = self.get_course_data_dir()
            
            # Validate data
            if not self.validate_data(contents):
                return 1
            
            # Prepare output directory
            output_dir = self.prepare_output_dir(dest_folder)
            
            # Generate assets
            self.generate_assets(output_dir, quiz_length)
            
            # Build quiz pages
            content_structures = self.build_quiz_pages(output_dir, contents, quiz_length)
            
            # Build catalog page
            self.build_catalog_page(output_dir, content_structures)
            
            # Print summary
            print(f"\n✅ Build complete! Output: {output_dir}")
            for content in contents:
                content_id = content["id"]
                content_name = content["name"]
                if content_id in content_structures:
                    structure = content_structures[content_id]
                    total_files = sum(len(files) for files in structure.values())
                    print(f"   {content_name}: {len(structure)} levels, {total_files} source files")
            
            return 0
            
        except Exception as e:
            print(f"\n❌ Build failed: {e}")
            import traceback
            traceback.print_exc()
            return 1
