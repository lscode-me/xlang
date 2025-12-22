#!/usr/bin/env python3
"""
Автоматическое исправление форматирования Markdown файлов.

Исправляет семь самых частых ошибок:
- Нет пустой строки между bold-пунктами (могут слипнуться)
- Нет пустой строки между **Bold:** и списком (список не отрендерится)
- Нет пустой строки между текстом и списком (списки склеиваются в строку)
- Нет пустой строки ПЕРЕД блоком кода
- Нет пустой строки ПОСЛЕ блока кода
- Нет пустой строки ПОСЛЕ заголовка
- Лишние пустые строки после заголовков вопросов (## Question N: ...)
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


def get_code_block_ranges(lines: List[str]) -> List[Tuple[int, int]]:
    """Находит диапазоны строк внутри блоков кода.
    
    Поддерживает вложенные блоки: ```` может содержать ``` внутри.
    """
    ranges = []
    in_code_block = False
    start = 0
    opening_backticks = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Считаем количество бэктиков в начале строки
        backtick_count = 0
        for char in stripped:
            if char == '`':
                backtick_count += 1
            else:
                break
        
        # Должно быть минимум 3 бэктика
        if backtick_count >= 3:
            if not in_code_block:
                # Открываем блок кода
                in_code_block = True
                start = i
                opening_backticks = backtick_count
            else:
                # Закрываем блок только если количество бэктиков >= opening
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


def ends_with_colon(text: str) -> bool:
    """Проверяет, заканчивается ли текст двоеточием (учитывая markdown)."""
    # Убираем trailing markdown форматирование
    text = text.rstrip('*_`')
    return text.endswith(':')


def fix_code_block_blank_before(lines: List[str]) -> Tuple[List[str], int]:
    """Исправление пустой строки ПЕРЕД блоком кода.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    in_code_block = False
    opening_backticks = 0
    offset = 0  # Смещение индексов из-за вставленных строк
    
    # Проходим в прямом порядке
    i = 0
    while i < len(fixed_lines):
        line = fixed_lines[i]
        stripped = line.strip()
        
        # Считаем количество бэктиков в начале строки
        backtick_count = 0
        for char in stripped:
            if char == '`':
                backtick_count += 1
            else:
                break
        
        # Должно быть минимум 3 бэктика
        if backtick_count >= 3:
            if not in_code_block:
                # Открываем блок кода
                in_code_block = True
                opening_backticks = backtick_count
                
                # Проверяем предыдущую строку
                if i > 0:
                    prev_line = fixed_lines[i - 1].strip()
                    # Исключения: пустая строка, заголовок, ---, текст с двоеточием на конце
                    if (prev_line and 
                        not prev_line.startswith('#') and 
                        prev_line != "---" and 
                        not ends_with_colon(prev_line)):
                        # Вставляем пустую строку перед блоком кода
                        fixed_lines.insert(i, '')
                        fixes_count += 1
                        i += 1  # Пропускаем вставленную строку
            else:
                # Закрываем блок только если количество бэктиков >= opening
                if backtick_count >= opening_backticks:
                    in_code_block = False
                    opening_backticks = 0
        
        i += 1
    
    return fixed_lines, fixes_count


def fix_code_block_blank_after(lines: List[str]) -> Tuple[List[str], int]:
    """Исправление пустой строки ПОСЛЕ блока кода.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    in_code_block = False
    opening_backticks = 0
    
    # Проходим в обратном порядке, чтобы индексы не сдвигались
    for i in range(len(fixed_lines) - 1, -1, -1):
        line = fixed_lines[i]
        stripped = line.strip()
        
        # Считаем количество бэктиков в начале строки
        backtick_count = 0
        for char in stripped:
            if char == '`':
                backtick_count += 1
            else:
                break
        
        # Должно быть минимум 3 бэктика
        if backtick_count >= 3:
            if in_code_block:
                # Закрываем блок только если количество бэктиков >= opening
                if backtick_count >= opening_backticks:
                    in_code_block = False
                    opening_backticks = 0
                    
                    # Проверяем следующую строку
                    if i + 1 < len(fixed_lines):
                        next_line = fixed_lines[i + 1].strip()
                        # Исключения: пустая строка, заголовок, ---, **Output:**
                        if (next_line and 
                            not next_line.startswith('#') and 
                            next_line != "---" and 
                            not next_line.startswith('**')):
                            # Вставляем пустую строку после блока кода
                            fixed_lines.insert(i + 1, '')
                            fixes_count += 1
            else:
                # Открываем блок кода
                in_code_block = True
                opening_backticks = backtick_count
    
    return fixed_lines, fixes_count


