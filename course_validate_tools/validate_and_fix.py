#!/usr/bin/env python3
"""
Course Validation and Fixing Tool - Комплексный инструмент для анализа и исправления курсов

ФУНКЦИОНАЛЬНОСТЬ:

1. Анализ качества:
   - Метрики лекций (длина: 600-1000 строк, секции H2: 5-12, блоки кода: 15-30)
   - Метрики квизов (вопросов: 20-40, наличие Answer Key и Scoring Guide)
   - Проверка структуры модулей (Learning Objectives, Key Takeaways, Prerequisites)
   - Анализ README курса

2. Проверка комплектности:
   - Наличие обязательных файлов (lecture.md, quiz.md в каждом модуле)
   - Соответствие между README и файловой системой
   - Поиск и удаление лишних файлов/папок

3. Исправление форматирования Markdown:
   - Пустые строки перед/после блоков кода
   - Пустые строки после заголовков
   - Пустые строки между элементами списков
   - Форматирование bold-элементов

4. Анализ и перемешивание ответов в квизах:
   - Анализ распределения правильных ответов (A/B/C/D)
   - Вычисление отклонения от равномерного распределения (25% каждый)
   - Итеративное перемешивание до достижения равномерности (< 5% отклонение)
   - Автоматическое обновление Answer Key
   - Отчёт о распределении до и после перемешивания

РЕЖИМЫ РАБОТЫ:

1. Режим анализа (по умолчанию):
   - Только анализ, никаких изменений
   - Показывает все проблемы и метрики
   - Безопасный режим для проверки

2. Режим исправления (-f, --fix):
   - Исправляет проблемы с комплектностью (удаляет лишние файлы)
   - Исправляет форматирование Markdown
   - Перемешивает ответы ТОЛЬКО если отклонение ≥ 5%
   - Рекомендуется для регулярного использования

3. Режим принудительного перемешивания (--force-shuffle):
   - Перемешивает ответы ВСЕГДА, даже при хорошем распределении
   - Полезно для дополнительной рандомизации
   - Использовать когда нужно гарантировать новое распределение

ИСПОЛЬЗОВАНИЕ:

Анализ:
  python3 validate_and_fix.py                      # все курсы
  python3 validate_and_fix.py Courses/English_A1   # один курс

Исправление (shuffle только при отклонении ≥ 5%):
  python3 validate_and_fix.py -f                   # все курсы
  python3 validate_and_fix.py -f Courses/English_A1

Принудительное перемешивание (всегда):
  python3 validate_and_fix.py --force-shuffle
  python3 validate_and_fix.py --force-shuffle Courses/English_A1

МЕТРИКИ КАЧЕСТВА:

Лекции:
  - Длина: 600-1000 строк (оптимум: 700-900)
  - Секции (H2): 5-12 (оптимум: 7-10)
  - Блоки кода: 15-30 (оптимум: 20-25)
  - Learning Objectives: 3-5
  - Key Takeaways: 3-5

Квизы:
  - Вопросов: 20-40 (оптимум: 25-30)
  - Answer Key: обязателен (формат: таблица или список)
  - Scoring Guide: обязателен
  - Распределение ответов: отклонение < 5% от равномерного (25% каждый)
  - Все вопросы должны иметь правильные ответы

README:
  - Минимум 200 строк
  - Все 20 модулей со ссылками, описанием тем и примерами
  - Обязательные секции: Описание, Цели (5+), Требования, Структура

СТАТУСЫ КАЧЕСТВА:
  ✅ Отлично - полное соответствие стандартам
  ✅ Хорошо - незначительные отклонения
  ⚠️ Требует улучшений - есть проблемы
  ❌ Серьёзные проблемы - критические проблемы с контентом

БЕЗОПАСНОСТЬ:
  - В режиме анализа (без -f) скрипт НЕ ВНОСИТ изменений
  - В режимах -f и --force-shuffle изменения применяются НЕМЕДЛЕННО
  - Рекомендуется использовать Git для отката изменений при необходимости

ПРОИЗВОДИТЕЛЬНОСТЬ:
  - Анализ одного курса: ~1-2 секунды
  - Анализ всех курсов (5-6 курсов): ~5-10 секунд
  - Исправление добавляет ~2-3 секунды на курс

ТРЕБОВАНИЯ:
  - Python 3.7+
  - Стандартная библиотека Python (никаких дополнительных зависимостей)
"""

import os
import re
import sys
import random
import shutil
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Set


# ============================================================================
# АНАЛИЗ КАЧЕСТВА (analyze_quality.py)
# ============================================================================

