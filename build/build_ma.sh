#!/bin/bash

# Скрипт для генерации Mini App тестов для изучения языков
# Автоматически создает venv, устанавливает зависимости и запускает генератор
# Использование: ./build_ma.sh <course_id>
# course_id ОБЯЗАТЕЛЕН и должен существовать в data/config.json

set -e  # Прерывать при ошибках

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

# Получить course_id из аргумента
COURSE_ID="$1"
DEBUG_FLAG=""

# Check for --debug flag in any position
if [[ "$2" == "--debug" ]] || [[ "$3" == "--debug" ]]; then
  DEBUG_FLAG="--debug"
fi

if [ -z "$COURSE_ID" ]; then
    echo "❌ Ошибка: Не указан ID курса"
    echo "   Использование: ./build_ma.sh <course_id> [--debug]"
    echo "   Пример: ./build_ma.sh turk"
    echo "   Пример: ./build_ma.sh turk --debug"
    exit 1
fi

# Получить название курса и dest_folder из конфига
CONFIG_FILE="$PROJECT_DIR/data/config.json"
# Оптимизировано: один вызов jq вместо двух
COURSE_DATA=$(jq -r ".courses[] | select(.id == \"$COURSE_ID\") | .name + \"|\" + (.dest_folder // \"null\")" "$CONFIG_FILE")
COURSE_NAME=$(echo "$COURSE_DATA" | cut -d'|' -f1)
DEST_FOLDER=$(echo "$COURSE_DATA" | cut -d'|' -f2)

if [ -z "$COURSE_NAME" ] || [ "$COURSE_NAME" = "null" ]; then
    echo "❌ Ошибка: Курс '$COURSE_ID' не найден в config.json"
    exit 1
fi

if [ -z "$DEST_FOLDER" ] || [ "$DEST_FOLDER" = "null" ]; then
    # Если dest_folder не указан, используем course_id
    DEST_FOLDER="$COURSE_ID"
fi

echo "🚀 Генератор Mini App тестов для изучения языков"
echo "=================================================="
echo "📚 Курс: $COURSE_ID (данные из: data/$COURSE_NAME)"
echo ""

# Проверка наличия jq
if ! command -v jq &> /dev/null; then
    echo "❌ Ошибка: jq не найден"
    echo "   Установите jq: brew install jq (macOS) или apt-get install jq (Linux)"
    exit 1
fi

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python 3 не найден"
    echo "   Установите Python 3.8 или выше"
    exit 1
fi

echo "✅ Найден Python"

# Создание venv, если его нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
    echo "✅ Виртуальное окружение создано"
else
    echo "✅ Виртуальное окружение уже существует"
fi

# Активация venv
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Установка/обновление зависимостей
echo "📥 Установка зависимостей..."
pip install -q -r requirements.txt
echo "✅ Зависимости установлены"

# Запуск валидации и балансировки
echo ""
echo "🔍 Валидация и обработка данных..."
echo "-------------------------------------------"
if ! python3 manage_vocabulary.py fix-all "$COURSE_ID"; then
    echo "❌ Валидация не прошла. Исправьте ошибки."
    exit 1
fi

# Запуск сборки
echo ""
echo "🔨 Сборка статического сайта..."
echo "-------------------------------------------"
python3 build_site.py "$COURSE_ID" $DEBUG_FLAG

# Валидация сгенерированного HTML
echo ""
echo "🔍 Валидация HTML..."
echo "-------------------------------------------"
if ! python3 validate_html.py "$COURSE_ID"; then
    echo "⚠️  HTML валидация выявила проблемы (но сборка завершена)"
fi

echo ""
echo "==========================================="
echo "✅ Генерация завершена!"
echo "   Результат: html/$DEST_FOLDER/index.html"
echo "   Запуск: python3 dev_server.py $COURSE_ID"
echo "==========================================="
