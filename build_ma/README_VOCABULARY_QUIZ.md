# RU→TR Vocabulary Quiz

Telegram Mini App для изучения турецкого языка через тесты на перевод с русского на турецкий.

## 🎯 Описание

Статический веб-сайт с квизами в стиле "Кто хочет стать миллионером":
- Выберите уровень (A1, A2 или B1)
- Ответьте на 15 случайных вопросов из базы вопросов выбранного уровня
- Получите результат с объяснениями

Все JSONL файлы одного уровня автоматически объединяются в один тест.

Прогресс сохраняется в Telegram CloudStorage (с fallback на localStorage).

## 📁 Структура проекта

```
xlang/
├── build_ma/                      # Скрипты сборки и валидации
│   ├── validate_questions.py     # Валидация JSONL файлов
│   ├── build_site.py             # Генерация статического сайта
│   └── dev_server.py             # Локальный сервер для разработки
├── Vocabulary/RU-TR/             # Исходные данные (JSONL)
│   ├── A1/
│   │   ├── 001.jsonl
│   │   └── 002.jsonl
│   ├── A2/
│   │   └── 001.jsonl
│   └── B1/
│       └── 001.jsonl
├── html/ma/                      # Собранный статический сайт (output)
│   ├── index.html                # Каталог уровней
│   ├── assets/
│   │   ├── app.css
│   │   ├── app.js
│   │   └── storage.js
│   └── RU-TR/
│       ├── A1/
│       │   ├── index.html        # Квиз уровня A1
│       │   └── questions.json    # Все вопросы A1 (объединенные)
│       ├── A2/
│       │   ├── index.html
│       │   └── questions.json
│       └── B1/
│           ├── index.html
│           └── questions.json
└── prompts/                      # Промпты для LLM
    ├── generate_questions_prompt.md
    └── self_check_prompt.md
```

## 🚀 Быстрый старт

### 1. Валидация вопросов

Проверьте все JSONL файлы на ошибки:

```bash
cd build_ma
python3 validate_questions.py
```

Скрипт проверяет:
- ✅ Корректность JSON
- ✅ Наличие обязательных полей
- ✅ Уникальность ID
- ✅ 4 варианта ответа (все уникальные)
- ✅ Отсутствие кириллицы в турецких вариантах
- ✅ Отсутствие LLM мусора ("правильный ответ", "As an AI" и т.д.)
- ✅ Корректное поле `explain_ru` с разделителями

### 2. Сборка сайта

Генерирует статический сайт в `html/ma/`:

```bash
cd build_ma
python3 build_site.py
```

Скрипт:
1. Запускает валидацию
2. Очищает `html/ma/` (кроме `.gitkeep`)
3. Генерирует HTML страницы для каждого набора вопросов
4. Создаёт `questions.json` для каждого квиза
5. Копирует CSS/JS ассеты

### 3. Локальный запуск

Запустите локальный сервер для тестирования:

```bash
cd build_ma
python3 dev_server.py
```

Откройте в браузере: http://localhost:8000

## 📝 Формат JSONL

Каждая строка в JSONL файле = один JSON объект вопроса.

### Обязательные поля

```json
{
  "id": "A1-001-0001",
  "ru": "Где находится остановка?",
  "tr": [
    "Durak nerede?",
    "Otobüs nerede?",
    "Burası neresi?",
    "Saat kaç?"
  ],
  "correct": 1,
  "explain_ru": "durak — остановка, nerede — где"
}
```

- **id**: Уникальный идентификатор в формате `<LEVEL>-<SET>-<NUM>`
  - Пример: `A1-001-0001`, `A2-003-0015`, `B1-002-0008`
- **ru**: Фраза на русском языке (2-15 слов)
- **tr**: Массив из **ровно 4** вариантов перевода на турецкий
  - Только **один** правильный
  - Остальные 3 — правдоподобные дистракторы
- **correct**: Номер правильного варианта (1, 2, 3 или 4)
- **explain_ru**: Объяснение с базовыми формами турецких слов
  - Формат: `<слово> — <перевод>, <слово> — <перевод>`

### Опциональные поля

```json
{
  "tags": ["transport", "location"],
  "source": "llm"
}
```

## ➕ Добавление новых вопросов

### Вручную

1. Создайте или откройте JSONL файл в `Vocabulary/RU-TR/<LEVEL>/`
2. Добавьте строки с вопросами (каждая строка = один JSON объект)
3. Запустите валидацию: `python3 build_ma/validate_questions.py`
4. Исправьте ошибки, если есть
5. Соберите сайт: `python3 build_ma/build_site.py`

**Примечание**: Все JSONL файлы одного уровня автоматически объединяются в один тест. Файлы 001.jsonl, 002.jsonl и т.д. - это просто исходники для организации вопросов по темам.

### С помощью LLM

1. Откройте промпт: `prompts/generate_questions_prompt.md`
2. Укажите параметры: уровень, набор, темы, количество
3. Скопируйте промпт в LLM (ChatGPT, Claude и т.д.)
4. Сохраните JSONL вывод в соответствующий файл
5. Опционально: используйте `prompts/self_check_prompt.md` для проверки
6. Запустите валидацию и сборку

### Пример создания нового набора

```bash
# Создайте файл для новой темы
touch Vocabulary/RU-TR/A1/003.jsonl

# Добавьте вопросы (используя редактор или LLM)
# Файлы с разными номерами нужны только для организации по темам
# При сборке все файлы уровня объединяются в один тест

# Валидация
python3 build_ma/validate_questions.py

# Сборка
python3 build_ma/build_site.py

# Или используйте единую команду
bash build_ma/build_ma.sh
```

