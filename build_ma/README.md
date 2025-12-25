# RU→TR Vocabulary Quiz - Build Scripts

Эта директория содержит скрипты для валидации и сборки Telegram Mini App.

## 🚀 Быстрый старт

### 1. Валидация вопросов
```bash
python3 validate_questions.py
```

### 2. Сборка сайта
```bash
python3 build_site.py
```

### 3. Запуск локального сервера
```bash
python3 dev_server.py
```
Откройте: http://localhost:8000

## 📝 Скрипты

### validate_questions.py
Проверяет все JSONL файлы в `Vocabulary/RU-TR_Phrases/{A1,A2,B1}/` на:
- Корректность JSON
- Обязательные поля
- Уникальность ID
- Правильность вариантов ответов
- Отсутствие кириллицы в турецком
- Отсутствие LLM мусора

**Exit code**: 0 = успех, 1 = ошибки найдены

### build_site.py
Генерирует статический сайт в `html/ma/`:
1. Запускает валидацию
2. Очищает output директорию
3. Создаёт HTML страницы для квизов
4. Генерирует JSON с вопросами
5. Копирует CSS/JS ассеты

**Output**: `html/ma/`

### dev_server.py
Запускает простой HTTP сервер на порту 8000 для локального тестирования.

**Требования**: Сначала запустите `build_site.py`

## 📚 Подробная документация

См. [README_VOCABULARY_QUIZ.md](../README_VOCABULARY_QUIZ.md) в корне репозитория.