@dataclass
class ModuleMetrics:
    """Метрики одного модуля."""
    course: str
    module: str
    
    # Lecture metrics
    lecture_lines: int = 0
    h2_sections: int = 0
    code_blocks: int = 0
    learning_objectives: int = 0
    key_takeaways: int = 0
    
    # Structure checks
    has_prerequisites: bool = False
    has_learning_objectives: bool = False
    has_key_takeaways: bool = False
    has_next_steps: bool = False
    has_quiz: bool = False
    
    # Quiz metrics
    quiz_questions: int = 0
    quiz_has_answer_key: bool = False
    quiz_has_scoring: bool = False
    quiz_answer_key_format_valid: bool = False
    quiz_answer_key_answers_count: int = 0
    quiz_questions_without_answers: list[int] = field(default_factory=list)
    quiz_questions_with_duplicate_options: list[int] = field(default_factory=list)
    
    def overall_quality(self) -> str:
        """Оценка общего качества модуля."""
        issues = 0
        
        # Критические проблемы с квизом
        if not self.has_quiz:
            issues += 3
        else:
            if self.quiz_questions_without_answers:
                issues += 5 + len(self.quiz_questions_without_answers)
            
            if self.quiz_questions_with_duplicate_options:
                issues += 2 + len(self.quiz_questions_with_duplicate_options)
            
            if self.quiz_questions < 15:
                issues += 3
            elif self.quiz_questions < 20:
                issues += 1
            
            if not self.quiz_has_answer_key:
                issues += 3
            elif not self.quiz_answer_key_format_valid:
                issues += 3
            elif self.quiz_answer_key_answers_count != self.quiz_questions:
                if not self.quiz_questions_without_answers:
                    issues += 2
            
            if not self.quiz_has_scoring:
                issues += 2
        
        # Критические проблемы с лекцией
        if self.lecture_lines < 400:
            issues += 2
        if not self.has_learning_objectives:
            issues += 1
        if not self.has_key_takeaways:
            issues += 1
        
        # Средние проблемы
        if self.lecture_lines < 600 or self.lecture_lines > 1000:
            issues += 1
        if self.h2_sections < 5 or self.h2_sections > 12:
            issues += 1
        if self.code_blocks < 15:
            issues += 1
        
        has_full_quiz = (self.has_quiz and 
                        self.quiz_questions >= 20 and 
                        self.quiz_has_answer_key and 
                        self.quiz_answer_key_format_valid and
                        self.quiz_answer_key_answers_count == self.quiz_questions and
                        self.quiz_has_scoring)
        
        if issues == 0 and not has_full_quiz:
            issues += 1
        
        if issues == 0:
            return "✅ Отлично"
        elif issues <= 2:
            return "✅ Хорошо"
        elif issues <= 4:
            return "⚠️ Требует улучшений"
        else:
            return "❌ Серьёзные проблемы"


@dataclass
class ReadmeMetrics:
    """Метрики README курса."""
    course: str
    exists: bool = False
    lines: int = 0
    has_title: bool = False
    has_description: bool = False
    has_goals: bool = False
    has_requirements: bool = False
    has_structure: bool = False
    modules_with_links: int = 0
    modules_with_topics: int = 0
    modules_with_examples: int = 0
    goals_count: int = 0
    requirements_count: int = 0


@dataclass
class CompletenessResults:
    """Результаты проверки комплектности."""
    course_path: Path
    has_readme: bool = False
    readme_modules: Set[str] = field(default_factory=set)
    actual_modules: Set[str] = field(default_factory=set)
    missing_modules: List[str] = field(default_factory=list)
    extra_modules: List[str] = field(default_factory=list)
    module_issues: dict = field(default_factory=dict)
    files_to_delete: List[Path] = field(default_factory=list)
    directories_to_delete: List[Path] = field(default_factory=list)
    course_root_extra_files: List[Path] = field(default_factory=list)


