#!/bin/bash
#
# Скрипт для запуска всех проверок курсов
#
# Использование:
#   ./check.sh [опции] [путь]
#
# Опции:
#   --completeness      Проверить комплектность курсов
#   --quality           Анализировать качество курсов
#   --markdown          Проверить форматирование Markdown
#   --quiz              Проверить распределение ответов в квизах
#   --all               Запустить все проверки (по умолчанию)
#   --no-dry-run        Реально применять изменения (по умолчанию только проверка)
#   --help              Показать эту справку
#

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Путь к директории со скриптами
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"

# Флаги проверок
RUN_COMPLETENESS=false
RUN_QUALITY=false
RUN_MARKDOWN=false
RUN_QUIZ=false
DRY_RUN=true
TARGET_PATH=""

# Функция для вывода заголовка
print_header() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Функция для вывода разделителя
print_separator() {
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo ""
}

# Функция для вывода справки
show_help() {
    cat << EOF
${CYAN}Скрипт проверки курсов${NC}

Использование:
    ./check.sh [опции] [путь]

Опции:
    --completeness      Проверить комплектность курсов
    --quality           Анализировать качество курсов
    --markdown          Проверить форматирование Markdown
    --quiz              Проверить распределение ответов в квизах
    --all               Запустить все проверки (по умолчанию)
    --no-dry-run        Реально применять изменения (по умолчанию только проверка)
    --help              Показать эту справку

Путь:
    Путь к курсу или директории с курсами (по умолчанию: Courses/)

Примеры:
    ./check.sh --all Courses/IT_Basics/
    ./check.sh --completeness --quality Courses/
    ./check.sh --markdown --no-dry-run Courses/AI/

EOF
}

