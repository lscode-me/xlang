#!/usr/bin/env python3
"""
Генератор HTML страниц для курсов CourseBuilder.
Читает lecture.md и quiz.md файлы и создаёт интерактивные HTML страницы.

Структура вывода:
  html/
    index.html              - главная страница со списком курсов
    <Course>/
      index.html            - страница курса со списком лекций
      <Module>.html         - страница лекции с тестом
"""

import html
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import markdown

# Импортируем названия курсов из отдельного файла
sys.path.insert(0, str(Path(__file__).parent.parent))
from Courses.course_names import COURSE_NAMES


class CourseHTMLGenerator:
    """Генератор HTML страниц для курсов"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.courses_dir = self.base_dir / "Courses"
        self.html_dir = self.base_dir / "html"
        # Очищаем директорию перед генерацией
        if self.html_dir.exists():
            import shutil
            shutil.rmtree(self.html_dir)
        self.html_dir.mkdir(exist_ok=True)
        
    def find_all_courses(self) -> List[Dict[str, Path]]:
        """Находит все курсы с lecture.md и quiz.md"""
        courses = []
        
        # Проверяем наличие директории Courses
        if not self.courses_dir.exists():
            print(f"⚠️  Директория {self.courses_dir} не найдена")
            return courses
        
        # Автоматически находим все директории с курсами в Courses/
        for category_path in sorted(self.courses_dir.iterdir()):
            if not category_path.is_dir():
                continue
            # Проверяем, есть ли внутри директории с номерами (01_..., 02_..., etc)
            has_modules = any(
                d.is_dir() and re.match(r'^\d{2}_', d.name) 
                for d in category_path.iterdir()
            )
            if not has_modules:
                continue
                
            for module_dir in sorted(category_path.iterdir()):
                if not module_dir.is_dir():
                    continue
                if not re.match(r'^\d{2}_', module_dir.name):
                    continue
                    
                lecture_path = module_dir / "lecture.md"
                quiz_path = module_dir / "quiz.md"
                
                if lecture_path.exists() and quiz_path.exists():
                    courses.append({
                        "category": category_path.name,
                        "module_name": module_dir.name,
                        "lecture_path": lecture_path,
                        "quiz_path": quiz_path,
                        "module_dir": module_dir
                    })
        
        return courses
    
    def parse_lecture(self, lecture_path: Path, category: str) -> Dict[str, str]:
        """Парсит lecture.md и возвращает заголовок и HTML контент"""
        with open(lecture_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Извлекаем заголовок (первая строка с #)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else "Лекция"
        
        # Заменяем относительные ссылки на HTML файлы
        # Формат: [Text](../02_Module/) -> [Text](02_Module.html)
        def replace_link(match):
            module_name = match.group(1).rstrip('/')
            return f']({module_name}.html)'
        
        content = re.sub(r'\]\(\.\./(\d{2}_[^/)]+)/?\)', replace_link, content)
        
        # Конвертируем markdown в HTML
        # Настраиваем codehilite для совместимости с highlight.js
        md = markdown.Markdown(extensions=[
            'extra', 
            'codehilite',
            'tables', 
            'fenced_code'
        ], extension_configs={
            'codehilite': {
                'css_class': 'hljs',
                'use_pygments': False,
                'noclasses': False,
            }
        })
        html_content = md.convert(content)
        
        # Post-processing: преобразуем классы codehilite в классы для highlight.js
        # codehilite генерирует <pre class="codehilite"><code class="language-xxx">
        # highlight.js ожидает <pre><code class="language-xxx hljs">
        html_content = re.sub(
            r'<pre class="codehilite"><code class="language-(\w+)"',
            r'<pre><code class="language-\1 hljs"',
            html_content
        )
        # Для блоков без указания языка
        html_content = re.sub(
            r'<pre class="codehilite"><code>',
            r'<pre><code class="hljs">',
            html_content
        )
        # Для блоков с классом codehilite но без language
        html_content = re.sub(
            r'<pre class="codehilite"><code class="hljs"',
            r'<pre><code class="hljs"',
            html_content
        )
        
        return {
            "title": title,
            "html": html_content
        }
    
    def _md_to_html(self, text: str) -> str:
        """Конвертирует markdown текст в HTML"""
        if not text:
            return ""
        md = markdown.Markdown(extensions=[
            'extra', 
            'codehilite',
            'tables', 
            'fenced_code'
        ], extension_configs={
            'codehilite': {
                'css_class': 'hljs',
                'use_pygments': False,
                'noclasses': False,
            }
        })
        html_content = md.convert(text)
        
        # Post-processing: преобразуем классы codehilite в классы для highlight.js
        html_content = re.sub(
            r'<pre class="codehilite"><code class="language-(\w+)"',
            r'<pre><code class="language-\1 hljs"',
            html_content
        )
        html_content = re.sub(
            r'<pre class="codehilite"><code>',
            r'<pre><code class="hljs">',
            html_content
        )
        html_content = re.sub(
            r'<pre class="codehilite"><code class="hljs"',
            r'<pre><code class="hljs"',
            html_content
        )
        
        return html_content
    
    def _text_to_safe_html(self, text: str) -> str:
        """Конвертирует текст в безопасный HTML без markdown-интерпретации.
        
        Экранирует HTML-сущности и обрабатывает только backticks для inline кода.
        Используется для вариантов ответа, чтобы символы вроде # не становились заголовками.
        """
        if not text:
            return ""
        # Экранируем HTML
        escaped = html.escape(text)
        # Заменяем `code` на <code>code</code>
        escaped = re.sub(r'`([^`]+)`', r'<code>\1</code>', escaped)
        return f"<p>{escaped}</p>"
    
    def parse_quiz(self, quiz_path: Path) -> List[Dict]:
        """Парсит quiz.md и возвращает список вопросов с ответами"""
        with open(quiz_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        questions = []
        
        # Формат: ## Question N: или ## Вопрос N: или ### Вопрос N
        # Разделяем по секциям вопросов (поддерживаем разные форматы)
        question_sections = re.split(r'#{2,3} (?:Question|Вопрос) (\d+):?', content)
        
        # question_sections будет: [преамбула, номер1, контент1, номер2, контент2, ...]
        for i in range(1, len(question_sections) - 1, 2):
            question_num = int(question_sections[i])
            section_content = question_sections[i + 1]
            
            # Останавливаемся если дошли до Answer Key или Ключ к Ответам
            for stop_marker in ['## Answer Key', '## Ключ к Ответам', '## Ключ к ответам']:
                if stop_marker in section_content:
                    section_content = section_content.split(stop_marker)[0]
                    break
            
            # Извлекаем заголовок (до первой пустой строки)
            lines = section_content.strip().split('\n')
            title = lines[0].strip() if lines else f"Вопрос {question_num}"
            
            # Ищем текст вопроса (между заголовком и вариантами ответов)
            # Варианты начинаются с A)
            full_text = '\n'.join(lines[1:]).strip()
            
            # Отделяем текст вопроса от вариантов
            options_match = re.search(r'\n\s*A\)', full_text)
            if options_match:
                question_text = full_text[:options_match.start()].strip()
                options_text = full_text[options_match.start():].strip()
            else:
                question_text = ""
                options_text = full_text
            
            # Конвертируем текст вопроса в HTML через markdown
            # НЕ экранируем заранее - markdown/codehilite сам обработает code blocks
            question_html = self._md_to_html(question_text)
            
            # Парсим опции
            options = []
            option_pattern = r'([A-D])\)\s*(.+?)(?=\n[A-D]\)|\n---|\n\n\n|\Z)'
            option_matches = re.finditer(option_pattern, options_text, re.DOTALL)
            
            for match in option_matches:
                option_text = match.group(2).strip()
                # Конвертируем в безопасный HTML без markdown-интерпретации
                # (чтобы # не становился заголовком, < > не парсились как теги и т.д.)
                option_html = self._text_to_safe_html(option_text)
                options.append(option_html)
            
            if len(options) == 4:  # Должно быть ровно 4 варианта
                questions.append({
                    "number": question_num,
                    "title": html.escape(title),  # Экранируем заголовок для безопасного отображения
                    "text": question_html,
                    "options": options,
                    "correct": None,
                    "explanation": None
                })
        
        # Парсим Answer Key (таблица или список)
        # Ищем секцию с ответами (поддерживаем разные названия)
        answer_key_match = re.search(
            r'## (?:Answer Key|Ключ к Ответам|Ключ к ответам|Ответы)\s*\n(.+?)(?=\n## |\Z)', 
            content, re.DOTALL | re.IGNORECASE
        )
        if answer_key_match:
            answer_section = answer_key_match.group(1)
            
            # Попробуем формат таблицы: | # | Answer | Explanation |
            row_pattern = r'\|\s*(\d+)\s*\|\s*([A-D])\s*\|\s*(.+?)\s*\|'
            table_matches = list(re.finditer(row_pattern, answer_section))
            
            if table_matches:
                # Формат таблицы
                for match in table_matches:
                    q_num = int(match.group(1))
                    correct_letter = match.group(2)
                    explanation = match.group(3).strip()
                    
                    # Находим соответствующий вопрос
                    for q in questions:
                        if q["number"] == q_num:
                            q["correct"] = ord(correct_letter) - ord('A')
                            q["explanation"] = html.escape(explanation)
                            break
            else:
                # Формат списка: N. **X** - Explanation
                # Или: N. **X** — Explanation (с длинным тире)
                list_pattern = r'(\d+)\.\s*\*\*([A-D])\*\*\s*[-—]\s*(.+?)(?=\n\d+\.|\Z)'
                for match in re.finditer(list_pattern, answer_section, re.DOTALL):
                    q_num = int(match.group(1))
                    correct_letter = match.group(2)
                    explanation = match.group(3).strip()
                    # Убираем лишние переносы строк из explanation
                    explanation = re.sub(r'\n+', ' ', explanation).strip()
                    
                    # Находим соответствующий вопрос
                    for q in questions:
                        if q["number"] == q_num:
                            q["correct"] = ord(correct_letter) - ord('A')
                            q["explanation"] = html.escape(explanation)
                            break
        
        return questions
    
    def generate_html(self, course: Dict, lecture_data: Dict, quiz_data: List[Dict]) -> str:
        """Генерирует HTML страницу для курса"""
        
        category = course["category"]
        course_info = COURSE_NAMES.get(category, {})
        category_name = course_info.get("name", category) if isinstance(course_info, dict) else category
        category_icon = course_info.get("icon", "") if isinstance(course_info, dict) else ""
        category_display = f"{category_icon} {category_name}".strip() if category_icon else category_name
        module_name = course["module_name"]
        
        # Получаем красивое название модуля
        module_title = lecture_data["title"]
        
        # Оборачиваем HTML контент лекции в content-card
        lecture_html = self._wrap_lecture_in_cards(lecture_data["html"])
        
        # Генерируем JavaScript данные для квиза
        quiz_js_data = self._generate_quiz_js(quiz_data)
        
        html_template = f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{module_title}</title>
    <!-- Highlight.js CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    {self._get_css()}
</head>
<body>
    <header>
        <div class="container">
            <div class="header-links">
                <a href="mailto:admin@lscode.me">admin@lscode.me</a>
                <a href="https://t.me/lscode_me_bot" target="_blank" rel="noopener noreferrer">
                    <svg class="telegram-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.169 1.858-.896 6.375-1.269 8.453-.152.855-.45 1.14-.74 1.17-.63.06-1.11-.415-1.72-.815-.955-.64-1.496-1.038-2.424-1.662-1.074-.72-.378-1.116.234-1.763.162-.17 2.97-2.723 3.024-2.954.006-.03.011-.15-.056-.212-.067-.058-.166-.038-.238-.023-.101.02-1.705 1.085-4.816 3.188-.456.31-.87.461-1.241.453-.409-.009-1.195-.231-1.78-.42-.718-.234-1.288-.36-1.24-.76.024-.2.36-.405.99-.614 3.884-1.7 6.48-2.82 7.785-3.36 3.774-1.6 4.556-1.88 5.068-1.89.114-.002.37.027.536.16.133.106.17.25.188.352.017.102.038.335.02.515z"/>
                    </svg>
                    Mini App
                </a>
            </div>
            <div class="breadcrumbs">
                <a href="../index.html" class="back-link">← Все курсы</a>
                <span class="separator">/</span>
                <a href="index.html" class="back-link">{category_display}</a>
            </div>
            <h1>{module_title}</h1>
            <p>{category_display} • {module_name}</p>
        </div>
    </header>

    <nav>
        <div class="container">
            <button class="nav-btn active" data-tab="lecture">📚 Лекция</button>
            <button class="nav-btn" data-tab="quiz">✅ Тест ({len(quiz_data)} вопросов)</button>
        </div>
    </nav>

    <main class="container">
        <!-- Lecture Tab -->
        <div id="lecture" class="tab-content active">
            {lecture_html}
        </div>

        <!-- Quiz Tab -->
        <div id="quiz" class="tab-content">
            <div class="quiz-container">
                <div class="content-card">
                    <h2>Тест: {module_title}</h2>
                    <p>Проверьте свои знания! Ответьте на {len(quiz_data)} вопросов и узнайте, как хорошо вы усвоили материал.</p>
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressBar" style="width: 0%"></div>
                    </div>
                </div>

                <div id="quizQuestions"></div>

                <div class="quiz-controls">
                    <button class="btn" id="submitQuiz">Проверить результаты</button>
                    <button class="btn btn-secondary hidden" id="retakeQuiz">Пройти заново</button>
                </div>

                <div id="quizResults" class="hidden"></div>
            </div>
        </div>
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 lscode.me | {category_display}</p>
        </div>
    </footer>

    <!-- Highlight.js JS -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/javascript.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/shell.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/go.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/yaml.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/xml.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/css.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/html.min.js"></script>
    <script>
        // Инициализация highlight.js для всех блоков кода
        document.addEventListener('DOMContentLoaded', function() {{
            hljs.highlightAll();
        }});
    </script>
    {self._get_javascript(quiz_js_data, len(quiz_data))}
</body>
</html>'''
        
        return html_template
    
    def _wrap_lecture_in_cards(self, html_content: str) -> str:
        """Оборачивает содержимое лекции в content-card блоки"""
        # Разбиваем по h2 заголовкам
        parts = re.split(r'(<h2>.*?</h2>)', html_content)
        
        result = []
        current_card = []
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            if part.startswith('<h2>'):
                # Если есть накопленный контент, оборачиваем его
                if current_card:
                    result.append('<div class="content-card">')
                    result.append(''.join(current_card))
                    result.append('</div>')
                    current_card = []
                
                # Начинаем новую карточку с заголовка
                current_card.append(part)
            else:
                current_card.append(part)
        
        # Добавляем последнюю карточку
        if current_card:
            result.append('<div class="content-card">')
            result.append(''.join(current_card))
            result.append('</div>')
        
        return '\n'.join(result)
    
    def _escape_js_string(self, text: str) -> str:
        """Экранирует строку для JavaScript"""
        return (text
                .replace('\\', '\\\\')
                .replace('"', '\\"')
                .replace("'", "\\'")
                .replace('\n', '\\n')
                .replace('\r', '\\r')
                .replace('</script>', '<\\/script>'))
    
    def _generate_quiz_js(self, quiz_data: List[Dict]) -> str:
        """Генерирует JavaScript массив данных для квиза"""
        questions_js = []
        
        for q in quiz_data:
            # Экранируем заголовок
            question_title = self._escape_js_string(q["title"])
            
            # Текст вопроса уже в HTML (конвертирован в parse_quiz)
            question_text = self._escape_js_string(q["text"])
            
            # Опции тоже уже в HTML
            options_js = ',\n                    '.join([
                f'"{self._escape_js_string(opt)}"'
                for opt in q["options"]
            ])
            
            explanation = self._escape_js_string(q.get("explanation") or "")
            correct = q.get("correct", 0) if q.get("correct") is not None else 0
            
            question_js = f'''            {{
                question: "Вопрос {q["number"]}: {question_title}",
                text: "{question_text}",
                options: [
                    {options_js}
                ],
                correct: {correct},
                explanation: "{explanation}"
            }}'''
            
            questions_js.append(question_js)
        
        return ',\n'.join(questions_js)
    
    def _get_css(self) -> str:
        """Возвращает CSS стили"""
        return '''<style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #10b981;
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
            --code-bg: #f1f5f9;
            --success: #10b981;
            --error: #ef4444;
            --warning: #f59e0b;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-main);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 2rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            position: relative;
        }

        header .container {
            position: relative;
        }

        header h1 {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        header p {
            opacity: 0.9;
            font-size: 1.1rem;
        }

        .header-links {
            position: absolute;
            top: 0;
            right: 0;
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 0.85rem;
        }

        .header-links a {
            color: white;
            text-decoration: none;
            opacity: 0.85;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: opacity 0.3s ease;
        }

        .header-links a:hover {
            opacity: 1;
            text-decoration: underline;
        }

        .header-links .telegram-icon {
            width: 14px;
            height: 14px;
            fill: currentColor;
        }

        .breadcrumbs {
            margin-bottom: 0.75rem;
            font-size: 0.9rem;
        }

        .breadcrumbs .separator {
            margin: 0 0.5rem;
            opacity: 0.6;
        }

        .back-link {
            color: white;
            text-decoration: none;
            opacity: 0.8;
        }

        .back-link:hover {
            opacity: 1;
            text-decoration: underline;
        }

        nav {
            background: var(--bg-card);
            border-bottom: 2px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }

        nav .container {
            display: flex;
            gap: 0;
        }

        nav button {
            flex: 1;
            padding: 1rem 2rem;
            border: none;
            background: none;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            transition: all 0.3s;
            border-bottom: 3px solid transparent;
        }

        nav button:hover {
            background: var(--bg-main);
            color: var(--primary);
        }

        nav button.active {
            color: var(--primary);
            border-bottom-color: var(--primary);
        }

        main {
            padding: 2rem 0;
            min-height: calc(100vh - 300px);
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .content-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        h2 {
            color: var(--primary);
            font-size: 1.8rem;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border);
        }

        .content-card h2:first-child {
            margin-top: 0;
        }

        h3 {
            color: var(--text-primary);
            font-size: 1.4rem;
            margin: 1.5rem 0 1rem 0;
        }

        h4 {
            color: var(--text-primary);
            font-size: 1.2rem;
            margin: 1.2rem 0 0.8rem 0;
        }

        p {
            margin: 1rem 0;
            line-height: 1.8;
        }

        ul, ol {
            margin: 1rem 0;
            padding-left: 2rem;
        }

        li {
            margin: 0.5rem 0;
            line-height: 1.6;
        }

        code {
            background: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: var(--primary-dark);
        }

        /* Стили для inline кода (не в pre) */
        code:not(pre code) {
            background: var(--code-bg);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: var(--primary-dark);
        }

        pre {
            background: var(--code-bg);
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border-left: 4px solid var(--primary);
        }

        /* Стили для highlight.js блоков кода */
        pre code.hljs {
            background: transparent;
            padding: 0;
            display: block;
            overflow-x: auto;
        }

        pre.hljs {
            background: #f6f8fa;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border-left: 4px solid var(--primary);
        }

        /* Улучшение контраста для highlight.js */
        .hljs {
            color: #24292e;
            background: #f6f8fa;
        }

        .hljs-comment,
        .hljs-quote {
            color: #6a737d;
            font-style: italic;
        }

        .hljs-keyword,
        .hljs-selector-tag,
        .hljs-type {
            color: #d73a49;
        }

        .hljs-string,
        .hljs-literal {
            color: #032f62;
        }

        .hljs-number {
            color: #005cc5;
        }

        .hljs-function,
        .hljs-title {
            color: #6f42c1;
        }

        .hljs-variable,
        .hljs-attr {
            color: #e36209;
        }

        .hljs-built_in,
        .hljs-builtin-name {
            color: #005cc5;
        }

        .hljs-meta {
            color: #6a737d;
        }

        /* Совместимость со старыми блоками кода */
        pre code {
            background: none;
            padding: 0;
            color: var(--text-primary);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: var(--bg-card);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }

        th {
            background: var(--primary);
            color: white;
            font-weight: 600;
        }

        tr:hover {
            background: var(--bg-main);
        }

        .info-box {
            background: #dbeafe;
            border-left: 4px solid var(--primary);
            padding: 1rem 1.5rem;
            margin: 1.5rem 0;
            border-radius: 4px;
        }

        .info-box strong {
            color: var(--primary);
        }

        /* Quiz Styles */
        .quiz-container {
            max-width: 900px;
            margin: 0 auto;
        }

        .quiz-question {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid var(--primary);
        }

        .quiz-question h3 {
            margin-top: 0;
            color: var(--primary);
            font-size: 1.3rem;
        }

        .question-text {
            font-size: 1.1rem;
            margin: 1rem 0;
        }

        .question-text p {
            margin: 0.5rem 0;
        }

        .question-text pre {
            background: var(--code-bg);
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1rem 0;
            border-left: 3px solid var(--primary);
        }

        .question-text code {
            background: var(--code-bg);
            padding: 0.15rem 0.3rem;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .question-text pre code {
            background: none;
            padding: 0;
        }

        .option-text {
            flex: 1;
        }

        .option-text p {
            margin: 0;
        }

        .option-text code {
            background: rgba(0,0,0,0.05);
            padding: 0.1rem 0.3rem;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .quiz-options {
            margin: 1.5rem 0;
        }

        .quiz-option {
            background: var(--bg-main);
            padding: 1rem 1.5rem;
            margin: 0.75rem 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
            border: 2px solid transparent;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .quiz-option:hover {
            background: #e0f2fe;
            border-color: var(--primary);
            transform: translateX(5px);
        }

        .quiz-option input[type="radio"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
        }

        .quiz-option.correct {
            background: #d1fae5;
            border-color: var(--success);
        }

        .quiz-option.incorrect {
            background: #fee2e2;
            border-color: var(--error);
        }

        .quiz-option.disabled {
            opacity: 0.7;
            cursor: not-allowed;
        }

        /* Стили для текста вопроса и вариантов с кодом */
        .question-text {
            margin: 1rem 0;
        }

        .question-text p {
            margin: 0.5rem 0;
        }

        .question-text pre,
        .option-text pre {
            background: var(--code-bg);
            padding: 1rem;
            border-radius: 6px;
            overflow-x: auto;
            margin: 0.5rem 0;
            border-left: 3px solid var(--primary);
            font-size: 0.9rem;
        }

        .question-text code,
        .option-text code {
            background: var(--code-bg);
            padding: 0.15rem 0.4rem;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }

        .question-text pre code,
        .option-text pre code {
            background: none;
            padding: 0;
        }

        .option-text {
            flex: 1;
        }

        .option-text p {
            margin: 0;
        }

        .quiz-controls {
            text-align: center;
            margin: 2rem 0;
        }

        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 1rem 2.5rem;
            border-radius: 8px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .btn:hover {
            background: var(--primary-dark);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: var(--text-secondary);
            margin-left: 1rem;
        }

        .btn-secondary:hover {
            background: #475569;
        }

        .quiz-result {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 2.5rem;
            margin: 2rem 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .quiz-result h2 {
            border: none;
            margin: 0 0 1rem 0;
        }

        .score-display {
            font-size: 4rem;
            font-weight: 700;
            color: var(--primary);
            margin: 1rem 0;
        }

        .score-text {
            font-size: 1.5rem;
            color: var(--text-secondary);
            margin-bottom: 1.5rem;
        }

        .feedback {
            background: var(--code-bg);
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1rem 0;
            text-align: left;
        }

        .feedback h4 {
            margin-top: 0;
        }

        .emoji {
            font-size: 3rem;
            margin: 1rem 0;
        }

        .progress-bar {
            background: var(--border);
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin: 1rem 0;
        }

        .progress-fill {
            background: linear-gradient(90deg, var(--primary), var(--secondary));
            height: 100%;
            transition: width 0.5s ease;
        }

        footer {
            background: var(--text-primary);
            color: white;
            text-align: center;
            padding: 2rem 0;
            margin-top: 4rem;
        }

        footer a {
            color: white;
            text-decoration: none;
            margin: 0 0.5rem;
            transition: opacity 0.3s ease;
        }

        footer a:hover {
            opacity: 0.8;
            text-decoration: underline;
        }

        .telegram-link {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .telegram-icon {
            width: 18px;
            height: 18px;
            fill: currentColor;
            vertical-align: middle;
        }

        hr {
            border: none;
            border-top: 2px solid var(--border);
            margin: 2rem 0;
        }

        @media (max-width: 768px) {
            header h1 {
                font-size: 1.5rem;
            }

            .header-links {
                font-size: 0.75rem;
                gap: 0.5rem;
                top: 0.5rem;
                right: 0.5rem;
            }

            .header-links .telegram-icon {
                width: 12px;
                height: 12px;
            }

            .content-card {
                padding: 1.5rem;
            }

            nav button {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
            }

            table {
                font-size: 0.9rem;
            }

            th, td {
                padding: 0.75rem 0.5rem;
            }

            .score-display {
                font-size: 3rem;
            }
        }

        .answer-explanation {
            background: #f0f9ff;
            border-left: 4px solid var(--primary);
            padding: 1rem;
            margin-top: 1rem;
            border-radius: 4px;
            display: none;
        }

        .answer-explanation.show {
            display: block;
            animation: slideDown 0.3s ease;
        }

        @keyframes slideDown {
            from {
                opacity: 0;
                max-height: 0;
            }
            to {
                opacity: 1;
                max-height: 500px;
            }
        }

        .hidden {
            display: none !important;
        }

        blockquote {
            border-left: 4px solid var(--primary);
            padding-left: 1rem;
            margin: 1.5rem 0;
            color: var(--text-secondary);
            font-style: italic;
        }

        a {
            color: var(--primary);
            text-decoration: none;
        }

        a:hover {
            text-decoration: underline;
        }

        img {
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            margin: 1.5rem 0;
        }
    </style>'''
    
    def _get_javascript(self, quiz_data_js: str, num_questions: int) -> str:
        """Возвращает JavaScript код"""
        return f'''<script>
        // Quiz data
        const quizData = [
{quiz_data_js}
        ];

        // Tab switching
        const navButtons = document.querySelectorAll('.nav-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        navButtons.forEach(button => {{
            button.addEventListener('click', () => {{
                const tabName = button.dataset.tab;
                
                navButtons.forEach(btn => btn.classList.remove('active'));
                tabContents.forEach(content => content.classList.remove('active'));
                
                button.classList.add('active');
                document.getElementById(tabName).classList.add('active');
            }});
        }});

        // Quiz functionality
        const quizQuestionsContainer = document.getElementById('quizQuestions');
        const submitButton = document.getElementById('submitQuiz');
        const retakeButton = document.getElementById('retakeQuiz');
        const resultsContainer = document.getElementById('quizResults');
        const progressBar = document.getElementById('progressBar');

        let userAnswers = new Array(quizData.length).fill(null);

        // Render quiz questions
        function renderQuiz() {{
            quizQuestionsContainer.innerHTML = '';
            userAnswers = new Array(quizData.length).fill(null);
            
            quizData.forEach((q, index) => {{
                const questionDiv = document.createElement('div');
                questionDiv.className = 'quiz-question';
                questionDiv.innerHTML = `
                    <h3>${{q.question}}</h3>
                    <div class="question-text">${{q.text}}</div>
                    <div class="quiz-options">
                        ${{[0, 1, 2, 3].map((optionIndex) => `
                            <label class="quiz-option" data-question="${{index}}" data-option="${{optionIndex}}">
                                <input type="radio" name="question${{index}}" value="${{optionIndex}}">
                                <span class="option-text">${{q.options[optionIndex]}}</span>
                            </label>
                        `).join('')}}
                    </div>
                    <div class="answer-explanation" id="explanation${{index}}">
                        <strong>Объяснение:</strong> ${{q.explanation}}
                    </div>
                `;
                quizQuestionsContainer.appendChild(questionDiv);
            }});

            // Add event listeners to options
            document.querySelectorAll('.quiz-option').forEach(option => {{
                option.addEventListener('click', function() {{
                    const questionIndex = parseInt(this.dataset.question);
                    const optionIndex = parseInt(this.dataset.option);
                    
                    // Update user answer
                    userAnswers[questionIndex] = optionIndex;
                    
                    // Update radio button
                    this.querySelector('input[type="radio"]').checked = true;
                    
                    // Update progress
                    updateProgress();
                }});
            }});
        }}

        function updateProgress() {{
            const answered = userAnswers.filter(a => a !== null).length;
            const progress = (answered / quizData.length) * 100;
            progressBar.style.width = progress + '%';
        }}

        function submitQuiz() {{
            // Check if all questions are answered
            if (userAnswers.includes(null)) {{
                alert('Пожалуйста, ответьте на все вопросы!');
                return;
            }}

            // Calculate score
            let correctCount = 0;
            quizData.forEach((q, index) => {{
                const userAnswer = userAnswers[index];
                const isCorrect = userAnswer === q.correct;
                
                if (isCorrect) correctCount++;

                // Highlight answers
                const options = document.querySelectorAll(`[data-question="${{index}}"]`);
                options.forEach((option) => {{
                    const optionIndex = parseInt(option.dataset.option);
                    option.classList.add('disabled');
                    if (optionIndex === q.correct) {{
                        option.classList.add('correct');
                    }} else if (optionIndex === userAnswer && !isCorrect) {{
                        option.classList.add('incorrect');
                    }}
                }});

                // Show explanation
                document.getElementById(`explanation${{index}}`).classList.add('show');
            }});

            // Display results
            const percentage = (correctCount / quizData.length * 100).toFixed(0);
            let feedback = '';
            let emoji = '';

            const passThreshold = Math.ceil(quizData.length * 0.7);
            const goodThreshold = Math.ceil(quizData.length * 0.8);
            const excellentThreshold = Math.ceil(quizData.length * 0.9);

            if (correctCount >= excellentThreshold) {{
                feedback = '🌟 Отлично! Вы превосходно усвоили материал. Переходите к следующему модулю.';
                emoji = '🎉';
            }} else if (correctCount >= goodThreshold) {{
                feedback = '✅ Очень хорошо! У вас прочное понимание материала. Рекомендуется лишь повторить темы, где были ошибки.';
                emoji = '👏';
            }} else if (correctCount >= passThreshold) {{
                feedback = '👍 Хорошо! Базовое понимание есть. Рекомендуется перечитать разделы с ошибками.';
                emoji = '📚';
            }} else {{
                feedback = '📚 Рекомендуется внимательно изучить лекцию еще раз. Обратите внимание на разделы, где были ошибки.';
                emoji = '💪';
            }}

            resultsContainer.innerHTML = `
                <div class="quiz-result">
                    <div class="emoji">${{emoji}}</div>
                    <h2>Ваш результат</h2>
                    <div class="score-display">${{correctCount}}/${{quizData.length}}</div>
                    <div class="score-text">${{percentage}}% правильных ответов</div>
                    <div class="feedback">
                        <p>${{feedback}}</p>
                    </div>
                </div>
            `;

            resultsContainer.classList.remove('hidden');
            submitButton.classList.add('hidden');
            retakeButton.classList.remove('hidden');

            // Scroll to results
            resultsContainer.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}

        function retakeQuiz() {{
            renderQuiz();
            resultsContainer.classList.add('hidden');
            resultsContainer.innerHTML = '';
            submitButton.classList.remove('hidden');
            retakeButton.classList.add('hidden');
            progressBar.style.width = '0%';
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        // Event listeners
        submitButton.addEventListener('click', submitQuiz);
        retakeButton.addEventListener('click', retakeQuiz);

        // Initialize quiz
        renderQuiz();
    </script>'''
    
    def generate_course_index(self, category: str, modules: List[Dict], category_path: Path) -> str:
        """Генерирует страницу курса из README.md"""
        
        course_info = COURSE_NAMES.get(category, {})
        category_name = course_info.get("name", category) if isinstance(course_info, dict) else category
        category_icon = course_info.get("icon", "") if isinstance(course_info, dict) else ""
        category_display = f"{category_icon} {category_name}".strip() if category_icon else category_name
        readme_path = category_path / "README.md"
        
        # Читаем README.md, если существует
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                readme_content = f.read()
            
            # Заменяем ссылки на модули: ./01_Intro/ или (01_Intro/) -> 01_Intro.html
            def replace_module_link(match):
                module_dir = match.group(1).rstrip('/')
                return f']({module_dir}.html)'
            
            # Форматы: [text](./01_Intro/) или [text](01_Intro/) или [text](./01_Intro/lecture.md)
            readme_content = re.sub(r'\]\(\./(\d{2}_[^/)]+)/(?:lecture\.md)?\)', replace_module_link, readme_content)
            readme_content = re.sub(r'\]\((\d{2}_[^/)]+)/(?:lecture\.md)?\)', replace_module_link, readme_content)
            
            # Конвертируем markdown в HTML
            md = markdown.Markdown(extensions=[
                'extra', 
                'codehilite',
                'tables', 
                'fenced_code'
            ], extension_configs={
                'codehilite': {
                    'css_class': 'hljs',
                    'use_pygments': False,
                    'noclasses': False,
                }
            })
            readme_html = md.convert(readme_content)
            
            # Post-processing: преобразуем классы codehilite в классы для highlight.js
            readme_html = re.sub(
                r'<pre class="codehilite"><code class="language-(\w+)"',
                r'<pre><code class="language-\1 hljs"',
                readme_html
            )
            readme_html = re.sub(
                r'<pre class="codehilite"><code>',
                r'<pre><code class="hljs">',
                readme_html
            )
            readme_html = re.sub(
                r'<pre class="codehilite"><code class="hljs"',
                r'<pre><code class="hljs"',
                readme_html
            )
            
            # Оборачиваем в content-card блоки
            content_html = self._wrap_lecture_in_cards(readme_html)
        else:
            # Fallback: генерируем список модулей
            modules_html = []
            for module in modules:
                module_name = module["module_name"]
                lecture_data = self.parse_lecture(module["lecture_path"], category)
                title = lecture_data["title"]
                
                filename = f"{module_name}.html"
                modules_html.append(f'''
                    <a href="{filename}" class="module-card">
                        <span class="module-number">{module_name.split("_")[0]}</span>
                        <span class="module-title">{title}</span>
                    </a>''')
            
            content_html = f'''
                <div class="content-card">
                    <h2>Модули курса</h2>
                    <div class="modules-list">
                        {''.join(modules_html)}
                    </div>
                </div>'''
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{category_display}</title>
    <!-- Highlight.js CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #10b981;
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-main);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 3rem 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            position: relative;
        }}

        header .container {{
            position: relative;
        }}

        header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .header-links {{
            position: absolute;
            top: 0;
            right: 0;
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 0.85rem;
        }}

        .header-links a {{
            color: white;
            text-decoration: none;
            opacity: 0.85;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: opacity 0.3s ease;
        }}

        .header-links a:hover {{
            opacity: 1;
            text-decoration: underline;
        }}

        .header-links .telegram-icon {{
            width: 14px;
            height: 14px;
            fill: currentColor;
        }}

        header p {{
            opacity: 0.9;
            font-size: 1.2rem;
        }}

        .back-link {{
            color: white;
            text-decoration: none;
            opacity: 0.8;
            font-size: 0.9rem;
            display: inline-block;
            margin-bottom: 0.75rem;
        }}

        .back-link:hover {{
            opacity: 1;
            text-decoration: underline;
        }}

        main {{
            padding: 2rem 0 4rem;
        }}

        .modules-list {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .module-card {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            background: var(--bg-card);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            text-decoration: none;
            color: var(--text-primary);
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            transition: all 0.2s;
            border: 2px solid transparent;
        }}

        .module-card:hover {{
            border-color: var(--primary);
            transform: translateX(8px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}

        .module-number {{
            background: var(--primary);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 1.1rem;
            flex-shrink: 0;
        }}

        .module-title {{
            font-weight: 500;
            font-size: 1.1rem;
            line-height: 1.4;
        }}

        footer {{
            background: var(--text-primary);
            color: white;
            text-align: center;
            padding: 2rem 0;
        }}

        footer a {{
            color: white;
            text-decoration: none;
            margin: 0 0.5rem;
            transition: opacity 0.3s ease;
        }}

        footer a:hover {{
            opacity: 0.8;
            text-decoration: underline;
        }}

        .telegram-link {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}

        .telegram-icon {{
            width: 18px;
            height: 18px;
            fill: currentColor;
            vertical-align: middle;
        }}

        /* Content card styles for README */
        .content-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        h2 {{
            color: var(--primary);
            font-size: 1.8rem;
            margin: 2rem 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border);
        }}

        .content-card h2:first-child {{
            margin-top: 0;
        }}

        h3 {{
            color: var(--text-primary);
            font-size: 1.4rem;
            margin: 1.5rem 0 1rem 0;
        }}

        h4 {{
            color: var(--text-primary);
            font-size: 1.2rem;
            margin: 1.2rem 0 0.8rem 0;
        }}

        p {{
            margin: 1rem 0;
            line-height: 1.8;
        }}

        ul, ol {{
            margin: 1rem 0;
            padding-left: 2rem;
        }}

        li {{
            margin: 0.5rem 0;
            line-height: 1.6;
        }}

        code {{
            background: #f1f5f9;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: var(--primary-dark);
        }}

        pre {{
            background: #f1f5f9;
            padding: 1.5rem;
            border-radius: 8px;
            overflow-x: auto;
            margin: 1.5rem 0;
            border-left: 4px solid var(--primary);
        }}

        pre code {{
            background: none;
            padding: 0;
            color: var(--text-primary);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5rem 0;
            background: var(--bg-card);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        th, td {{
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: var(--primary);
            color: white;
            font-weight: 600;
        }}

        tr:hover {{
            background: var(--bg-main);
        }}

        a {{
            color: var(--primary);
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}

        hr {{
            border: none;
            border-top: 2px solid var(--border);
            margin: 2rem 0;
        }}

        blockquote {{
            border-left: 4px solid var(--primary);
            padding-left: 1rem;
            margin: 1.5rem 0;
            color: var(--text-secondary);
            font-style: italic;
        }}

        @media (max-width: 768px) {{
            header h1 {{
                font-size: 1.8rem;
            }}

            .header-links {{
                font-size: 0.75rem;
                gap: 0.5rem;
                top: 0.5rem;
                right: 0.5rem;
            }}

            .header-links .telegram-icon {{
                width: 12px;
                height: 12px;
            }}

            .content-card {{
                padding: 1.5rem;
            }}

            .module-card {{
                padding: 1rem 1.25rem;
            }}

            .module-number {{
                width: 40px;
                height: 40px;
                font-size: 0.9rem;
            }}

            .module-title {{
                font-size: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-links">
                <a href="mailto:admin@lscode.me">admin@lscode.me</a>
                <a href="https://t.me/lscode_me_bot" target="_blank" rel="noopener noreferrer">
                    <svg class="telegram-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.169 1.858-.896 6.375-1.269 8.453-.152.855-.45 1.14-.74 1.17-.63.06-1.11-.415-1.72-.815-.955-.64-1.496-1.038-2.424-1.662-1.074-.72-.378-1.116.234-1.763.162-.17 2.97-2.723 3.024-2.954.006-.03.011-.15-.056-.212-.067-.058-.166-.038-.238-.023-.101.02-1.705 1.085-4.816 3.188-.456.31-.87.461-1.241.453-.409-.009-1.195-.231-1.78-.42-.718-.234-1.288-.36-1.24-.76.024-.2.36-.405.99-.614 3.884-1.7 6.48-2.82 7.785-3.36 3.774-1.6 4.556-1.88 5.068-1.89.114-.002.37.027.536.16.133.106.17.25.188.352.017.102.038.335.02.515z"/>
                    </svg>
                    Mini App
                </a>
            </div>
            <a href="../index.html" class="back-link">← Все курсы</a>
            <h1>{category_display}</h1>
            <p>{len(modules)} лекций</p>
        </div>
    </header>

    <main class="container">
        {content_html}
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 lscode.me</p>
        </div>
    </footer>
    <!-- Highlight.js JS -->
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/javascript.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/shell.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/go.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/yaml.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/xml.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/css.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/html.min.js"></script>
    <script>
        // Инициализация highlight.js для всех блоков кода
        document.addEventListener('DOMContentLoaded', function() {{
            hljs.highlightAll();
        }});
    </script>
</body>
</html>'''
    
    def generate_main_index(self, courses_by_category: Dict[str, List[Dict]]) -> str:
        """Генерирует главную страницу со списком всех курсов, сгруппированных по разделам"""
        
        # Собираем все используемые разделы и группируем курсы по разделам
        sections_to_courses: Dict[str, List[Tuple[str, Dict]]] = {}
        
        for category in sorted(courses_by_category.keys()):
            course_list = courses_by_category[category]
            course_info = COURSE_NAMES.get(category, {})
            
            if not isinstance(course_info, dict):
                continue
            
            # Получаем разделы для этого курса
            course_sections = course_info.get("sections", set())
            if not course_sections:
                # Если у курса нет разделов, пропускаем его или добавляем в "Другие"
                continue
            
            # Добавляем курс во все его разделы
            for section in course_sections:
                if section not in sections_to_courses:
                    sections_to_courses[section] = []
                sections_to_courses[section].append((category, course_info))
        
        # Генерируем HTML для разделов
        sections_html = []
        for section in sorted(sections_to_courses.keys()):
            courses_in_section = sections_to_courses[section]
            # Сортируем курсы внутри раздела по названию
            courses_in_section.sort(key=lambda x: x[1].get("name", x[0]))
            
            # Генерируем HTML для курсов в разделе
            courses_html = []
            for category, course_info in courses_in_section:
                course_list = courses_by_category[category]
                category_name = course_info.get("name", category)
                category_icon = course_info.get("icon", "")
                category_display = f"{category_icon} {category_name}".strip() if category_icon else category_name
                num_modules = len(course_list)
                
                courses_html.append(f'''
                    <a href="{category}/index.html" class="course-card">
                        <div class="course-info">
                            <h3>{category_display}</h3>
                            <p>{num_modules} лекций</p>
                        </div>
                        <span class="arrow">→</span>
                    </a>''')
            
            sections_html.append(f'''
                <section class="section-group">
                    <h2 class="section-title">{section}</h2>
                    <div class="courses-grid">
                        {''.join(courses_html)}
                    </div>
                </section>''')
        
        return f'''<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>lscode.me - Все курсы</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        :root {{
            --primary: #2563eb;
            --primary-dark: #1e40af;
            --secondary: #10b981;
            --bg-main: #f8fafc;
            --bg-card: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', sans-serif;
            line-height: 1.6;
            color: var(--text-primary);
            background: var(--bg-main);
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }}

        header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 4rem 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            position: relative;
        }}

        header .container {{
            position: relative;
        }}

        header h1 {{
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        header p {{
            opacity: 0.9;
            font-size: 1.3rem;
        }}

        .header-links {{
            position: absolute;
            top: 1rem;
            right: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            font-size: 0.85rem;
        }}

        .header-links a {{
            color: white;
            text-decoration: none;
            opacity: 0.85;
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            transition: opacity 0.3s ease;
        }}

        .header-links a:hover {{
            opacity: 1;
            text-decoration: underline;
        }}

        .header-links .telegram-icon {{
            width: 14px;
            height: 14px;
            fill: currentColor;
        }}

        main {{
            padding: 3rem 0 4rem;
        }}

        .section-group {{
            margin-bottom: 3rem;
        }}

        .section-title {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 3px solid var(--primary);
        }}

        .courses-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
        }}

        .course-card {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-card);
            padding: 2rem;
            border-radius: 16px;
            text-decoration: none;
            color: var(--text-primary);
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            transition: all 0.3s;
            border: 2px solid transparent;
        }}

        .course-card:hover {{
            border-color: var(--primary);
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
        }}

        .course-info h3 {{
            font-size: 1.4rem;
            font-weight: 600;
            margin-bottom: 0.25rem;
            color: var(--text-primary);
        }}

        .course-info p {{
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}

        .arrow {{
            font-size: 1.5rem;
            color: var(--primary);
            opacity: 0.5;
            transition: all 0.3s;
        }}

        .course-card:hover .arrow {{
            opacity: 1;
            transform: translateX(4px);
        }}

        footer {{
            background: var(--text-primary);
            color: white;
            text-align: center;
            padding: 2rem 0;
        }}

        @media (max-width: 768px) {{
            header h1 {{
                font-size: 2rem;
            }}

            header p {{
                font-size: 1.1rem;
            }}

            .header-links {{
                font-size: 0.75rem;
                gap: 0.5rem;
                top: 0.5rem;
                right: 0.5rem;
            }}

            .header-links .telegram-icon {{
                width: 12px;
                height: 12px;
            }}

            .courses-grid {{
                grid-template-columns: 1fr;
            }}

            .course-card {{
                padding: 1.5rem;
            }}

            .section-title {{
                font-size: 1.5rem;
            }}

            .course-info h3 {{
                font-size: 1.2rem;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <div class="container">
            <div class="header-links">
                <a href="mailto:admin@lscode.me">admin@lscode.me</a>
                <a href="https://t.me/lscode_me_bot" target="_blank" rel="noopener noreferrer">
                    <svg class="telegram-icon" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.562 8.161c-.169 1.858-.896 6.375-1.269 8.453-.152.855-.45 1.14-.74 1.17-.63.06-1.11-.415-1.72-.815-.955-.64-1.496-1.038-2.424-1.662-1.074-.72-.378-1.116.234-1.763.162-.17 2.97-2.723 3.024-2.954.006-.03.011-.15-.056-.212-.067-.058-.166-.038-.238-.023-.101.02-1.705 1.085-4.816 3.188-.456.31-.87.461-1.241.453-.409-.009-1.195-.231-1.78-.42-.718-.234-1.288-.36-1.24-.76.024-.2.36-.405.99-.614 3.884-1.7 6.48-2.82 7.785-3.36 3.774-1.6 4.556-1.88 5.068-1.89.114-.002.37.027.536.16.133.106.17.25.188.352.017.102.038.335.02.515z"/>
                    </svg>
                    Mini App
                </a>
            </div>
            <h1>📚 lscode.me</h1>
            <p>Курсы по программированию, IT и естественным наукам</p>
        </div>
    </header>

    <main class="container">
        {''.join(sections_html)}
    </main>

    <footer>
        <div class="container">
            <p>&copy; 2025 lscode.me</p>
        </div>
    </footer>
</body>
</html>'''
    
    def generate_all(self):
        """Генерирует HTML для всех курсов"""
        courses = self.find_all_courses()
        
        # Группируем курсы по категориям
        courses_by_category = {}
        for course in courses:
            category = course["category"]
            if category not in courses_by_category:
                courses_by_category[category] = []
            courses_by_category[category].append(course)
        
        print(f"Найдено {len(courses)} модулей в {len(courses_by_category)} курсах:")
        
        # Обрабатываем каждую категорию
        for category in sorted(courses_by_category.keys()):
            category_modules = courses_by_category[category]
            course_info = COURSE_NAMES.get(category, {})
            category_name = course_info.get("name", category) if isinstance(course_info, dict) else category
            category_icon = course_info.get("icon", "") if isinstance(course_info, dict) else ""
            category_display = f"{category_icon} {category_name}".strip() if category_icon else category_name
            
            print(f"\n📂 {category_display} ({len(category_modules)} модулей)")
            
            # Создаём директорию для курса
            course_html_dir = self.html_dir / category
            course_html_dir.mkdir(exist_ok=True)
            
            # Генерируем страницы для каждого модуля
            for course in category_modules:
                module_name = course["module_name"]
                print(f"  📚 {module_name}...")
                
                # Парсим лекцию
                lecture_data = self.parse_lecture(course['lecture_path'], category)
                
                # Парсим квиз
                quiz_data = self.parse_quiz(course['quiz_path'])
                
                # Генерируем HTML
                html_content = self.generate_html(course, lecture_data, quiz_data)
                
                # Сохраняем файл
                output_filename = f"{module_name}.html"
                output_path = course_html_dir / output_filename
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            # Генерируем index.html для курса
            category_path = self.courses_dir / category
            course_index_html = self.generate_course_index(category, category_modules, category_path)
            course_index_path = course_html_dir / "index.html"
            with open(course_index_path, 'w', encoding='utf-8') as f:
                f.write(course_index_html)
            print(f"  ✅ Сохранено: {course_html_dir}/")
        
        # Генерируем главную страницу
        print(f"\n📑 Генерация главной страницы...")
        main_index_html = self.generate_main_index(courses_by_category)
        main_index_path = self.html_dir / "index.html"
        with open(main_index_path, 'w', encoding='utf-8') as f:
            f.write(main_index_html)
        print(f"  ✅ Сохранено: {main_index_path}")
        
        print(f"\n🎉 Готово!")
        print(f"   {len(courses_by_category)} курсов")
        print(f"   {len(courses)} модулей")
        print(f"   Директория: {self.html_dir}")


def main():
    import sys
    # Если передан аргумент - используем его как базовую директорию
    base_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    generator = CourseHTMLGenerator(base_dir)
    generator.generate_all()


if __name__ == "__main__":
    main()
