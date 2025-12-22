#!/usr/bin/env python3
"""
Проверка комплектности курсов.

Проверяет:
- Наличие README в папке курса
- Наличие lecture.md и quiz.md в каждой папке лекции
- Соответствие между лекциями в README и реальными папками
- Отсутствие лишних файлов/папок
"""

import re
import sys
from pathlib import Path
from typing import Set, List, Tuple


def extract_lecture_modules_from_readme(readme_path: Path) -> Set[str]:
    """
    Извлекает имена модулей лекций из README.
    Ищет ссылки вида:
    - [текст](XX_ModuleName/)
    - [текст](./XX_ModuleName/)
    - [текст](XX_ModuleName/lecture.md)
    - [текст](XX_ModuleName/file.md)
    """
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Паттерн для ссылок: [текст](XX_ModuleName/) или [текст](XX_ModuleName/file.md)
    # Извлекаем имя модуля (XX_ModuleName) из пути
    pattern = r'\[[^\]]+\]\(\.?/?([0-9]+_[^/)]+)(?:/|\))'
    matches = re.findall(pattern, content)
    
    return set(matches)


def get_lecture_directories(course_path: Path) -> Set[str]:
    """Получает список папок лекций в курсе (исключая README.md)."""
    modules = set()
    for item in course_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            modules.add(item.name)
    return modules


def check_lecture_directory(lecture_path: Path) -> Tuple[bool, List[str], List[str]]:
    """
    Проверяет папку лекции.
    Возвращает: (is_valid, missing_files, extra_files)
    """
    required_files = {'lecture.md', 'quiz.md'}
    
    files = set()
    for item in lecture_path.iterdir():
        if item.is_file():
            files.add(item.name)
        elif item.is_dir():
            files.add(f"{item.name}/")  # Помечаем папки
    
    missing = required_files - files
    extra = files - required_files
    
    is_valid = len(missing) == 0 and len(extra) == 0
    return is_valid, sorted(missing), sorted(extra)


def check_course(course_path: Path, dry_run: bool = True) -> dict:
    """
    Проверяет курс на комплектность.
    Возвращает словарь с результатами проверки.
    """
    results = {
        'course_path': course_path,
        'has_readme': False,
        'readme_modules': set(),
        'actual_modules': set(),
        'missing_modules': [],
        'extra_modules': [],
        'module_issues': {},  # module_name -> {'missing': [], 'extra': []}
        'files_to_delete': [],
        'directories_to_delete': [],
        'course_root_extra_files': [],  # Лишние файлы в корне курса
    }
    
    # Проверка README
    readme_path = course_path / 'README.md'
    if not readme_path.exists():
        return results
    
    results['has_readme'] = True
    
    # Извлекаем модули из README
    results['readme_modules'] = extract_lecture_modules_from_readme(readme_path)
    
    # Получаем реальные папки модулей
    results['actual_modules'] = get_lecture_directories(course_path)
    
    # Проверяем корневую папку курса на лишние файлы
    # В корне должны быть только README.md и папки с модулями
    allowed_in_root = {'README.md'}
    for item in course_path.iterdir():
        if item.is_file() and item.name not in allowed_in_root:
            results['course_root_extra_files'].append(item)
            results['files_to_delete'].append(item)
        elif item.is_dir() and not item.name.startswith('.') and item.name not in results['actual_modules']:
            # Лишняя папка (не модуль)
            results['directories_to_delete'].append(item)
    
    # Модули, которые есть в README, но отсутствуют в файловой системе
    results['missing_modules'] = sorted(results['readme_modules'] - results['actual_modules'])
    
    # Модули, которые есть в файловой системе, но не упомянуты в README
    results['extra_modules'] = sorted(results['actual_modules'] - results['readme_modules'])
    
    # Проверяем каждую папку модуля
    for module_name in results['actual_modules']:
        module_path = course_path / module_name
        is_valid, missing, extra = check_lecture_directory(module_path)
        
        if not is_valid:
            results['module_issues'][module_name] = {
                'missing': missing,
                'extra': extra
            }
            
            # Собираем файлы для удаления
            for item in extra:
                if item.endswith('/'):
                    # Это папка
                    dir_name = item.rstrip('/')
                    results['directories_to_delete'].append(module_path / dir_name)
                else:
                    # Это файл
                    results['files_to_delete'].append(module_path / item)
    
    return results