def fix_header_blank_after(lines: List[str], code_ranges: List[Tuple[int, int]]) -> Tuple[List[str], int]:
    """Исправление пустой строки ПОСЛЕ заголовка.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    
    # Проходим в обратном порядке, чтобы индексы не сдвигались
    for i in range(len(fixed_lines) - 1, -1, -1):
        # Пропускаем первую строку и строки внутри блоков кода
        if i == 0 or is_in_code_block(i, code_ranges):
            continue
        
        line = fixed_lines[i]
        
        # Если это заголовок (не внутри кода)
        if re.match(r'^#{1,6}\s+', line):
            # Проверяем следующую строку (должна быть пустой)
            if i + 1 < len(fixed_lines):
                next_line = fixed_lines[i + 1].strip()
                # После заголовка должна быть пустая строка ИЛИ другой заголовок ИЛИ ---
                if next_line and not next_line.startswith('#') and next_line != "---":
                    # Вставляем пустую строку после заголовка
                    fixed_lines.insert(i + 1, '')
                    fixes_count += 1
    
    return fixed_lines, fixes_count


def fix_bold_list_items(lines: List[str]) -> Tuple[List[str], int]:
    """Исправление пустых строк между пунктами списка с **bold**.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    # Проходим в обратном порядке, чтобы индексы не сдвигались
    for i in range(len(fixed_lines) - 1, -1, -1):
        line = fixed_lines[i]
        # Если это пункт списка с bold: - **Something:**
        if re.match(r'^[-*]\s+\*\*[^*]+\*\*', line) or re.match(r'^[-*]\s+\*\*[^*]+:', line):
            # Проверяем следующую строку
            if i + 1 < len(fixed_lines):
                next_line = fixed_lines[i + 1]
                # Если следующая строка тоже bold-пункт
                if (re.match(r'^[-*]\s+\*\*[^*]+\*\*', next_line) or 
                    re.match(r'^[-*]\s+\*\*[^*]+:', next_line)):
                    # Проверяем, что между ними действительно нет пустой строки
                    # (следующая строка не пустая, значит пустой строки между ними нет)
                    if next_line.strip():
                        # Вставляем пустую строку после текущей строки
                        fixed_lines.insert(i + 1, '')
                        fixes_count += 1
    
    return fixed_lines, fixes_count


def fix_bold_heading_before_list(lines: List[str], code_ranges: List[Tuple[int, int]]) -> Tuple[List[str], int]:
    """Исправление пустой строки между **Bold:** и последующим списком.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    # Проходим в обратном порядке, чтобы индексы не сдвигались
    for i in range(len(fixed_lines) - 1, -1, -1):
        # Пропускаем строки внутри блоков кода
        if is_in_code_block(i, code_ranges):
            continue
        
        stripped = fixed_lines[i].strip()
        
        # Паттерн: строка вида **Something:** (bold заголовок)
        if re.match(r'^\*\*[^*]+:\*\*$', stripped):
            # Проверяем следующую строку
            if i + 1 < len(fixed_lines):
                next_line_raw = fixed_lines[i + 1]
                next_line = next_line_raw.strip()
                # Если следующая строка — пункт списка
                if (next_line.startswith('-') or 
                    next_line.startswith('*') or 
                    re.match(r'^\d+\.', next_line)):
                    # Проверяем, что между ними действительно нет пустой строки
                    # (следующая строка не пустая, значит пустой строки между ними нет)
                    if next_line:
                        # Вставляем пустую строку после текущей строки
                        fixed_lines.insert(i + 1, '')
                        fixes_count += 1
    
    return fixed_lines, fixes_count


def fix_text_colon_before_list(lines: List[str], code_ranges: List[Tuple[int, int]]) -> Tuple[List[str], int]:
    """Исправление пустой строки между обычным текстом и последующим списком.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    
    # Проходим в обратном порядке, чтобы индексы не сдвигались
    for i in range(len(fixed_lines) - 1, -1, -1):
        # Пропускаем строки внутри блоков кода
        if is_in_code_block(i, code_ranges):
            continue
        
        stripped = fixed_lines[i].strip()
        
        # Пропускаем пустые строки, заголовки, списки, блоки кода, разделители
        if (not stripped or 
            stripped.startswith('#') or 
            stripped.startswith('-') or 
            stripped.startswith('*') or 
            stripped.startswith('`') or 
            stripped == "---" or
            re.match(r'^\d+\.', stripped) or
            (stripped.startswith('**') and stripped.endswith('**'))):
            continue
        
        # Проверяем следующую строку - если это список, нужна пустая строка
        if i + 1 < len(fixed_lines):
            next_line_raw = fixed_lines[i + 1]
            next_line = next_line_raw.strip()
            # Если следующая строка — пункт списка
            if (next_line.startswith('-') or 
                next_line.startswith('*') or 
                re.match(r'^\d+\.', next_line)):
                # Проверяем, что между ними действительно нет пустой строки
                # (следующая строка не пустая, значит пустой строки между ними нет)
                if next_line:
                    # Вставляем пустую строку после текущей строки
                    fixed_lines.insert(i + 1, '')
                    fixes_count += 1
    
    return fixed_lines, fixes_count


