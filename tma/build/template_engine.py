#!/usr/bin/env python3
"""
Template engine for rendering HTML/CSS/JS templates using Jinja2.
Provides simple interface for loading and rendering templates.
"""
import time
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateEngine:
    """Template engine for rendering quiz site templates"""
    
    def __init__(self, templates_dir: Path):
        """
        Initialize template engine
        
        Args:
            templates_dir: Path to templates directory
        """
        self.templates_dir = templates_dir
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Cache for static files
        self._static_cache: Dict[str, str] = {}
        
    def render_quiz_page(self, content_id: str, level: str, questions_count: int, 
                        type_label: str, content_emoji: str = "📚", cache_buster: int = None) -> str:
        """
        Render quiz page HTML
        
        Args:
            content_id: Content identifier (e.g., 'rutrwords', 'rutrphrases')
            level: Quiz level (e.g., 'A1', 'A2')
            questions_count: Number of questions in database
            type_label: Content type label (e.g., 'Слова', 'Фразы')
            content_emoji: Content emoji icon (e.g., '🇬🇧', '💬', '📚')
            cache_buster: Optional cache buster timestamp
            
        Returns:
            Rendered HTML string
        """
        if cache_buster is None:
            cache_buster = int(time.time())
            
        template = self.env.get_template('quiz_page.html')
        return template.render(
            content_id=content_id,
            level=level,
            questions_count=questions_count,
            type_label=type_label,
            content_emoji=content_emoji,
            cache_buster=cache_buster
        )
    
    def render_catalog_page(self, course_name: str, course_icon: str,
                           sections: list, debug_mode: bool = False, 
                           cache_buster: int = None, course_description: str = "") -> str:
        """
        Render catalog/index page HTML
        
        Args:
            course_name: Name of the course
            course_icon: Emoji icon for the course
            sections: List of section dictionaries with level cards
            debug_mode: Enable debug panel display
            cache_buster: Optional cache buster timestamp
            course_description: Description of the course
            
        Returns:
            Rendered HTML string
        """
        if cache_buster is None:
            cache_buster = int(time.time())
            
        template = self.env.get_template('catalog_page.html')
        return template.render(
            course_name=course_name,
            course_description=course_description,
            course_icon=course_icon,
            sections=sections,
            debug_mode=debug_mode,
            cache_buster=cache_buster
        )
    
    def render_app_js(self, quiz_length: int = 5) -> str:
        """
        Render app.js with dynamic configuration
        
        Args:
            quiz_length: Number of questions per quiz
            
        Returns:
            Rendered JavaScript string
        """
        template = self.env.get_template('app.js')
        return template.render(quiz_length=quiz_length)
    
    def get_static_file(self, filename: str) -> str:
        """
        Get contents of a static file (CSS/JS without templating)
        
        Args:
            filename: Name of the file in templates directory
            
        Returns:
            File contents as string
        """
        # Check cache first
        if filename in self._static_cache:
            return self._static_cache[filename]
        
        # Read and cache
        file_path = self.templates_dir / filename
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        self._static_cache[filename] = content
        return content
    

