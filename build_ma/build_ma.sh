#!/bin/bash

# Скрипт для генерации Mini App тестов для изучения языков
# Автоматически создает venv, устанавливает зависимости и запускает генератор

set -e  # Прерывать при ошибках

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$SCRIPT_DIR"

echo "🚀 Генератор Mini App тестов для изучения языков"
echo "=================================================="
echo ""

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python 3 не найден"
    echo "   Установите Python 3.8 или выше"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "✅ Найден Python $PYTHON_VERSION"

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

# Запуск валидации
echo ""
echo "🔍 Валидация вопросов..."
echo "-------------------------------------------"
if ! python3 validate_questions.py; then
    echo "❌ Валидация не прошла. Исправьте ошибки."
    exit 1
fi

# Запуск сборки
echo ""
echo "🔨 Сборка статического сайта..."
echo "-------------------------------------------"
python3 build_site.py

# Валидация сгенерированного HTML
echo ""
echo "🔍 Валидация HTML..."
echo "-------------------------------------------"
if ! python3 validate_html.py; then
    echo "⚠️  HTML валидация выявила проблемы (но сборка завершена)"
fi

echo ""
echo "==========================================="
echo "✅ Генерация завершена!"
echo "   Результат: html/ma/index.html"
echo "   Запуск: python3 dev_server.py"
echo "==========================================="