def fix_question_header_extra_blanks(lines: List[str], code_ranges: List[Tuple[int, int]]) -> Tuple[List[str], int]:
    """Удаление лишних пустых строк после заголовков вопросов (## Question N: ...).
    
    После заголовка вопроса должна быть ровно одна пустая строка перед текстом вопроса.
    
    Возвращает исправленные строки и количество исправлений.
    """
    fixed_lines = lines.copy()
    fixes_count = 0
    
    # Проходим в обратном порядке, чтобы индексы не сдвигались
    for i in range(len(fixed_lines) - 1, -1, -1):
        # Пропускаем строки внутри блоков кода
        if is_in_code_block(i, code_ranges):
            continue
        
        line = fixed_lines[i]
        
        # Проверяем, является ли это заголовком вопроса
        if re.match(r'^## Question \d+:', line):
            # Ищем следующую непустую строку после заголовка
            j = i + 1
            blank_count = 0
            
            # Считаем пустые строки сразу после заголовка
            while j < len(fixed_lines):
                if is_in_code_block(j, code_ranges):
                    break
                if not fixed_lines[j].strip():
                    blank_count += 1
                    j += 1
                else:
                    break
            
            # Если пустых строк больше одной, удаляем лишние
            if blank_count > 1:
                # Удаляем лишние пустые строки (оставляем только одну)
                for _ in range(blank_count - 1):
                    fixed_lines.pop(i + 1)
                    fixes_count += 1
    
    return fixed_lines, fixes_count