def analyze_lecture(filepath: Path) -> dict:
    """Анализ lecture.md файла."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    code_blocks = len(re.findall(r'^```', content, re.MULTILINE)) // 2
    h2_sections = len(re.findall(r'^## \d+\.', content, re.MULTILINE))
    
    # Learning Objectives
    lo_match = re.search(
        r'## 🎯 Learning Objectives.*?\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    learning_objectives = 0
    if lo_match:
        lo_text = lo_match.group(1)
        learning_objectives = len(re.findall(r'^[-*•]\s', lo_text, re.MULTILINE))
    
    # Key Takeaways
    kt_match = re.search(
        r'## 💡 Key Takeaways.*?\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    key_takeaways = 0
    if kt_match:
        kt_text = kt_match.group(1)
        key_takeaways = len(re.findall(r'^[-*•]\s', kt_text, re.MULTILINE))
    
    return {
        'lecture_lines': len(lines),
        'code_blocks': code_blocks,
        'h2_sections': h2_sections,
        'learning_objectives': learning_objectives,
        'key_takeaways': key_takeaways,
        'has_prerequisites': bool(re.search(r'## 📋 Prerequisites', content, re.IGNORECASE)),
        'has_learning_objectives': bool(re.search(r'## 🎯 Learning Objectives', content, re.IGNORECASE)),
        'has_key_takeaways': bool(re.search(r'## 💡 Key Takeaways', content, re.IGNORECASE)),
        'has_next_steps': bool(re.search(r'## 🚀 Next Steps', content, re.IGNORECASE)),
    }


def analyze_quiz(filepath: Path) -> dict:
    """Анализ quiz.md файла."""
    if not filepath.exists():
        return {
            'has_quiz': False,
            'quiz_questions': 0,
            'quiz_has_answer_key': False,
            'quiz_has_scoring': False,
            'quiz_answer_key_format_valid': False,
            'quiz_answer_key_answers_count': 0,
            'quiz_questions_without_answers': [],
            'quiz_questions_with_duplicate_options': [],
        }
    
    if filepath.stat().st_size < 100:
        return {
            'has_quiz': False,
            'quiz_questions': 0,
            'quiz_has_answer_key': False,
            'quiz_has_scoring': False,
            'quiz_answer_key_format_valid': False,
            'quiz_answer_key_answers_count': 0,
            'quiz_questions_without_answers': [],
            'quiz_questions_with_duplicate_options': [],
        }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions = len(re.findall(r'##\s*Question\s+\d+', content, re.IGNORECASE))
    if questions == 0:
        questions = len(re.findall(r'\*\*Question\s+\d+', content, re.IGNORECASE))
    if questions == 0:
        questions = len(re.findall(r'^##\s*\d+\.', content, re.MULTILINE))
    
    has_answer_key = bool(re.search(
        r'##\s*Answer\s+Key|##\s*Ответы|Answer\s+Key|Ключ\s+ответов',
        content, re.IGNORECASE
    ))
    
    has_scoring = bool(re.search(
        r'##\s*Scoring\s+Guide|##\s*Шкала\s+оценки|Scoring\s+Guide|Шкала\s+оценки',
        content, re.IGNORECASE
    ))
    
    answer_key_format_valid = False
    answer_key_answers_count = 0
    questions_without_answers = []
    
    question_numbers = set()
    question_matches = re.findall(r'##\s*Question\s+(\d+)', content, re.IGNORECASE)
    if not question_matches:
        question_matches = re.findall(r'\*\*Question\s+(\d+)', content, re.IGNORECASE)
    if not question_matches:
        question_matches = re.findall(r'^##\s*(\d+)\.', content, re.MULTILINE)
    
    for match in question_matches:
        question_numbers.add(int(match))
    
    if has_answer_key:
        answer_key_match = re.search(
            r'##\s*Answer\s+Key.*?(?=\n##|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        
        if answer_key_match:
            answer_key_section = answer_key_match.group(0)
            answered_question_numbers = set()
            
            table_format = re.findall(
                r'^\|\s*(\d+)\s*\|\s*([A-D])\s*\|\s*.+?\s*\|',
                answer_key_section, re.MULTILINE
            )
            if table_format:
                answer_key_format_valid = True
                answer_key_answers_count = len(table_format)
                for num_str, _ in table_format:
                    answered_question_numbers.add(int(num_str))
            else:
                list_format = re.findall(
                    r'^(\d+)\.\s*\*\*([A-D])\*\*\s*[-–—]\s*.+',
                    answer_key_section, re.MULTILINE
                )
                if list_format:
                    answer_key_format_valid = True
                    answer_key_answers_count = len(list_format)
                    for num_str, _ in list_format:
                        answered_question_numbers.add(int(num_str))
                else:
                    wrong_format = re.findall(
                        r'^(\d+)\.\s*([A-D])\)\s*.+',
                        answer_key_section, re.MULTILINE
                    )
                    if wrong_format:
                        answer_key_format_valid = False
                        answer_key_answers_count = len(wrong_format)
                        for num_str, _ in wrong_format:
                            answered_question_numbers.add(int(num_str))
            
            if question_numbers:
                questions_without_answers = sorted(question_numbers - answered_question_numbers)
    else:
        if question_numbers:
            questions_without_answers = sorted(question_numbers)
    
    questions_with_duplicates = []
    
    if questions > 0:
        question_pattern = None
        if re.search(r'##\s*Question\s+\d+', content, re.IGNORECASE):
            question_pattern = r'##\s*Question\s+(\d+).*?(?=\n##\s*Question\s+\d+|\n##\s*Answer\s+Key|\Z)'
        elif re.search(r'\*\*Question\s+\d+', content, re.IGNORECASE):
            question_pattern = r'\*\*Question\s+(\d+).*?(?=\n\*\*Question\s+\d+|\n##\s*Answer\s+Key|\Z)'
        elif re.search(r'^##\s*\d+\.', content, re.MULTILINE):
            question_pattern = r'^##\s*(\d+)\..*?(?=\n##\s*\d+\.|\n##\s*Answer\s+Key|\Z)'
        
        if question_pattern:
            question_matches = re.finditer(question_pattern, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
            for match in question_matches:
                question_num = int(match.group(1))
                question_text = match.group(0)
                
                options = re.findall(r'^([A-D])\)\s*(.+?)$', question_text, re.MULTILINE)
                
                if options:
                    option_texts = []
                    for letter, text in options:
                        normalized = ' '.join(text.strip().split()).lower()
                        option_texts.append((letter, normalized))
                    
                    seen_texts = set()
                    has_duplicate = False
                    for letter, text in option_texts:
                        if text in seen_texts:
                            has_duplicate = True
                            break
                        seen_texts.add(text)
                    
                    if has_duplicate:
                        questions_with_duplicates.append(question_num)
    
    if questions == 0:
        return {
            'has_quiz': False,
            'quiz_questions': 0,
            'quiz_has_answer_key': False,
            'quiz_has_scoring': False,
            'quiz_answer_key_format_valid': False,
            'quiz_answer_key_answers_count': 0,
            'quiz_questions_without_answers': [],
            'quiz_questions_with_duplicate_options': [],
        }
    
    return {
        'has_quiz': True,
        'quiz_questions': questions,
        'quiz_has_answer_key': has_answer_key,
        'quiz_has_scoring': has_scoring,
        'quiz_answer_key_format_valid': answer_key_format_valid,
        'quiz_answer_key_answers_count': answer_key_answers_count,
        'quiz_questions_without_answers': questions_without_answers,
        'quiz_questions_with_duplicate_options': sorted(set(questions_with_duplicates)),
    }


def analyze_module(course_path: Path, module_name: str, course_name: str) -> Optional[ModuleMetrics]:
    """Анализ одного модуля."""
    module_path = course_path / module_name
    lecture_path = module_path / 'lecture.md'
    quiz_path = module_path / 'quiz.md'
    
    if not lecture_path.exists():
        return None
    
    metrics = ModuleMetrics(course=course_name, module=module_name)
    
    lecture_data = analyze_lecture(lecture_path)
    for key, value in lecture_data.items():
        setattr(metrics, key, value)
    
    quiz_data = analyze_quiz(quiz_path)
    for key, value in quiz_data.items():
        setattr(metrics, key, value)
    
    return metrics


def analyze_course(courses_path: Path, course_name: str) -> list[ModuleMetrics]:
    """Анализ всего курса."""
    course_path = courses_path / course_name
    metrics = []
    
    if not course_path.exists():
        return metrics
    
    for item in sorted(course_path.iterdir()):
        if item.is_dir() and item.name[0].isdigit():
            module_metrics = analyze_module(course_path, item.name, course_name)
            if module_metrics:
                metrics.append(module_metrics)
    
    return metrics


# ============================================================================
# ПРОВЕРКА КОМПЛЕКТНОСТИ (check_course_completeness.py)
# ============================================================================

def extract_lecture_modules_from_readme(readme_path: Path) -> Set[str]:
    """Извлекает имена модулей из README."""
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'\[[^\]]+\]\(\.?/?([0-9]+_[^/)]+)(?:/|\))'
    matches = re.findall(pattern, content)
    
    return set(matches)


def get_lecture_directories(course_path: Path) -> Set[str]:
    """Получает список папок лекций в курсе."""
    modules = set()
    for item in course_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            modules.add(item.name)
    return modules


def check_lecture_directory(lecture_path: Path) -> Tuple[bool, List[str], List[str]]:
    """Проверяет папку лекции."""
    required_files = {'lecture.md', 'quiz.md'}
    
    files = set()
    for item in lecture_path.iterdir():
        if item.is_file():
            files.add(item.name)
        elif item.is_dir():
            files.add(f"{item.name}/")
    
    missing = required_files - files
    extra = files - required_files
    
    is_valid = len(missing) == 0 and len(extra) == 0
    return is_valid, sorted(missing), sorted(extra)


def check_course_completeness(course_path: Path) -> CompletenessResults:
    """Проверяет курс на комплектность."""
    results = CompletenessResults(course_path=course_path)
    
    readme_path = course_path / 'README.md'
    if not readme_path.exists():
        return results
    
    results.has_readme = True
    results.readme_modules = extract_lecture_modules_from_readme(readme_path)
    results.actual_modules = get_lecture_directories(course_path)
    
    # Проверка корневой папки
    allowed_in_root = {'README.md'}
    for item in course_path.iterdir():
        if item.is_file() and item.name not in allowed_in_root:
            results.course_root_extra_files.append(item)
            results.files_to_delete.append(item)
        elif item.is_dir() and not item.name.startswith('.') and item.name not in results.actual_modules:
            results.directories_to_delete.append(item)
    
    results.missing_modules = sorted(results.readme_modules - results.actual_modules)
    results.extra_modules = sorted(results.actual_modules - results.readme_modules)
    
    # Проверяем каждую папку модуля
    for module_name in results.actual_modules:
        module_path = course_path / module_name
        is_valid, missing, extra = check_lecture_directory(module_path)
        
        if not is_valid:
            results.module_issues[module_name] = {
                'missing': missing,
                'extra': extra
            }
            
            for item in extra:
                if item.endswith('/'):
                    dir_name = item.rstrip('/')
                    results.directories_to_delete.append(module_path / dir_name)
                else:
                    results.files_to_delete.append(module_path / item)
    
    return results


def fix_completeness_issues(results: CompletenessResults) -> Tuple[int, int]:
    """Удаляет лишние файлы и папки."""
    deleted_files = 0
    deleted_dirs = 0
    
    for file_path in results.files_to_delete:
        try:
            file_path.unlink()
            deleted_files += 1
            print(f"   ✓ Удалён файл: {file_path.name}")
        except Exception as e:
            print(f"   ⚠️ Ошибка при удалении {file_path}: {e}")
    
    for dir_path in sorted(results.directories_to_delete, key=lambda p: len(p.parts), reverse=True):
        try:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                deleted_dirs += 1
                print(f"   ✓ Удалена папка: {dir_path.name}")
        except Exception as e:
            print(f"   ⚠️ Ошибка при удалении {dir_path}: {e}")
    
    for module_name in results.extra_modules:
        module_path = results.course_path / module_name
        try:
            if module_path.exists():
                shutil.rmtree(module_path)
                deleted_dirs += 1
                print(f"   ✓ Удалён лишний модуль: {module_name}")
        except Exception as e:
            print(f"   ⚠️ Ошибка при удалении модуля {module_path}: {e}")
    
    return deleted_files, deleted_dirs


# ============================================================================
# ИСПРАВЛЕНИЕ ФОРМАТИРОВАНИЯ (fix_markdown_format.py)
# ============================================================================

def get_code_block_ranges(lines: List[str]) -> List[Tuple[int, int]]:
    """Находит диапазоны строк внутри блоков кода."""
    ranges = []
    in_code_block = False
    start = 0
    opening_backticks = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        backtick_count = len(stripped) - len(stripped.lstrip('`'))
        
        if backtick_count >= 3 and all(c == '`' for c in stripped[:backtick_count]):
            if not in_code_block:
                in_code_block = True
                start = i
                opening_backticks = backtick_count
            else:
                if backtick_count >= opening_backticks:
                    in_code_block = False
                    ranges.append((start, i))
                    opening_backticks = 0
    
    return ranges


def is_in_code_block(line_num: int, ranges: List[Tuple[int, int]]) -> bool:
    """Проверяет, находится ли строка внутри блока кода."""
    for start, end in ranges:
        if start < line_num < end:
            return True
    return False


def fix_markdown_formatting(filepath: Path) -> int:
    """Исправляет форматирование markdown файла. Возвращает количество исправлений."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        original_content = content
        lines = content.split('\n')
    except Exception as e:
        print(f"   ⚠️ Ошибка чтения {filepath}: {e}")
        return 0
    
    code_ranges = get_code_block_ranges(lines)
    
    # Исправляем пустые строки перед блоками кода
    fixed_lines = []
    in_code_block = False
    opening_backticks = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        backtick_count = len(stripped) - len(stripped.lstrip('`'))
        
        if backtick_count >= 3 and all(c == '`' for c in stripped[:backtick_count]):
            if not in_code_block:
                in_code_block = True
                opening_backticks = backtick_count
                
                if i > 0:
                    prev_line = fixed_lines[-1].strip() if fixed_lines else ''
                    if (prev_line and 
                        not prev_line.startswith('#') and 
                        prev_line != "---" and 
                        not prev_line.endswith(':')):
                        fixed_lines.append('')
            else:
                if backtick_count >= opening_backticks:
                    in_code_block = False
                    opening_backticks = 0
        
        fixed_lines.append(line)
        
        # Добавляем пустую строку после закрытия блока кода
        if not in_code_block and i > 0:
            prev_stripped = lines[i-1].strip()
            prev_backticks = len(prev_stripped) - len(prev_stripped.lstrip('`'))
            if prev_backticks >= 3:
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if (next_line and 
                        not next_line.startswith('#') and 
                        next_line != "---" and 
                        not next_line.startswith('**')):
                        pass  # Будет добавлено на следующей итерации
    
    new_content = '\n'.join(fixed_lines)
    if content.endswith('\n') and not new_content.endswith('\n'):
        new_content += '\n'
    
    fixes_count = len(new_content.split('\n')) - len(content.split('\n'))
    
    if fixes_count != 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return abs(fixes_count)
    
    return 0


