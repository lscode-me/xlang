#!/usr/bin/env python3
"""
Анализатор качества курсов согласно стандартам CourseBuilder.

Метрики из course_write_meta/:
- Длина лекции: 600-1000 строк
- Основных секций (H2): 5-12
- Блоков кода: 15-30
- Learning Objectives: 3-5
- Key Takeaways: 3-5
- Вопросов в quiz.md: 20-40
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


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
    quiz_answer_key_format_valid: bool = False  # Соответствует ли формат шаблону
    quiz_answer_key_answers_count: int = 0  # Количество ответов в Answer Key
    quiz_questions_without_answers: list[int] = field(default_factory=list)  # Номера вопросов без ответов
    quiz_questions_with_duplicate_options: list[int] = field(default_factory=list)  # Номера вопросов с дубликатами вариантов


@dataclass
class ReadmeMetrics:
    """Метрики README курса."""
    course: str
    
    # Basic checks
    exists: bool = False
    lines: int = 0
    
    # Required sections
    has_title: bool = False
    has_description: bool = False
    has_goals: bool = False
    has_requirements: bool = False
    has_structure: bool = False
    
    # Structure section details
    modules_with_links: int = 0
    modules_with_topics: int = 0
    modules_with_examples: int = 0
    
    # Quality metrics
    goals_count: int = 0
    requirements_count: int = 0
    
    def quality_status(self) -> str:
        """Статус качества README."""
        if not self.exists:
            return "❌ README отсутствует"
        
        issues = 0
        
        # Критические проблемы
        if self.lines < 100:
            issues += 3
        if not self.has_description:
            issues += 2
        if not self.has_structure:
            issues += 2
        if self.modules_with_links < 15:
            issues += 2
        
        # Средние проблемы
        if self.lines < 200:
            issues += 1
        if not self.has_goals or self.goals_count < 3:
            issues += 1
        if not self.has_requirements:
            issues += 1
        if self.modules_with_examples < 15:
            issues += 1
        if self.modules_with_topics < 15:
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
    quiz_answer_key_format_valid: bool = False  # Соответствует ли формат шаблону
    quiz_answer_key_answers_count: int = 0  # Количество ответов в Answer Key
    quiz_questions_without_answers: list[int] = field(default_factory=list)  # Номера вопросов без ответов
    quiz_questions_with_duplicate_options: list[int] = field(default_factory=list)  # Номера вопросов с дубликатами вариантов
    
    def lecture_status(self) -> str:
        """Статус длины лекции."""
        if self.lecture_lines < 400:
            return "❌ Очень короткая"
        elif self.lecture_lines < 600:
            return "⚠️ Короткая"
        elif self.lecture_lines <= 1000:
            return "✅ Норма"
        elif self.lecture_lines <= 1200:
            return "⚠️ Длинная"
        else:
            return "❌ Очень длинная"
    
    def sections_status(self) -> str:
        """Статус количества секций."""
        if self.h2_sections < 5:
            return "⚠️ Мало"
        elif self.h2_sections <= 12:
            return "✅ Норма"
        else:
            return "⚠️ Много"
    
    def code_blocks_status(self) -> str:
        """Статус количества блоков кода."""
        if self.code_blocks < 10:
            return "⚠️ Мало"
        elif self.code_blocks < 15:
            return "⚠️ Ниже нормы"
        elif self.code_blocks <= 30:
            return "✅ Норма"
        else:
            return "⚠️ Много"
    
    def quiz_status(self) -> str:
        """Статус квиза."""
        if not self.has_quiz:
            return "❌ Нет"
        elif self.quiz_questions < 15:
            return "⚠️ Мало вопросов"
        elif self.quiz_questions < 20:
            return "⚠️ Ниже нормы"
        elif self.quiz_questions <= 40:
            return "✅ Норма"
        else:
            return "⚠️ Много вопросов"
    
    def structure_score(self) -> int:
        """Баллы за структуру (0-5)."""
        score = 0
        if self.has_prerequisites:
            score += 1
        if self.has_learning_objectives:
            score += 1
        if self.has_key_takeaways:
            score += 1
        if self.has_next_steps:
            score += 1
        if self.has_quiz:
            score += 1
        return score
    
    def overall_quality(self) -> str:
        issues = 0
        
        # Критические проблемы с квизом
        if not self.has_quiz:
            # Нет квиза - критическая проблема
            issues += 3
        else:
            # САМЫЙ ВЫСОКИЙ ПРИОРИТЕТ: Проверка отсутствия ответов для всех вопросов
            if self.quiz_questions_without_answers:
                # Есть вопросы без правильных ответов - критическая проблема
                # Каждый вопрос без ответа добавляет серьезный штраф
                issues += 5 + len(self.quiz_questions_without_answers)
            
            # Проверка дубликатов вариантов ответа
            if self.quiz_questions_with_duplicate_options:
                # Есть вопросы с дубликатами вариантов - серьезная проблема
                issues += 2 + len(self.quiz_questions_with_duplicate_options)
            
            # Квиз есть, проверяем его полноту
            if self.quiz_questions < 15:
                # Слишком мало вопросов - критическая проблема
                issues += 3
            elif self.quiz_questions < 20:
                # Меньше рекомендуемого минимума
                issues += 1
            
            # Проверяем наличие обязательных компонентов независимо
            if not self.quiz_has_answer_key:
                # Нет ключа ответов - критическая проблема (нельзя использовать квиз)
                issues += 3
            elif not self.quiz_answer_key_format_valid:
                # Неправильный формат Answer Key - критическая проблема (не работает shuffle)
                issues += 3
            elif self.quiz_answer_key_answers_count != self.quiz_questions:
                # Количество ответов не совпадает с количеством вопросов
                # Но только если мы еще не учли это в quiz_questions_without_answers
                if not self.quiz_questions_without_answers:
                    issues += 2
            
            if not self.quiz_has_scoring:
                # Нет шкалы оценки - серьезная проблема
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
        
        # Нельзя получить "Отлично" без полного квиза
        # Проверяем, что квиз полностью готов (20+ вопросов, Answer Key с правильным форматом, Scoring Guide)
        has_full_quiz = (self.has_quiz and 
                        self.quiz_questions >= 20 and 
                        self.quiz_has_answer_key and 
                        self.quiz_answer_key_format_valid and
                        self.quiz_answer_key_answers_count == self.quiz_questions and
                        self.quiz_has_scoring)
        
        if issues == 0:
            if not has_full_quiz:
                issues += 1  # Недостаточно для "Отлично"
        
        if issues == 0:
            return "✅ Отлично"
        elif issues <= 2:
            return "✅ Хорошо"
        elif issues <= 4:
            return "⚠️ Требует улучшений"
        else:
            return "❌ Серьёзные проблемы"


def analyze_lecture(filepath: Path) -> dict:
    """Анализ lecture.md файла."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Подсчет блоков кода
    code_blocks = len(re.findall(r'^```', content, re.MULTILINE))
    code_blocks = code_blocks // 2  # Открывающие и закрывающие
    
    # Подсчет H2 секций (основных нумерованных секций)
    h2_sections = len(re.findall(r'^## \d+\.', content, re.MULTILINE))
    
    # Learning Objectives - считаем пункты после секции
    lo_match = re.search(
        r'## 🎯 Learning Objectives.*?\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    learning_objectives = 0
    if lo_match:
        lo_text = lo_match.group(1)
        learning_objectives = len(re.findall(r'^[-*•]\s', lo_text, re.MULTILINE))
    
    # Key Takeaways - считаем пункты
    kt_match = re.search(
        r'## 💡 Key Takeaways.*?\n(.*?)(?=\n## |\n---|\Z)',
        content, re.DOTALL | re.IGNORECASE
    )
    key_takeaways = 0
    if kt_match:
        kt_text = kt_match.group(1)
        key_takeaways = len(re.findall(r'^[-*•]\s', kt_text, re.MULTILINE))
    
    # Проверка наличия секций
    has_prerequisites = bool(re.search(r'## 📋 Prerequisites', content, re.IGNORECASE))
    has_learning_objectives = bool(re.search(r'## 🎯 Learning Objectives', content, re.IGNORECASE))
    has_key_takeaways = bool(re.search(r'## 💡 Key Takeaways', content, re.IGNORECASE))
    has_next_steps = bool(re.search(r'## 🚀 Next Steps', content, re.IGNORECASE))
    
    return {
        'lecture_lines': len(lines),
        'code_blocks': code_blocks,
        'h2_sections': h2_sections,
        'learning_objectives': learning_objectives,
        'key_takeaways': key_takeaways,
        'has_prerequisites': has_prerequisites,
        'has_learning_objectives': has_learning_objectives,
        'has_key_takeaways': has_key_takeaways,
        'has_next_steps': has_next_steps,
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
    
    # Проверяем размер файла - пустые файлы не считаются квизами
    file_size = filepath.stat().st_size
    if file_size < 100:  # Меньше 100 байт - скорее всего пустой файл
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
    
    # Подсчет вопросов - ищем "## Question N" или "**Question N"
    questions = len(re.findall(r'##\s*Question\s+\d+', content, re.IGNORECASE))
    if questions == 0:
        # Альтернативный формат
        questions = len(re.findall(r'\*\*Question\s+\d+', content, re.IGNORECASE))
    if questions == 0:
        # Еще один формат: просто нумерованные вопросы
        questions = len(re.findall(r'^##\s*\d+\.', content, re.MULTILINE))
    
    # Проверка наличия Answer Key - ищем более точные паттерны
    has_answer_key = bool(re.search(
        r'##\s*Answer\s+Key|##\s*Ответы|Answer\s+Key|Ключ\s+ответов',
        content, re.IGNORECASE
    ))
    
    # Проверка наличия Scoring Guide - ищем более точные паттерны
    has_scoring = bool(re.search(
        r'##\s*Scoring\s+Guide|##\s*Шкала\s+оценки|Scoring\s+Guide|Шкала\s+оценки',
        content, re.IGNORECASE
    ))
    
    # Проверка формата Answer Key
    answer_key_format_valid = False
    answer_key_answers_count = 0
    questions_without_answers = []
    
    # Собираем номера всех вопросов
    question_numbers = set()
    question_matches = re.findall(r'##\s*Question\s+(\d+)', content, re.IGNORECASE)
    if not question_matches:
        # Альтернативный формат
        question_matches = re.findall(r'\*\*Question\s+(\d+)', content, re.IGNORECASE)
    if not question_matches:
        # Еще один формат: просто нумерованные вопросы
        question_matches = re.findall(r'^##\s*(\d+)\.', content, re.MULTILINE)
    
    for match in question_matches:
        question_numbers.add(int(match))
    
    if has_answer_key:
        # Ищем секцию Answer Key
        answer_key_match = re.search(
            r'##\s*Answer\s+Key.*?(?=\n##|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        
        if answer_key_match:
            answer_key_section = answer_key_match.group(0)
            answered_question_numbers = set()
            
            # Проверяем формат 1: Таблица | # | Answer | Explanation |
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
                # Проверяем формат 2: Список 1. **B** - explanation
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
                    # Проверяем неправильный формат: 1. B) answer
                    wrong_format = re.findall(
                        r'^(\d+)\.\s*([A-D])\)\s*.+',
                        answer_key_section, re.MULTILINE
                    )
                    if wrong_format:
                        # Это неправильный формат - не соответствует шаблону
                        answer_key_format_valid = False
                        answer_key_answers_count = len(wrong_format)
                        for num_str, _ in wrong_format:
                            answered_question_numbers.add(int(num_str))
            
            # Определяем вопросы без ответов
            if question_numbers:
                questions_without_answers = sorted(question_numbers - answered_question_numbers)
    else:
        # Если Answer Key отсутствует, все вопросы без ответов
        if question_numbers:
            questions_without_answers = sorted(question_numbers)
    
    # Проверка на дубликаты вариантов ответа в вопросах
    questions_with_duplicates = []
    
    if questions > 0:
        # Определяем, какой паттерн использовался для поиска вопросов
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
                
                # Извлекаем все варианты ответа (A), B), C), D))
                # Паттерн ищет строки, начинающиеся с буквы A-D, затем ), затем пробелы и текст до конца строки
                options = re.findall(r'^([A-D])\)\s*(.+?)$', question_text, re.MULTILINE)
                
                if options:
                    # Проверяем на дубликаты по тексту варианта (без учета регистра и пробелов)
                    option_texts = []
                    for letter, text in options:
                        # Нормализуем текст: убираем лишние пробелы, приводим к нижнему регистру
                        normalized = ' '.join(text.strip().split()).lower()
                        option_texts.append((letter, normalized))
                    
                    # Проверяем на дубликаты
                    seen_texts = set()
                    has_duplicate = False
                    for letter, text in option_texts:
                        if text in seen_texts:
                            has_duplicate = True
                            break
                        seen_texts.add(text)
                    
                    if has_duplicate:
                        questions_with_duplicates.append(question_num)
    
    # Если вопросов нет, то это не квиз
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


def analyze_readme(course_path: Path, course_name: str) -> ReadmeMetrics:
    """Анализ README.md курса."""
    readme_path = course_path / course_name / 'README.md'
    
    metrics = ReadmeMetrics(course=course_name)
    
    if not readme_path.exists():
        return metrics
    
    metrics.exists = True
    
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    metrics.lines = len(lines)
    
    # Проверка заголовка H1
    metrics.has_title = bool(re.search(r'^# .+', content, re.MULTILINE))
    
    # Проверка секций
    metrics.has_description = bool(re.search(r'## Описание курса', content, re.IGNORECASE))
    metrics.has_goals = bool(re.search(r'## Цели курса', content, re.IGNORECASE))
    metrics.has_requirements = bool(re.search(r'## Требования', content, re.IGNORECASE))
    metrics.has_structure = bool(re.search(r'## Структура курса', content, re.IGNORECASE))
    
    # Подсчет целей (список после "Цели курса")
    if metrics.has_goals:
        goals_match = re.search(
            r'## Цели курса.*?\n(.*?)(?=\n## |\n---|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        if goals_match:
            goals_text = goals_match.group(1)
            metrics.goals_count = len(re.findall(r'^[-*•]\s', goals_text, re.MULTILINE))
    
    # Подсчет требований
    if metrics.has_requirements:
        req_match = re.search(
            r'## Требования.*?\n(.*?)(?=\n## |\n---|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        if req_match:
            req_text = req_match.group(1)
            metrics.requirements_count = len(re.findall(r'^[-*•]\s', req_text, re.MULTILINE))
    
    # Анализ структуры курса
    if metrics.has_structure:
        struct_match = re.search(
            r'## Структура курса.*?(?=\n## [^#]|\Z)',
            content, re.DOTALL | re.IGNORECASE
        )
        if struct_match:
            struct_text = struct_match.group(0)
            
            # Модули со ссылками: ### [01. Name](folder/)
            modules_with_links = re.findall(
                r'###\s*\[.+?\]\(.+?\)',
                struct_text
            )
            metrics.modules_with_links = len(modules_with_links)
            
            # Разбиваем на блоки модулей по разделителю ---
            module_blocks = re.split(r'\n---\n', struct_text)
            
            for block in module_blocks:
                # Проверяем наличие ссылки на модуль
                if not re.search(r'###\s*\[', block):
                    continue
                
                # Проверяем наличие маркированного списка тем
                topics = re.findall(r'^[-*•]\s', block, re.MULTILINE)
                if topics:
                    metrics.modules_with_topics += 1
                
                # Проверяем наличие подзаголовка "Примеры:" и самих примеров
                if re.search(r'\*\*Примеры:\*\*', block, re.IGNORECASE):
                    # Ищем примеры после "Примеры:"
                    examples_match = re.search(
                        r'\*\*Примеры:\*\*(.*?)(?=\n---|\n###|\Z)',
                        block, re.DOTALL | re.IGNORECASE
                    )
                    if examples_match:
                        examples_text = examples_match.group(1)
                        # Проверяем, что есть хотя бы один пример (строка с содержанием)
                        example_lines = [line.strip() for line in examples_text.split('\n') if line.strip() and not line.strip().startswith('#')]
                        if example_lines:
                            metrics.modules_with_examples += 1
    
    return metrics


def analyze_module(course_path: Path, module_name: str, course_name: str) -> Optional[ModuleMetrics]:
    """Анализ одного модуля."""
    module_path = course_path / module_name
    lecture_path = module_path / 'lecture.md'
    quiz_path = module_path / 'quiz.md'
    
    if not lecture_path.exists():
        return None
    
    metrics = ModuleMetrics(course=course_name, module=module_name)
    
    # Анализ лекции
    lecture_data = analyze_lecture(lecture_path)
    metrics.lecture_lines = lecture_data['lecture_lines']
    metrics.code_blocks = lecture_data['code_blocks']
    metrics.h2_sections = lecture_data['h2_sections']
    metrics.learning_objectives = lecture_data['learning_objectives']
    metrics.key_takeaways = lecture_data['key_takeaways']
    metrics.has_prerequisites = lecture_data['has_prerequisites']
    metrics.has_learning_objectives = lecture_data['has_learning_objectives']
    metrics.has_key_takeaways = lecture_data['has_key_takeaways']
    metrics.has_next_steps = lecture_data['has_next_steps']
    
    # Анализ квиза
    quiz_data = analyze_quiz(quiz_path)
    metrics.has_quiz = quiz_data['has_quiz']
    metrics.quiz_questions = quiz_data['quiz_questions']
    metrics.quiz_has_answer_key = quiz_data['quiz_has_answer_key']
    metrics.quiz_has_scoring = quiz_data['quiz_has_scoring']
    metrics.quiz_answer_key_format_valid = quiz_data['quiz_answer_key_format_valid']
    metrics.quiz_answer_key_answers_count = quiz_data['quiz_answer_key_answers_count']
    metrics.quiz_questions_without_answers = quiz_data.get('quiz_questions_without_answers', [])
    metrics.quiz_questions_with_duplicate_options = quiz_data.get('quiz_questions_with_duplicate_options', [])
    
    return metrics


def analyze_course(courses_path: Path, course_name: str) -> list[ModuleMetrics]:
    """Анализ всего курса."""
    course_path = courses_path / course_name
    metrics = []
    
    if not course_path.exists():
        return metrics
    
    for item in sorted(course_path.iterdir()):
        if item.is_dir() and item.name.startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')):
            module_metrics = analyze_module(course_path, item.name, course_name)
            if module_metrics:
                metrics.append(module_metrics)
    
    return metrics


def print_course_report(course_name: str, modules: list[ModuleMetrics], readme_metrics: Optional[ReadmeMetrics] = None):
    """Вывод отчета по курсу."""
    if not modules:
        print(f"\n{'='*80}")
        print(f"📚 {course_name}: нет модулей")
        return
    
    print(f"\n{'='*80}")
    print(f"📚 {course_name} ({len(modules)} модулей)")
    print(f"{'='*80}")
    
    # README метрики (в начале отчета)
    if readme_metrics:
        print(f"\n📖 README:")
        if readme_metrics.exists:
            print(f"   Статус: {readme_metrics.quality_status()}")
            print(f"   Строк: {readme_metrics.lines}", end="")
            if readme_metrics.lines < 200:
                print(" ⚠️")
            else:
                print(" ✅")
            
            # Секции
            sections_ok = (readme_metrics.has_title and readme_metrics.has_description and 
                          readme_metrics.has_goals and readme_metrics.has_requirements and 
                          readme_metrics.has_structure)
            print(f"   Обязательные секции: {'✅' if sections_ok else '⚠️'}", end="")
            if not sections_ok:
                missing = []
                if not readme_metrics.has_title:
                    missing.append("заголовок")
                if not readme_metrics.has_description:
                    missing.append("описание")
                if not readme_metrics.has_goals:
                    missing.append("цели")
                if not readme_metrics.has_requirements:
                    missing.append("требования")
                if not readme_metrics.has_structure:
                    missing.append("структура")
                print(f" (отсутствует: {', '.join(missing)})")
            else:
                print()
            
            # Детали структуры
            if readme_metrics.has_structure:
                print(f"   Модулей со ссылками: {readme_metrics.modules_with_links}/20", end="")
                if readme_metrics.modules_with_links < 20:
                    print(" ⚠️")
                else:
                    print(" ✅")
                print(f"   Модулей с описанием тем: {readme_metrics.modules_with_topics}/20", end="")
                if readme_metrics.modules_with_topics < 15:
                    print(" ⚠️")
                else:
                    print(" ✅")
                print(f"   Модулей с примерами: {readme_metrics.modules_with_examples}/20", end="")
                if readme_metrics.modules_with_examples < 15:
                    print(" ⚠️")
                else:
                    print(" ✅")
            
            # Цели и требования
            if readme_metrics.has_goals:
                print(f"   Целей курса: {readme_metrics.goals_count}", end="")
                if readme_metrics.goals_count < 3:
                    print(" ⚠️")
                else:
                    print(" ✅")
        else:
            print(f"   Статус: ❌ README.md отсутствует")
    
    # Сводка по курсу
    total_lines = sum(m.lecture_lines for m in modules)
    avg_lines = total_lines // len(modules)
    total_code_blocks = sum(m.code_blocks for m in modules)
    total_quiz_questions = sum(m.quiz_questions for m in modules)
    modules_with_quiz = sum(1 for m in modules if m.has_quiz)
    
    print(f"\n📊 СВОДКА ПО КУРСУ:")
    print(f"   Всего модулей: {len(modules)}")
    print(f"   Средняя длина лекции: {avg_lines} строк", end="")
    if avg_lines < 600:
        print(" ⚠️")
    elif avg_lines > 1000:
        print(" ⚠️")
    else:
        print(" ✅")
    print(f"   Всего блоков кода: {total_code_blocks}")
    print(f"   Модулей с квизом: {modules_with_quiz}/{len(modules)}", end="")
    if modules_with_quiz < len(modules):
        print(" ⚠️")
    else:
        print(" ✅")
    print(f"   Всего вопросов в квизах: {total_quiz_questions}")
    
    # Проверка полноты квизов
    modules_with_full_quiz = sum(1 for m in modules if m.has_quiz and m.quiz_questions >= 20 and m.quiz_has_answer_key and m.quiz_has_scoring)
    if modules_with_full_quiz < len(modules):
        print(f"   Модулей с полным квизом (20+ вопросов, Answer Key, Scoring): {modules_with_full_quiz}/{len(modules)} ⚠️")
    
    # Проверка формата Answer Key
    modules_with_valid_format = sum(1 for m in modules if m.has_quiz and m.quiz_has_answer_key and m.quiz_answer_key_format_valid)
    modules_with_wrong_format = sum(1 for m in modules if m.has_quiz and m.quiz_has_answer_key and not m.quiz_answer_key_format_valid)
    if modules_with_wrong_format > 0:
        print(f"   Модулей с правильным форматом Answer Key: {modules_with_valid_format}/{modules_with_quiz} ⚠️")
        print(f"   Модулей с неправильным форматом Answer Key: {modules_with_wrong_format} ⚠️")
    
    # Проверка соответствия количества ответов количеству вопросов
    modules_with_matching_counts = sum(1 for m in modules if m.has_quiz and m.quiz_has_answer_key and m.quiz_answer_key_answers_count == m.quiz_questions)
    modules_with_mismatched_counts = sum(1 for m in modules if m.has_quiz and m.quiz_has_answer_key and m.quiz_answer_key_answers_count != m.quiz_questions)
    if modules_with_mismatched_counts > 0:
        print(f"   Модулей с совпадающим количеством ответов: {modules_with_matching_counts}/{modules_with_quiz} ⚠️")
        print(f"   Модулей с несовпадающим количеством ответов: {modules_with_mismatched_counts} ⚠️")
    
    # Проверка вопросов без ответов (критическая проблема)
    modules_with_missing_answers = sum(1 for m in modules if m.has_quiz and m.quiz_questions_without_answers)
    if modules_with_missing_answers > 0:
        print(f"\n   ❌ КРИТИЧЕСКАЯ ПРОБЛЕМА: Модулей с вопросами без ответов: {modules_with_missing_answers}/{modules_with_quiz}")
        for m in modules:
            if m.has_quiz and m.quiz_questions_without_answers:
                print(f"      - {m.module}: вопросы {', '.join(map(str, m.quiz_questions_without_answers))} без ответов")
    
    # Проверка дубликатов вариантов ответа
    modules_with_duplicates = sum(1 for m in modules if m.has_quiz and m.quiz_questions_with_duplicate_options)
    if modules_with_duplicates > 0:
        print(f"\n   ⚠️ ПРОБЛЕМА: Модулей с дубликатами вариантов ответа: {modules_with_duplicates}/{modules_with_quiz}")
        for m in modules:
            if m.has_quiz and m.quiz_questions_with_duplicate_options:
                print(f"      - {m.module}: вопросы {', '.join(map(str, m.quiz_questions_with_duplicate_options))} с дубликатами")
    
    # Структура
    with_prereq = sum(1 for m in modules if m.has_prerequisites)
    with_lo = sum(1 for m in modules if m.has_learning_objectives)
    with_kt = sum(1 for m in modules if m.has_key_takeaways)
    with_ns = sum(1 for m in modules if m.has_next_steps)
    
    print(f"\n📋 СТРУКТУРА:")
    print(f"   Prerequisites: {with_prereq}/{len(modules)}", "✅" if with_prereq == len(modules) else "⚠️")
    print(f"   Learning Objectives: {with_lo}/{len(modules)}", "✅" if with_lo == len(modules) else "⚠️")
    print(f"   Key Takeaways: {with_kt}/{len(modules)}", "✅" if with_kt == len(modules) else "⚠️")
    print(f"   Next Steps: {with_ns}/{len(modules)}", "✅" if with_ns == len(modules) else "⚠️")
    
    # Качество
    excellent = sum(1 for m in modules if "Отлично" in m.overall_quality())
    good = sum(1 for m in modules if "Хорошо" in m.overall_quality())
    needs_work = sum(1 for m in modules if "Требует" in m.overall_quality())
    serious = sum(1 for m in modules if "Серьёзные" in m.overall_quality())
    
    print(f"\n🎯 КАЧЕСТВО:")
    print(f"   ✅ Отлично: {excellent}")
    print(f"   ✅ Хорошо: {good}")
    print(f"   ⚠️ Требует улучшений: {needs_work}")
    print(f"   ❌ Серьёзные проблемы: {serious}")
    
    # Детальная таблица
    print(f"\n📝 ДЕТАЛИ ПО МОДУЛЯМ:")
    print("-" * 100)
    print(f"{'Модуль':<25} {'Строк':>7} {'H2':>4} {'Код':>5} {'LO':>4} {'KT':>4} {'Quiz':>6} {'Качество':<20}")
    print("-" * 100)
    
    for m in modules:
        if m.has_quiz and m.quiz_questions >= 20 and m.quiz_has_answer_key and m.quiz_answer_key_format_valid and m.quiz_answer_key_answers_count == m.quiz_questions and m.quiz_has_scoring and not m.quiz_questions_without_answers and not m.quiz_questions_with_duplicate_options:
            quiz_info = f"{m.quiz_questions}✅"
        elif m.has_quiz:
            # Квиз есть, но неполный
            missing = []
            if m.quiz_questions_without_answers:
                missing.append(f"нет ответов: {', '.join(map(str, m.quiz_questions_without_answers))}")
            if m.quiz_questions_with_duplicate_options:
                missing.append(f"дубликаты: {', '.join(map(str, m.quiz_questions_with_duplicate_options))}")
            if m.quiz_questions < 20:
                missing.append(f"<20")
            if not m.quiz_has_answer_key:
                missing.append("нет Key")
            elif not m.quiz_answer_key_format_valid:
                missing.append("неверный формат")
            elif m.quiz_answer_key_answers_count != m.quiz_questions:
                missing.append(f"несовпадение ({m.quiz_answer_key_answers_count}/{m.quiz_questions})")
            if not m.quiz_has_scoring:
                missing.append("нет Scoring")
            quiz_info = f"{m.quiz_questions}⚠️"
        else:
            quiz_info = "—"
        print(f"{m.module:<25} {m.lecture_lines:>7} {m.h2_sections:>4} {m.code_blocks:>5} {m.learning_objectives:>4} {m.key_takeaways:>4} {quiz_info:>6} {m.overall_quality():<20}")
    
    print("-" * 100)


def print_summary(all_metrics: dict[str, list[ModuleMetrics]]):
    """Общая сводка по всем курсам."""
    print("\n" + "=" * 80)
    print("📈 ОБЩАЯ СВОДКА ПО ВСЕМ КУРСАМ")
    print("=" * 80)
    
    total_modules = 0
    total_excellent = 0
    total_good = 0
    total_needs_work = 0
    total_serious = 0
    total_no_quiz = 0
    
    print(f"\n{'Курс':<25} {'Модулей':>8} {'Отлично':>8} {'Хорошо':>8} {'⚠️ Улучш':>8} {'❌ Пробл':>8} {'Без quiz':>8}")
    print("-" * 90)
    
    for course_name, modules in sorted(all_metrics.items()):
        if not modules:
            continue
            
        total_modules += len(modules)
        
        excellent = sum(1 for m in modules if "Отлично" in m.overall_quality())
        good = sum(1 for m in modules if "Хорошо" in m.overall_quality())
        needs_work = sum(1 for m in modules if "Требует" in m.overall_quality())
        serious = sum(1 for m in modules if "Серьёзные" in m.overall_quality())
        no_quiz = sum(1 for m in modules if not m.has_quiz)
        
        total_excellent += excellent
        total_good += good
        total_needs_work += needs_work
        total_serious += serious
        total_no_quiz += no_quiz
        
        print(f"{course_name:<25} {len(modules):>8} {excellent:>8} {good:>8} {needs_work:>8} {serious:>8} {no_quiz:>8}")
    
    print("-" * 90)
    print(f"{'ИТОГО':<25} {total_modules:>8} {total_excellent:>8} {total_good:>8} {total_needs_work:>8} {total_serious:>8} {total_no_quiz:>8}")
    
    print("\n📊 ПРОЦЕНТНОЕ РАСПРЕДЕЛЕНИЕ:")
    if total_modules > 0:
        print(f"   ✅ Отлично: {total_excellent/total_modules*100:.1f}%")
        print(f"   ✅ Хорошо: {total_good/total_modules*100:.1f}%")
        print(f"   ⚠️ Требует улучшений: {total_needs_work/total_modules*100:.1f}%")
        print(f"   ❌ Серьёзные проблемы: {total_serious/total_modules*100:.1f}%")
        if total_no_quiz > 0:
            print(f"\n   ⚠️ Модулей без quiz.md: {total_no_quiz} ({total_no_quiz/total_modules*100:.1f}%)")


def main():
    """Главная функция."""
    import argparse
    import sys

    script_dir = Path(__file__).parent
    workspace = script_dir.parent
    default_courses_path = workspace / 'Courses'

    parser = argparse.ArgumentParser(
        description='Анализ качества курсов (лекции, квизы, структура) согласно стандартам CourseBuilder'
    )
    parser.add_argument(
        'path',
        nargs='?',
        help='Путь к курсу или директории с курсами (по умолчанию: Courses/)'
    )
    args = parser.parse_args()

    # Определяем базовую директорию с курсами и список курсов для анализа
    if args.path:
        target = Path(args.path)
        if not target.is_absolute():
            target = workspace / args.path
        if not target.exists():
            print(f"❌ Путь не найден: {target}")
            sys.exit(1)

        # Если явно передана папка Courses/ или её абсолютный путь
        if target == default_courses_path or target.name == 'Courses':
            courses_path = target
            courses = [d.name for d in sorted(courses_path.iterdir()) if d.is_dir()]
        # Если это один курс (есть README.md)
        elif (target / 'README.md').exists():
            courses_path = target.parent
            courses = [target.name]
        # Если это директория, внутри которой лежат несколько курсов
        elif target.is_dir():
            courses_path = target
            courses = [
                d.name
                for d in sorted(courses_path.iterdir())
                if d.is_dir() and (d / 'README.md').exists()
            ]
            if not courses:
                print(f"❌ В директории {target} не найдено ни одного курса (папка с README.md)")
                sys.exit(1)
        else:
            print(f"❌ Ожидалась директория курса или директория с курсами, получено: {target}")
            sys.exit(1)
    else:
        # Старое поведение по умолчанию: все директории в Courses/
        courses_path = default_courses_path
        if not courses_path.exists():
            print(f"Папка {courses_path} не найдена!")
            sys.exit(1)
        courses = [d.name for d in sorted(courses_path.iterdir()) if d.is_dir()]

    if not courses:
        print("❌ Не найдено курсов для анализа")
        sys.exit(1)

    all_metrics: dict[str, list[ModuleMetrics]] = {}

    # Анализируем каждый курс
    for course_name in courses:
        modules = analyze_course(courses_path, course_name)
        all_metrics[course_name] = modules
        readme_metrics = analyze_readme(courses_path, course_name)
        print_course_report(course_name, modules, readme_metrics)
    
    # Общая сводка (по только что проанализированным курсам)
    print_summary(all_metrics)
    
    # Легенда
    print("\n" + "=" * 80)
    print("📖 ЛЕГЕНДА (целевые метрики согласно стандарту):")
    print("=" * 80)
    print("   Длина лекции (строк): 600-1000 (оптимум: 700-900)")
    print("   Основных секций (H2): 5-12 (оптимум: 7-10)")
    print("   Блоков кода: 15-30 (оптимум: 20-25)")
    print("   Learning Objectives: 3-5")
    print("   Key Takeaways: 3-5")
    print("   Вопросов в quiz.md: 20-40 (оптимум: 25-30)")
    print("\n   README.md курса:")
    print("   - Минимум 200 строк")
    print("   - Все 20 модулей со ссылками, описанием тем и примерами")
    print("   - Обязательные секции: Описание, Цели (5+), Требования, Структура")
    print("   - Подробности: course_write_meta/README_STANDARD.md")


if __name__ == '__main__':
    main()