## 🔍 Правила валидации

### Критические ошибки (строка удаляется)

- ❌ Отсутствие обязательных полей
- ❌ Неверный JSON
- ❌ Массив `tr` не содержит ровно 4 элемента
- ❌ Пустые варианты ответа

### Предупреждения (можно исправить)

- ⚠️ Дубликаты ID (должны быть уникальны глобально)
- ⚠️ Дубликаты вариантов в `tr` (после нормализации)
- ⚠️ Кириллица в турецких вариантах
- ⚠️ LLM мусор в тексте
- ⚠️ Неверный индекс `correct` (не 1-4)
- ⚠️ Пустое или плохое `explain_ru`

## 🎨 Frontend

### Технологии

- Чистый HTML/CSS/JavaScript (без фреймворков)
- Telegram WebApp API
- CloudStorage / localStorage

### Функции

- 📱 Адаптивный дизайн
- 🎲 Перемешивание вопросов и вариантов
- 💾 Сохранение прогресса (лучший результат, попытки)
- 📊 Статистика по завершении
- 💡 Объяснения после каждого ответа
- 📚 Автоматическое объединение всех вопросов уровня

### Интеграция с Telegram

```javascript
// Инициализация
if (window.Telegram && window.Telegram.WebApp) {
  const tg = window.Telegram.WebApp;
  tg.ready();
  tg.expand();
}

// Сохранение прогресса по уровню
await storage.set('quiz:ru-tr:a1', JSON.stringify({
  bestScore: 12,
  lastScore: 10,
  attempts: 3,
  lastAttemptAt: '2025-12-24T10:30:00Z'
}));
```

### CloudStorage ограничения

- Максимум ~1024 ключей
- Максимум ~4096 байт на значение
- Асинхронный API
- Fallback на localStorage для обычных браузеров

## 🛠️ Разработка

### Требования

- Python 3.7+
- Браузер с поддержкой ES6+
- (Опционально) Telegram Mini App для тестирования CloudStorage

### Зависимости

Проект использует только стандартную библиотеку Python. Зависимости не требуются.

Dev-зависимости (опционально):
- `ruff` — линтер/форматтер
- `pytest` — тестирование

### Скрипты

```bash
# Валидация
python3 build_ma/validate_questions.py

# Сборка
python3 build_ma/build_site.py

# Dev-сервер
python3 build_ma/dev_server.py

# Или встроенный HTTP-сервер Python
python3 -m http.server -d html/ma 8000
```

### Структура ассетов

- `html/ma/assets/app.css` — стили
- `html/ma/assets/app.js` — логика квиза
- `html/ma/assets/storage.js` — обёртка над CloudStorage/localStorage

## 📚 Примеры

### Пример вопроса A1

```json
{
  "id": "A1-001-0001",
  "ru": "Где находится остановка?",
  "tr": [
    "Durak nerede?",
    "Otobüs nerede?",
    "Burası neresi?",
    "Saat kaç?"
  ],
  "correct": 1,
  "explain_ru": "durak — остановка, nerede — где",
  "tags": ["transport", "location"],
  "source": "llm"
}
```

### Пример вопроса B1

```json
{
  "id": "B1-001-0001",
  "ru": "Если бы у меня было время, я бы пришёл",
  "tr": [
    "Vaktim olsaydı gelirdim",
    "Vaktim olursa gelirim",
    "Vaktim var geldim",
    "Vaktim olacak geleceğim"
  ],
  "correct": 1,
  "explain_ru": "vakit — время, olsaydı — если бы было, gelirdim — пришёл бы",
  "tags": ["conditional", "hypothetical"],
  "source": "llm"
}
```

## 📄 Лицензия

MIT (или укажите свою лицензию)

## 🤝 Контрибуция

1. Форкните репозиторий
2. Создайте ветку для фичи: `git checkout -b feature/new-questions`
3. Добавьте вопросы в JSONL
4. Запустите валидацию: `python3 build_ma/validate_questions.py`
5. Закоммитьте: `git commit -am 'Add new A2 questions'`
6. Запушьте: `git push origin feature/new-questions`
7. Создайте Pull Request

## ❓ FAQ

### Как изменить количество вопросов в квизе?

Откройте `build_ma/build_site.py`, найдите строку:
```python
questions = shuffleArray(allQuestions).slice(0, 15);
```
Измените `15` на нужное число.

### Как добавить новый уровень (например, B2)?

1. Создайте директорию: `Vocabulary/RU-TR/B2/`
2. Добавьте JSONL файлы с вопросами
3. Обновите `build_site.py`: добавьте `"B2"` в список уровней в функциях `find_jsonl_files()` и `generate_catalog_page()`
4. Запустите сборку: `bash build_ma/build_ma.sh`

### Как работает перемешивание ответов?

В `app.js` варианты перемешиваются, и индекс `correct` пересчитывается:
```javascript
const shuffled = shuffleArray(variants);
const newCorrectIndex = shuffled.indexOf(correctAnswer) + 1;
```

### Можно ли использовать без Telegram?

Да! Приложение работает как обычный веб-сайт. CloudStorage недоступен, используется localStorage.

## 📞 Поддержка

Если нашли баг или есть предложение — создайте Issue на GitHub.

---

**Приятного изучения турецкого! 🇹🇷**