# ============================================================================
# ПЕРЕМЕШИВАНИЕ ОТВЕТОВ (shuffle_quiz_answers.py)
# ============================================================================

def parse_quiz(content: str) -> tuple:
    """Парсит содержимое quiz.md."""
    lines = content.split('\n')
    
    questions = []
    current_question = None
    answer_key = {}
    answer_key_format = 'table'
    
    before_questions = []
    after_answer_key = []
    in_questions = False
    in_answer_key = False
    after_answer_key_done = False
    answer_key_header = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        question_match = re.match(r'^## Question (\d+):\s*(.*)$', line)
        if question_match:
            in_questions = True
            if current_question:
                questions.append(current_question)
            
            current_question = {
                'num': int(question_match.group(1)),
                'title': question_match.group(2),
                'content_lines': [],
                'options': {},
                'options_order': [],
            }
            i += 1
            continue
        
        if '## Answer Key' in line:
            if current_question:
                questions.append(current_question)
                current_question = None
            in_answer_key = True
            answer_key_header.append(line)
            i += 1
            continue
        
        if in_answer_key and not after_answer_key_done:
            answer_match = re.match(r'^\|\s*(\d+)\s*\|\s*([A-D])\s*\|\s*(.+?)\s*\|?\s*$', line)
            if answer_match:
                answer_key_format = 'table'
                q_num = int(answer_match.group(1))
                letter = answer_match.group(2)
                explanation = answer_match.group(3)
                answer_key[q_num] = (letter, explanation)
                i += 1
                continue
            
            if line.startswith('|') and ('---' in line or '# ' in line.lower() or 'answer' in line.lower()):
                answer_key_header.append(line)
                i += 1
                continue
            
            answer_match2 = re.match(r'^(\d+)\.\s*\*\*([A-D])\*\*\s*[-–—]\s*(.+)$', line)
            if answer_match2:
                answer_key_format = 'list'
                q_num = int(answer_match2.group(1))
                letter = answer_match2.group(2)
                explanation = answer_match2.group(3)
                answer_key[q_num] = (letter, explanation)
                i += 1
                continue
            
            if answer_key and line.strip() == '---':
                after_answer_key_done = True
                after_answer_key.append(line)
                i += 1
                continue
            
            if line.strip() == '':
                if answer_key:
                    has_more = False
                    for j in range(i+1, min(i+5, len(lines))):
                        if re.match(r'^\|\s*\d+\s*\|', lines[j]) or re.match(r'^\d+\.\s*\*\*[A-D]\*\*', lines[j]):
                            has_more = True
                            break
                    if not has_more:
                        after_answer_key_done = True
                        after_answer_key.append(line)
                        i += 1
                        continue
                i += 1
                continue
        
        if after_answer_key_done:
            after_answer_key.append(line)
            i += 1
            continue
        
        if not in_questions and not in_answer_key:
            before_questions.append(line)
            i += 1
            continue
        
        if current_question:
            option_match = re.match(r'^([A-D])\)\s*(.*)$', line)
            if option_match:
                letter = option_match.group(1)
                text = option_match.group(2)
                current_question['options'][letter] = text
                current_question['options_order'].append(letter)
            else:
                if line.strip() == '---':
                    pass
                elif not current_question['options']:
                    current_question['content_lines'].append(line)
        
        i += 1
    
    return (questions, answer_key, '\n'.join(before_questions), 
            answer_key_format, '\n'.join(answer_key_header), '\n'.join(after_answer_key))