def print_results(results: dict, dry_run: bool = True):
    """Выводит результаты проверки."""
    course_path = results['course_path']
    print(f"\n📁 Курс: {course_path.name}")
    print("=" * 60)
    
    # README
    if not results['has_readme']:
        print("❌ README.md отсутствует!")
        return
    
    print("✅ README.md найден")
    
    # Лишние файлы в корне курса
    if results['course_root_extra_files']:
        print(f"\n🗑️  Лишние файлы в корне курса ({len(results['course_root_extra_files'])}):")
        for file_path in results['course_root_extra_files']:
            print(f"   - {file_path.name}")
            if not dry_run:
                print(f"     → Будет удален: {file_path}")
    
    # Статистика модулей
    readme_count = len(results['readme_modules'])
    actual_count = len(results['actual_modules'])
    print(f"\n📊 Модули:")
    print(f"   В README: {readme_count}")
    print(f"   В файловой системе: {actual_count}")
    
    # Отсутствующие модули
    if results['missing_modules']:
        print(f"\n⚠️  Отсутствующие модули ({len(results['missing_modules'])}):")
        for module in results['missing_modules']:
            print(f"   - {module}")
    
    # Лишние модули
    if results['extra_modules']:
        print(f"\n🗑️  Лишние модули ({len(results['extra_modules'])}):")
        for module in results['extra_modules']:
            print(f"   - {module}")
            if not dry_run:
                print(f"     → Будет удалена папка: {course_path / module}")
    
    # Проблемы в модулях
    if results['module_issues']:
        print(f"\n⚠️  Проблемы в модулях ({len(results['module_issues'])}):")
        for module_name, issues in sorted(results['module_issues'].items()):
            print(f"   {module_name}:")
            if issues['missing']:
                print(f"      Отсутствуют: {', '.join(issues['missing'])}")
            if issues['extra']:
                print(f"      Лишние: {', '.join(issues['extra'])}")
                for item in issues['extra']:
                    if item.endswith('/'):
                        print(f"         → Будет удалена папка: {course_path / module_name / item.rstrip('/')}")
                    else:
                        print(f"         → Будет удален файл: {course_path / module_name / item}")
    
    # Файлы для удаления
    if results['files_to_delete']:
        print(f"\n🗑️  Файлы для удаления ({len(results['files_to_delete'])}):")
        for file_path in results['files_to_delete']:
            print(f"   - {file_path.relative_to(course_path.parent)}")
    
    # Папки для удаления
    if results['directories_to_delete']:
        print(f"\n🗑️  Папки для удаления ({len(results['directories_to_delete'])}):")
        for dir_path in results['directories_to_delete']:
            print(f"   - {dir_path.relative_to(course_path.parent)}")
    
    # Итоговая статистика
    total_issues = (
        len(results['missing_modules']) +
        len(results['extra_modules']) +
        len(results['module_issues']) +
        len(results['course_root_extra_files']) +
        len(results['files_to_delete']) +
        len(results['directories_to_delete'])
    )
    
    if total_issues == 0:
        print(f"\n✅ Курс полностью корректен!")
    else:
        print(f"\n📈 Итого проблем: {total_issues}")


