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

# Запуск генератора
echo ""
echo "🔨 Запуск генератора Mini App..."
echo "-------------------------------------------"
python generate_ma.py "$PROJECT_DIR"

echo ""
echo "==========================================="
echo "✅ Генерация завершена!"
echo "   Результат: html/ma/index.html"
echo "==========================================="