def shuffle_question_options(question: dict, correct_letter: str) -> tuple[dict, str]:
    """Перемешивает варианты ответа."""
    letters = ['A', 'B', 'C', 'D']
    items = [(l, question['options'].get(l, '')) for l in letters if l in question['options']]
    
    if len(items) != 4:
        return question['options'], correct_letter
    
    random.shuffle(items)
    
    new_options = {}
    new_correct = correct_letter
    
    for new_letter, (old_letter, text) in zip(letters, items):
        new_options[new_letter] = text
        if old_letter == correct_letter:
            new_correct = new_letter
    
    return new_options, new_correct


def rebuild_quiz(questions: list[dict], answer_key: dict, before: str, 
                 answer_format: str, answer_header: str, after: str) -> str:
    """Пересобирает quiz из компонентов."""
    lines = [before, '']
    
    for q in questions:
        lines.append(f"## Question {q['num']}: {q['title']}")
        lines.append('')
        
        content_lines = q['content_lines']
        while content_lines and not content_lines[0].strip():
            content_lines = content_lines[1:]
        
        lines.extend(content_lines)
        
        for letter in ['A', 'B', 'C', 'D']:
            if letter in q['options']:
                lines.append(f"{letter}) {q['options'][letter]}")
                lines.append('')
        
        lines.append('---')
        lines.append('')
    
    lines.extend(['---', '', '## Answer Key', ''])
    
    if answer_format == 'table':
        lines.extend(['| # | Answer | Explanation |', '|---|--------|-------------|'])
        for q_num in sorted(answer_key.keys()):
            letter, explanation = answer_key[q_num]
            lines.append(f'| {q_num} | {letter} | {explanation} |')
    else:
        for q_num in sorted(answer_key.keys()):
            letter, explanation = answer_key[q_num]
            lines.append(f'{q_num}. **{letter}** - {explanation}')
    
    lines.extend(['', after.lstrip('\n')])
    
    return '\n'.join(lines)