# Парсинг аргументов
parse_args() {
    local run_all=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --completeness)
                RUN_COMPLETENESS=true
                shift
                ;;
            --quality)
                RUN_QUALITY=true
                shift
                ;;
            --markdown)
                RUN_MARKDOWN=true
                shift
                ;;
            --quiz)
                RUN_QUIZ=true
                shift
                ;;
            --all)
                run_all=true
                shift
                ;;
            --no-dry-run)
                DRY_RUN=false
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            -*)
                echo -e "${RED}❌ Неизвестная опция: $1${NC}" >&2
                echo "Используйте --help для справки"
                exit 1
                ;;
            *)
                if [[ -z "$TARGET_PATH" ]]; then
                    TARGET_PATH="$1"
                else
                    echo -e "${RED}❌ Указано несколько путей: $TARGET_PATH и $1${NC}" >&2
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # Если не указаны конкретные проверки, запускаем все
    if [[ "$run_all" == true ]] || [[ "$RUN_COMPLETENESS" == false && "$RUN_QUALITY" == false && "$RUN_MARKDOWN" == false && "$RUN_QUIZ" == false ]]; then
        RUN_COMPLETENESS=true
        RUN_QUALITY=true
        RUN_MARKDOWN=true
        RUN_QUIZ=true
    fi
    
    # Устанавливаем путь по умолчанию
    if [[ -z "$TARGET_PATH" ]]; then
        TARGET_PATH="Courses/"
    fi
    
    # Преобразуем относительный путь в абсолютный
    if [[ ! "$TARGET_PATH" = /* ]]; then
        TARGET_PATH="$WORKSPACE/$TARGET_PATH"
    fi
    
    # Проверяем существование пути
    if [[ ! -e "$TARGET_PATH" ]]; then
        echo -e "${RED}❌ Путь не найден: $TARGET_PATH${NC}" >&2
        exit 1
    fi
}

# Функция для запуска проверки комплектности
run_completeness_check() {
    print_header "📋 ПРОВЕРКА КОМПЛЕКТНОСТИ КУРСОВ"
    
    local dry_run_flag=""
    if [[ "$DRY_RUN" == true ]]; then
        dry_run_flag="-n"
    else
        dry_run_flag="--no-dry-run"
    fi
    
    if "$SCRIPT_DIR/check_course_completeness.py" $dry_run_flag "$TARGET_PATH"; then
        echo -e "${GREEN}✅ Проверка комплектности завершена${NC}"
        return 0
    else
        echo -e "${RED}❌ Ошибка при проверке комплектности${NC}" >&2
        return 1
    fi
}

# Функция для запуска анализа качества
run_quality_check() {
    print_header "📊 АНАЛИЗ КАЧЕСТВА КУРСОВ"
    
    if "$SCRIPT_DIR/analyze_quality.py" "$TARGET_PATH"; then
        echo -e "${GREEN}✅ Анализ качества завершен${NC}"
        return 0
    else
        echo -e "${RED}❌ Ошибка при анализе качества${NC}" >&2
        return 1
    fi
}

# Функция для запуска проверки Markdown
run_markdown_check() {
    print_header "📝 ПРОВЕРКА ФОРМАТИРОВАНИЯ MARKDOWN"
    
    local dry_run_flag=""
    if [[ "$DRY_RUN" == true ]]; then
        dry_run_flag="-n"
    fi
    
    if "$SCRIPT_DIR/fix_markdown_format.py" $dry_run_flag "$TARGET_PATH"; then
        echo -e "${GREEN}✅ Проверка форматирования Markdown завершена${NC}"
        return 0
    else
        echo -e "${RED}❌ Ошибка при проверке форматирования Markdown${NC}" >&2
        return 1
    fi
}

# Функция для запуска проверки квизов
run_quiz_check() {
    print_header "🎯 ПРОВЕРКА РАСПРЕДЕЛЕНИЯ ОТВЕТОВ В КВИЗАХ"
    
    local dry_run_flag=""
    if [[ "$DRY_RUN" == true ]]; then
        dry_run_flag="-n"
    fi
    
    if "$SCRIPT_DIR/shuffle_quiz_answers.py" $dry_run_flag "$TARGET_PATH"; then
        echo -e "${GREEN}✅ Проверка квизов завершена${NC}"
        return 0
    else
        echo -e "${RED}❌ Ошибка при проверке квизов${NC}" >&2
        return 1
    fi
}

# Главная функция
main() {
    parse_args "$@"
    
    print_header "🔍 ЗАПУСК ПРОВЕРОК КУРСОВ"
    
    echo -e "${BLUE}Целевой путь:${NC} $TARGET_PATH"
    echo -e "${BLUE}Режим:${NC} $([ "$DRY_RUN" == true ] && echo "Проверка (dry-run)" || echo "Применение изменений")"
    echo ""
    echo -e "${BLUE}Запускаемые проверки:${NC}"
    [[ "$RUN_COMPLETENESS" == true ]] && echo "  ✅ Проверка комплектности"
    [[ "$RUN_QUALITY" == true ]] && echo "  ✅ Анализ качества"
    [[ "$RUN_MARKDOWN" == true ]] && echo "  ✅ Проверка форматирования Markdown"
    [[ "$RUN_QUIZ" == true ]] && echo "  ✅ Проверка распределения ответов в квизах"
    
    if [[ "$DRY_RUN" == false ]]; then
        echo ""
        echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Режим применения изменений включен!${NC}"
        echo -e "${YELLOW}   Файлы будут изменены!${NC}"
        echo ""
        read -p "Продолжить? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Отменено пользователем${NC}"
            exit 0
        fi
    fi
    
    print_separator
    
    local exit_code=0
    local checks_run=0
    local checks_passed=0
    
    # Запускаем проверки
    if [[ "$RUN_COMPLETENESS" == true ]]; then
        ((checks_run++))
        if run_completeness_check; then
            ((checks_passed++))
        else
            exit_code=1
        fi
        print_separator
    fi
    
    if [[ "$RUN_QUALITY" == true ]]; then
        ((checks_run++))
        if run_quality_check; then
            ((checks_passed++))
        else
            exit_code=1
        fi
        print_separator
    fi
    
    if [[ "$RUN_MARKDOWN" == true ]]; then
        ((checks_run++))
        if run_markdown_check; then
            ((checks_passed++))
        else
            exit_code=1
        fi
        print_separator
    fi
    
    if [[ "$RUN_QUIZ" == true ]]; then
        ((checks_run++))
        if run_quiz_check; then
            ((checks_passed++))
        else
            exit_code=1
        fi
        print_separator
    fi
    
    # Итоговая статистика
    print_header "📈 ИТОГОВАЯ СТАТИСТИКА"
    
    echo -e "${BLUE}Проверок запущено:${NC} $checks_run"
    echo -e "${BLUE}Проверок пройдено:${NC} $checks_passed"
    
    if [[ $checks_passed -eq $checks_run ]]; then
        echo -e "${GREEN}✅ Все проверки завершены успешно!${NC}"
    else
        echo -e "${YELLOW}⚠️  Некоторые проверки завершились с ошибками${NC}"
    fi
    
    exit $exit_code
}

# Запуск главной функции
main "$@"