def fix_file(filepath: Path, dry_run: bool = False) -> Tuple[int, int, int, int, int, int, int]:
    """Исправление одного файла.
    
    Возвращает (количество исправлений bold_list, количество исправлений bold_heading, 
                количество исправлений code_block_before, количество исправлений code_block_after,
                количество исправлений header_after, количество исправлений text_colon,
                количество исправлений question_header_blanks).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        lines = content.split('\n')
    except Exception as e:
        print(f"❌ Ошибка чтения {filepath}: {e}")
        return (0, 0, 0, 0, 0, 0, 0)
    
    # Находим диапазоны блоков кода (чтобы игнорировать их содержимое)
    code_ranges = get_code_block_ranges(lines)
    
    # Исправляем все проблемы
    # Важно: сначала исправляем код блоки, потом остальное, чтобы code_ranges оставались актуальными
    fixed_lines, fixes_code_block_before = fix_code_block_blank_before(lines)
    # Пересчитываем code_ranges после изменений
    code_ranges = get_code_block_ranges(fixed_lines)
    
    fixed_lines, fixes_code_block_after = fix_code_block_blank_after(fixed_lines)
    # Пересчитываем code_ranges после изменений
    code_ranges = get_code_block_ranges(fixed_lines)
    
    fixed_lines, fixes_bold_list = fix_bold_list_items(fixed_lines)
    fixed_lines, fixes_bold_heading = fix_bold_heading_before_list(fixed_lines, code_ranges)
    fixed_lines, fixes_text_colon = fix_text_colon_before_list(fixed_lines, code_ranges)
    fixed_lines, fixes_header_after = fix_header_blank_after(fixed_lines, code_ranges)
    fixed_lines, fixes_question_header_blanks = fix_question_header_extra_blanks(fixed_lines, code_ranges)
    
    total_fixes = fixes_bold_list + fixes_bold_heading + fixes_code_block_before + fixes_code_block_after + fixes_header_after + fixes_text_colon + fixes_question_header_blanks
    
    if total_fixes > 0:
        if not dry_run:
            # Сохраняем исправленный файл
            new_content = '\n'.join(fixed_lines)
            # Сохраняем с тем же окончанием строк, что было в оригинале
            if content.endswith('\n'):
                new_content += '\n'
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ {filepath}: исправлено {total_fixes} проблем "
                  f"(bold_list: {fixes_bold_list}, bold_heading: {fixes_bold_heading}, "
                  f"code_before: {fixes_code_block_before}, code_after: {fixes_code_block_after}, "
                  f"header_after: {fixes_header_after}, text_before_list: {fixes_text_colon}, "
                  f"question_header_blanks: {fixes_question_header_blanks})")
        else:
            print(f"🔍 {filepath}: найдено {total_fixes} проблем для исправления "
                  f"(bold_list: {fixes_bold_list}, bold_heading: {fixes_bold_heading}, "
                  f"code_before: {fixes_code_block_before}, code_after: {fixes_code_block_after}, "
                  f"header_after: {fixes_header_after}, text_before_list: {fixes_text_colon}, "
                  f"question_header_blanks: {fixes_question_header_blanks})")
    
    return (fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks)


def fix_module(module_path: Path, dry_run: bool = False) -> Tuple[int, int, int, int, int, int, int]:
    """Исправление модуля (lecture.md и quiz.md).
    
    Возвращает (общее количество исправлений bold_list, общее количество исправлений bold_heading, 
                общее количество исправлений code_block_before, общее количество исправлений code_block_after,
                общее количество исправлений header_after, общее количество исправлений text_colon,
                общее количество исправлений question_header_blanks).
    """
    total_bold_list = 0
    total_bold_heading = 0
    total_code_block_before = 0
    total_code_block_after = 0
    total_header_after = 0
    total_text_colon = 0
    total_question_header_blanks = 0
    
    for filename in ['lecture.md', 'quiz.md']:
        filepath = module_path / filename
        if filepath.exists():
            fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks = fix_file(filepath, dry_run)
            total_bold_list += fixes_bold_list
            total_bold_heading += fixes_bold_heading
            total_code_block_before += fixes_code_block_before
            total_code_block_after += fixes_code_block_after
            total_header_after += fixes_header_after
            total_text_colon += fixes_text_colon
            total_question_header_blanks += fixes_question_header_blanks
    
    return (total_bold_list, total_bold_heading, total_code_block_before, total_code_block_after, total_header_after, total_text_colon, total_question_header_blanks)


def fix_course(course_path: Path, dry_run: bool = False) -> Tuple[int, int, int, int, int, int, int]:
    """Исправление всего курса.
    
    Возвращает (общее количество исправлений bold_list, общее количество исправлений bold_heading, 
                общее количество исправлений code_block_before, общее количество исправлений code_block_after,
                общее количество исправлений header_after, общее количество исправлений text_colon,
                общее количество исправлений question_header_blanks).
    """
    total_bold_list = 0
    total_bold_heading = 0
    total_code_block_before = 0
    total_code_block_after = 0
    total_header_after = 0
    total_text_colon = 0
    total_question_header_blanks = 0

    # Сначала пробуем исправить корневые markdown-файлы курса (например, README.md),
    # потому что они тоже попадают в HTML и могут страдать от тех же проблем со списками.
    for root_md in ['README.md']:
        root_md_path = course_path / root_md
        if root_md_path.exists():
            (fixes_bold_list,
             fixes_bold_heading,
             fixes_code_block_before,
             fixes_code_block_after,
             fixes_header_after,
             fixes_text_colon,
             fixes_question_header_blanks) = fix_file(root_md_path, dry_run)

            total_bold_list += fixes_bold_list
            total_bold_heading += fixes_bold_heading
            total_code_block_before += fixes_code_block_before
            total_code_block_after += fixes_code_block_after
            total_header_after += fixes_header_after
            total_text_colon += fixes_text_colon
            total_question_header_blanks += fixes_question_header_blanks
    
    for item in sorted(course_path.iterdir()):
        if item.is_dir() and item.name[0].isdigit():
            fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks = fix_module(item, dry_run)
            total_bold_list += fixes_bold_list
            total_bold_heading += fixes_bold_heading
            total_code_block_before += fixes_code_block_before
            total_code_block_after += fixes_code_block_after
            total_header_after += fixes_header_after
            total_text_colon += fixes_text_colon
            total_question_header_blanks += fixes_question_header_blanks
    
    return (total_bold_list, total_bold_heading, total_code_block_before, total_code_block_after, total_header_after, total_text_colon, total_question_header_blanks)


def main():
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Автоматическое исправление форматирования Markdown')
    parser.add_argument('path', nargs='?', help='Путь к файлу, модулю или курсу')
    parser.add_argument('-a', '--all', action='store_true', help='Исправить все курсы')
    parser.add_argument('-n', '--dry-run', action='store_true', help='Только показать, что будет исправлено (не изменять файлы)')
    
    args = parser.parse_args()
    
    # Определяем путь к курсам
    script_dir = Path(__file__).parent
    courses_path = script_dir.parent / 'Courses'
    
    total_bold_list = 0
    total_bold_heading = 0
    total_code_block_before = 0
    total_code_block_after = 0
    total_header_after = 0
    total_text_colon = 0
    total_question_header_blanks = 0
    
    if args.dry_run:
        print("🔍 Режим проверки (dry-run): файлы не будут изменены")
        print("=" * 60)
    
    if args.all:
        # Исправляем все курсы
        print("=" * 60)
        print("🔧 Исправление форматирования всех курсов")
        print("=" * 60)
        
        for course_dir in sorted(courses_path.iterdir()):
            if course_dir.is_dir():
                print(f"\n📚 {course_dir.name}")
                fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks = fix_course(course_dir, args.dry_run)
                total_bold_list += fixes_bold_list
                total_bold_heading += fixes_bold_heading
                total_code_block_before += fixes_code_block_before
                total_code_block_after += fixes_code_block_after
                total_header_after += fixes_header_after
                total_text_colon += fixes_text_colon
                total_question_header_blanks += fixes_question_header_blanks
    
    elif args.path:
        path = Path(args.path)
        
        if path.is_file():
            # Исправляем один файл
            fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks = fix_file(path, args.dry_run)
            total_bold_list = fixes_bold_list
            total_bold_heading = fixes_bold_heading
            total_code_block_before = fixes_code_block_before
            total_code_block_after = fixes_code_block_after
            total_header_after = fixes_header_after
            total_text_colon = fixes_text_colon
            total_question_header_blanks = fixes_question_header_blanks
        
        elif path.is_dir():
            # Исправляем директорию
            if (path / 'lecture.md').exists() or (path / 'quiz.md').exists():
                # Это модуль
                fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks = fix_module(path, args.dry_run)
                total_bold_list = fixes_bold_list
                total_bold_heading = fixes_bold_heading
                total_code_block_before = fixes_code_block_before
                total_code_block_after = fixes_code_block_after
                total_header_after = fixes_header_after
                total_text_colon = fixes_text_colon
                total_question_header_blanks = fixes_question_header_blanks
            else:
                # Это курс
                fixes_bold_list, fixes_bold_heading, fixes_code_block_before, fixes_code_block_after, fixes_header_after, fixes_text_colon, fixes_question_header_blanks = fix_course(path, args.dry_run)
                total_bold_list = fixes_bold_list
                total_bold_heading = fixes_bold_heading
                total_code_block_before = fixes_code_block_before
                total_code_block_after = fixes_code_block_after
                total_header_after = fixes_header_after
                total_text_colon = fixes_text_colon
                total_question_header_blanks = fixes_question_header_blanks
    
    else:
        parser.print_help()
        return
    
    # Итог
    print("\n" + "=" * 60)
    total_fixes = total_bold_list + total_bold_heading + total_code_block_before + total_code_block_after + total_header_after + total_text_colon + total_question_header_blanks
    if total_fixes == 0:
        print("✅ Проблем для исправления не найдено!")
    else:
        print(f"📊 Итого исправлено:")
        print(f"   - Пустых строк между bold-пунктами: {total_bold_list}")
        print(f"   - Пустых строк между **Bold:** и списком: {total_bold_heading}")
        print(f"   - Пустых строк между текстом и списком: {total_text_colon}")
        print(f"   - Пустых строк ПЕРЕД блоками кода: {total_code_block_before}")
        print(f"   - Пустых строк ПОСЛЕ блоков кода: {total_code_block_after}")
        print(f"   - Пустых строк ПОСЛЕ заголовков: {total_header_after}")
        print(f"   - Лишних пустых строк после заголовков вопросов: {total_question_header_blanks}")
        print(f"   - Всего: {total_fixes}")
    print("=" * 60)
    
    sys.exit(0)


if __name__ == '__main__':
    main()