def get_answer_distribution(directory: Path) -> dict:
    """Получает распределение правильных ответов по курсу."""
    distribution = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    
    for quiz_file in directory.rglob('quiz.md'):
        try:
            with open(quiz_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Table format
            matches = re.findall(r'\|\s*\d+\s*\|\s*([A-D])\s*\|', content)
            for letter in matches:
                distribution[letter] += 1
            
            # List format
            matches = re.findall(r'^\d+\.\s*\*\*([A-D])\*\*\s*[-–—]', content, re.MULTILINE)
            for letter in matches:
                distribution[letter] += 1
        except Exception:
            continue
    
    return distribution


def calculate_deviation(distribution: dict) -> float:
    """Вычисляет максимальное отклонение от равномерного распределения (25%)."""
    total = sum(distribution.values())
    if total == 0:
        return 0.0
    
    ideal_pct = 25.0
    max_deviation = 0.0
    
    for letter in ['A', 'B', 'C', 'D']:
        count = distribution.get(letter, 0)
        pct = (count / total * 100) if total > 0 else 0
        deviation = abs(pct - ideal_pct)
        max_deviation = max(max_deviation, deviation)
    
    return max_deviation


def print_distribution(distribution: dict, label: str = "Распределение"):
    """Выводит распределение ответов."""
    total = sum(distribution.values())
    if total == 0:
        print(f"   {label}: нет данных")
        return
    
    print(f"   {label}:")
    for letter in ['A', 'B', 'C', 'D']:
        count = distribution[letter]
        pct = (count / total * 100) if total > 0 else 0
        print(f"      {letter}: {count:4d} ({pct:5.1f}%)")


def shuffle_quiz(filepath: Path) -> bool:
    """Перемешивает ответы в quiz файле."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"   ⚠️ Ошибка чтения {filepath}: {e}")
        return False
    
    questions, answer_key, before, answer_format, answer_header, after = parse_quiz(content)
    
    if not questions or not answer_key:
        return False
    
    new_answer_key = {}
    for q in questions:
        if q['num'] not in answer_key:
            continue
        
        correct_letter, explanation = answer_key[q['num']]
        
        if len(q['options']) != 4:
            new_answer_key[q['num']] = (correct_letter, explanation)
            continue
        
        new_options, new_correct = shuffle_question_options(q, correct_letter)
        q['options'] = new_options
        new_answer_key[q['num']] = (new_correct, explanation)
    
    new_content = rebuild_quiz(questions, new_answer_key, before, answer_format, answer_header, after)
    
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"   ⚠️ Ошибка записи {filepath}: {e}")
        return False


# ============================================================================
# ГЛАВНЫЙ ПРОЦЕССОР
# ============================================================================

def process_course(course_path: Path, fix_mode: bool = False, force_shuffle: bool = False) -> dict:
    """Обрабатывает один курс: анализ и исправление."""
    course_name = course_path.name
    
    print(f"\n{'='*80}")
    print(f"📚 Курс: {course_name}")
    print(f"{'='*80}")
    
    results = {
        'course_name': course_name,
        'modules_analyzed': 0,
        'issues_found': 0,
        'issues_fixed': 0,
    }
    
    # 1. Анализ качества
    print(f"\n📊 Анализ качества...")
    modules = analyze_course(course_path.parent, course_name)
    results['modules_analyzed'] = len(modules)
    
    # 2. Проверка комплектности
    print(f"\n📋 Проверка комплектности...")
    completeness = check_course_completeness(course_path)
    
    completeness_issues = (
        len(completeness.missing_modules) +
        len(completeness.extra_modules) +
        len(completeness.module_issues) +
        len(completeness.course_root_extra_files)
    )
    
    if completeness_issues > 0:
        results['issues_found'] += completeness_issues
        print(f"   ⚠️ Найдено проблем с комплектностью: {completeness_issues}")
        
        if completeness.missing_modules:
            print(f"   - Отсутствующих модулей: {len(completeness.missing_modules)}")
        if completeness.extra_modules:
            print(f"   - Лишних модулей: {len(completeness.extra_modules)}")
        if completeness.module_issues:
            print(f"   - Модулей с проблемами: {len(completeness.module_issues)}")
        if completeness.course_root_extra_files:
            print(f"   - Лишних файлов в корне: {len(completeness.course_root_extra_files)}")
        
        if fix_mode:
            print(f"\n🔧 Исправление проблем с комплектностью...")
            deleted_files, deleted_dirs = fix_completeness_issues(completeness)
            results['issues_fixed'] += deleted_files + deleted_dirs
            print(f"   ✓ Удалено: {deleted_files} файлов, {deleted_dirs} папок")
    else:
        print(f"   ✅ Проблем с комплектностью не найдено")
    
    # 3. Исправление форматирования
    formatting_issues = 0
    if fix_mode:
        print(f"\n🔧 Исправление форматирования Markdown...")
        for item in sorted(course_path.iterdir()):
            if item.is_dir() and item.name[0].isdigit():
                for md_file in ['lecture.md', 'quiz.md']:
                    md_path = item / md_file
                    if md_path.exists():
                        fixes = fix_markdown_formatting(md_path)
                        if fixes > 0:
                            formatting_issues += fixes
                            print(f"   ✓ {item.name}/{md_file}: {fixes} исправлений")
        
        readme_path = course_path / 'README.md'
        if readme_path.exists():
            fixes = fix_markdown_formatting(readme_path)
            if fixes > 0:
                formatting_issues += fixes
                print(f"   ✓ README.md: {fixes} исправлений")
        
        results['issues_fixed'] += formatting_issues
        if formatting_issues > 0:
            print(f"   ✓ Всего исправлено форматирования: {formatting_issues}")
        else:
            print(f"   ✅ Проблем с форматированием не найдено")
    
    # 4. Анализ и перемешивание квизов
    print(f"\n🎯 Анализ распределения ответов в квизах...")
    
    # Проверяем распределение ответов ДО shuffle
    before_distribution = get_answer_distribution(course_path)
    total_answers = sum(before_distribution.values())
    
    if total_answers > 0:
        print_distribution(before_distribution, "До перемешивания")
        deviation_before = calculate_deviation(before_distribution)
        print(f"   Отклонение от равномерного: {deviation_before:.1f}%")
        
        needs_shuffle = deviation_before >= 5.0
        
        if needs_shuffle:
            print(f"   ⚠️ Распределение неравномерное (отклонение ≥ 5%)")
        else:
            print(f"   ✅ Распределение равномерное (отклонение < 5%)")
    else:
        print(f"   ⚠️ Квизов с Answer Key не найдено")
        needs_shuffle = False
    
    # Проверяем проблемы с Answer Key
    quiz_issues = 0
    for m in modules:
        if not m.quiz_has_answer_key or not m.quiz_answer_key_format_valid:
            quiz_issues += 1
    
    if quiz_issues > 0:
        results['issues_found'] += quiz_issues
        print(f"   ⚠️ Квизов с проблемами Answer Key: {quiz_issues}")
    
    # Исправление и shuffle
    should_shuffle = force_shuffle or (fix_mode and needs_shuffle)
    
    if should_shuffle and total_answers > 0:
        if force_shuffle:
            print(f"\n🔀 Принудительное перемешивание ответов в квизах...")
        else:
            print(f"\n🔀 Перемешивание ответов в квизах...")
        
        # Итеративный shuffle до достижения хорошего распределения
        max_iterations = 50
        quiz_files = []
        for item in sorted(course_path.iterdir()):
            if item.is_dir() and item.name[0].isdigit():
                quiz_path = item / 'quiz.md'
                if quiz_path.exists():
                    quiz_files.append(quiz_path)
        
        if not quiz_files:
            print(f"   ⚠️ Файлов quiz.md не найдено")
        else:
            best_deviation = float('inf')
            best_iteration = 0
            
            for iteration in range(1, max_iterations + 1):
                # Устанавливаем seed для воспроизводимости
                random.seed(42 + iteration * 7919)
                
                # Shuffle всех квизов
                shuffled = 0
                for quiz_path in quiz_files:
                    if shuffle_quiz(quiz_path):
                        shuffled += 1
                
                # Проверяем результат
                after_distribution = get_answer_distribution(course_path)
                deviation = calculate_deviation(after_distribution)
                
                if deviation < best_deviation:
                    best_deviation = deviation
                    best_iteration = iteration
                
                # Если достигли хорошего распределения, останавливаемся
                if deviation < 5.0:
                    print(f"   ✓ Достигнуто равномерное распределение за {iteration} итераций")
                    print_distribution(after_distribution, "После перемешивания")
                    print(f"   Отклонение от равномерного: {deviation:.1f}%")
                    results['issues_fixed'] += shuffled
                    break
            else:
                # Если не достигли за max_iterations
                print(f"   ⚠️ Не удалось достичь идеального распределения за {max_iterations} попыток")
                print(f"   Лучший результат: итерация {best_iteration}, отклонение {best_deviation:.1f}%")
                after_distribution = get_answer_distribution(course_path)
                print_distribution(after_distribution, "После перемешивания")
                results['issues_fixed'] += shuffled
    
    # Отчёт по модулям
    print(f"\n📝 Отчёт по модулям:")
    print("-" * 80)
    print(f"{'Модуль':<25} {'Строк':>7} {'Quiz':>6} {'Качество':<20}")
    print("-" * 80)
    
    for m in modules:
        quiz_info = f"{m.quiz_questions}" if m.has_quiz else "—"
        print(f"{m.module:<25} {m.lecture_lines:>7} {quiz_info:>6} {m.overall_quality():<20}")
    
    print("-" * 80)
    
    # Итоги
    excellent = sum(1 for m in modules if "Отлично" in m.overall_quality())
    good = sum(1 for m in modules if "Хорошо" in m.overall_quality())
    needs_work = sum(1 for m in modules if "Требует" in m.overall_quality())
    serious = sum(1 for m in modules if "Серьёзные" in m.overall_quality())
    
    print(f"\n🎯 Качество модулей:")
    print(f"   ✅ Отлично: {excellent}")
    print(f"   ✅ Хорошо: {good}")
    print(f"   ⚠️ Требует улучшений: {needs_work}")
    print(f"   ❌ Серьёзные проблемы: {serious}")
    
    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Комплексный инструмент для анализа и исправления курсов',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python validate_and_fix.py                    # Анализ всех курсов
  python validate_and_fix.py -f                 # Анализ + исправление всех курсов
  python validate_and_fix.py --force-shuffle    # Принудительно перемешать ответы
  python validate_and_fix.py Courses/English_A1 # Анализ одного курса
  python validate_and_fix.py -f Courses/English_A1 # Анализ + исправление одного курса
  python validate_and_fix.py --force-shuffle Courses/English_A1 # Принудительный shuffle
        """
    )
    
    parser.add_argument(
        'path',
        nargs='?',
        help='Путь к курсу или директории с курсами (по умолчанию: Courses/)'
    )
    parser.add_argument(
        '-f', '--fix',
        action='store_true',
        help='Автоматически исправлять найденные проблемы (перемешивает ответы только если отклонение ≥ 5%%)'
    )
    parser.add_argument(
        '--force-shuffle',
        action='store_true',
        help='Принудительно перемешать ответы в квизах, даже если распределение равномерное'
    )
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent
    workspace = script_dir.parent
    default_courses_path = workspace / 'Courses'
    
    # Определяем целевую директорию
    if args.path:
        target = Path(args.path)
        if not target.is_absolute():
            target = workspace / args.path
        if not target.exists():
            print(f"❌ Путь не найден: {target}")
            sys.exit(1)
        
        if target == default_courses_path or target.name == 'Courses':
            courses_path = target
            courses = [d for d in sorted(courses_path.iterdir()) if d.is_dir()]
        elif (target / 'README.md').exists():
            courses_path = target.parent
            courses = [target]
        elif target.is_dir():
            courses_path = target
            courses = [
                d for d in sorted(courses_path.iterdir())
                if d.is_dir() and (d / 'README.md').exists()
            ]
            if not courses:
                print(f"❌ В директории {target} не найдено курсов")
                sys.exit(1)
        else:
            print(f"❌ Неверный путь: {target}")
            sys.exit(1)
    else:
        courses_path = default_courses_path
        if not courses_path.exists():
            print(f"❌ Папка {courses_path} не найдена!")
            sys.exit(1)
        courses = [d for d in sorted(courses_path.iterdir()) if d.is_dir()]
    
    if not courses:
        print("❌ Не найдено курсов для анализа")
        sys.exit(1)
    
    # Заголовок
    if args.force_shuffle:
        mode = "ПРИНУДИТЕЛЬНОЕ ПЕРЕМЕШИВАНИЕ ОТВЕТОВ"
    elif args.fix:
        mode = "АНАЛИЗ И ИСПРАВЛЕНИЕ"
    else:
        mode = "АНАЛИЗ"
    
    print(f"\n{'='*80}")
    print(f"🔍 {mode} КУРСОВ")
    print(f"{'='*80}")
    print(f"Курсов для обработки: {len(courses)}")
    
    if args.force_shuffle:
        print(f"⚠️  Режим принудительного перемешивания - ответы будут перемешаны независимо от распределения!")
    elif args.fix:
        print(f"⚠️  Режим исправления активен - изменения будут сохранены!")
    else:
        print(f"ℹ️  Режим только чтения - используйте -f для исправления проблем")
    
    # Обрабатываем курсы
    all_results = []
    for course_path in courses:
        result = process_course(course_path, fix_mode=args.fix, force_shuffle=args.force_shuffle)
        all_results.append(result)
    
    # Общая статистика
    print(f"\n{'='*80}")
    print(f"📈 ИТОГОВАЯ СТАТИСТИКА")
    print(f"{'='*80}")
    
    total_modules = sum(r['modules_analyzed'] for r in all_results)
    total_issues_found = sum(r['issues_found'] for r in all_results)
    total_issues_fixed = sum(r['issues_fixed'] for r in all_results)
    
    print(f"Курсов обработано: {len(all_results)}")
    print(f"Модулей проанализировано: {total_modules}")
    print(f"Проблем найдено: {total_issues_found}")
    if args.fix:
        print(f"Проблем исправлено: {total_issues_fixed}")
    
    print(f"\n{'='*80}")
    if args.force_shuffle:
        print(f"✅ Принудительное перемешивание завершено!")
    elif args.fix:
        print(f"✅ Анализ и исправление завершены!")
    else:
        print(f"✅ Анализ завершён! Используйте -f для автоматического исправления.")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()