def delete_extra_items(results: dict):
    """Удаляет лишние файлы и папки."""
    deleted_files = 0
    deleted_dirs = 0
    
    # Удаляем лишние файлы
    for file_path in results['files_to_delete']:
        try:
            file_path.unlink()
            deleted_files += 1
        except Exception as e:
            print(f"   ⚠️  Ошибка при удалении {file_path}: {e}")
    
    # Удаляем лишние папки (сначала вложенные, потом родительские)
    for dir_path in sorted(results['directories_to_delete'], key=lambda p: len(p.parts), reverse=True):
        try:
            dir_path.rmdir()  # rmdir удаляет только пустые папки
            deleted_dirs += 1
        except OSError:
            # Если папка не пустая, удаляем рекурсивно
            import shutil
            shutil.rmtree(dir_path)
            deleted_dirs += 1
        except Exception as e:
            print(f"   ⚠️  Ошибка при удалении {dir_path}: {e}")
    
    # Удаляем лишние модули (папки, не упомянутые в README)
    for module_name in results['extra_modules']:
        module_path = results['course_path'] / module_name
        try:
            import shutil
            shutil.rmtree(module_path)
            deleted_dirs += 1
        except Exception as e:
            print(f"   ⚠️  Ошибка при удалении модуля {module_path}: {e}")
    
    return deleted_files, deleted_dirs


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Проверка комплектности курсов: проверяет наличие файлов, соответствие README и удаляет лишнее'
    )
    parser.add_argument(
        'path',
        nargs='?',
        help='Путь к курсу или директории с курсами (по умолчанию: весь workspace)'
    )
    parser.add_argument(
        '-n', '--dry-run',
        action='store_true',
        default=True,
        help='Только показать, что будет изменено (по умолчанию: включен)'
    )
    parser.add_argument(
        '--no-dry-run',
        action='store_false',
        dest='dry_run',
        help='Реально удалить лишние файлы и папки'
    )
    
    args = parser.parse_args()
    
    # Получаем путь к workspace
    script_dir = Path(__file__).parent
    workspace = script_dir.parent
    courses_dir = workspace / 'Courses'
    
    # Определяем целевую директорию
    if args.path:
        target = Path(args.path)
        if not target.is_absolute():
            target = workspace / args.path
        if not target.exists():
            print(f"❌ Путь не найден: {target}")
            sys.exit(1)
    else:
        target = courses_dir
    
    if args.dry_run:
        print("🔍 Режим проверки (dry-run): файлы не будут удалены")
    else:
        print("⚠️  РЕЖИМ УДАЛЕНИЯ: лишние файлы и папки будут удалены!")
    
    print("=" * 60)
    
    # Определяем, это один курс или директория с курсами
    courses_to_check = []
    
    # Проверяем, является ли target курсом (есть README.md)
    if (target / 'README.md').exists():
        # Это один курс
        courses_to_check = [target]
    elif target.is_dir():
        # Это директория - ищем курсы внутри
        # Курс определяется наличием README.md в папке
        for item in target.iterdir():
            if item.is_dir() and not item.name.startswith('.') and (item / 'README.md').exists():
                courses_to_check.append(item)
    else:
        print(f"❌ Не найдено курсов в: {target}")
        sys.exit(1)
    
    if not courses_to_check:
        print(f"❌ Не найдено курсов для проверки")
        sys.exit(1)
    
    # Проверяем каждый курс
    all_results = []
    for course_path in sorted(courses_to_check):
        results = check_course(course_path, dry_run=args.dry_run)
        all_results.append(results)
        print_results(results, dry_run=args.dry_run)
    
    # Удаляем лишнее, если не dry-run
    if not args.dry_run:
        print("\n" + "=" * 60)
        print("🗑️  Удаление лишних файлов и папок...")
        
        total_deleted_files = 0
        total_deleted_dirs = 0
        
        for results in all_results:
            deleted_files, deleted_dirs = delete_extra_items(results)
            total_deleted_files += deleted_files
            total_deleted_dirs += deleted_dirs
        
        print(f"\n✅ Удалено: {total_deleted_files} файлов, {total_deleted_dirs} папок")
    
    # Итоговая статистика
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)
    
    total_courses = len(all_results)
    courses_with_readme = sum(1 for r in all_results if r['has_readme'])
    courses_ok = sum(1 for r in all_results if (
        r['has_readme'] and
        len(r['missing_modules']) == 0 and
        len(r['extra_modules']) == 0 and
        len(r['module_issues']) == 0 and
        len(r['course_root_extra_files']) == 0
    ))
    
    total_missing_modules = sum(len(r['missing_modules']) for r in all_results)
    total_extra_modules = sum(len(r['extra_modules']) for r in all_results)
    total_module_issues = sum(len(r['module_issues']) for r in all_results)
    total_course_root_extra_files = sum(len(r['course_root_extra_files']) for r in all_results)
    total_files_to_delete = sum(len(r['files_to_delete']) for r in all_results)
    total_dirs_to_delete = sum(len(r['directories_to_delete']) for r in all_results)
    
    print(f"Курсов проверено: {total_courses}")
    print(f"Курсов с README: {courses_with_readme}")
    print(f"Курсов без проблем: {courses_ok}")
    print(f"Отсутствующих модулей: {total_missing_modules}")
    print(f"Лишних модулей: {total_extra_modules}")
    print(f"Модулей с проблемами: {total_module_issues}")
    print(f"Лишних файлов в корне курсов: {total_course_root_extra_files}")
    print(f"Лишних файлов в модулях: {total_files_to_delete - total_course_root_extra_files}")
    print(f"Лишних папок: {total_dirs_to_delete}")
    
    if args.dry_run and (total_files_to_delete > 0 or total_dirs_to_delete > 0 or total_extra_modules > 0):
        print(f"\n💡 Используйте --no-dry-run для удаления лишних файлов и папок")


if __name__ == '__main__':
    main()

