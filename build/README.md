# Build MA (Mini App) — RU→TR Vocabulary Quiz

Telegram Mini App для изучения турецкого языка через тесты на перевод с русского на турецкий.

## 🎯 О проекте

Статический веб-сайт с квизами в стиле викторины:
- Три категории: **Слова** (Words), **Фразы** (Phrases), **Грамматика** (Grammar)
- Три уровня: **A1**, **A2**, **B1**
- По 5 случайных вопросов из базы выбранного уровня
- Результаты с объяснениями после каждого ответа
- Прогресс сохраняется в Telegram CloudStorage (с fallback на localStorage)

Все JSONL файлы одного уровня автоматически объединяются в один тест.

---

## 🚀 Быстрый старт

```bash
# Полная сборка с валидацией
./build/build_ma.sh

# Локальный сервер для тестирования
python3 build/dev_server.py
# Откройте: http://localhost:8000
```

---

## 📁 Структура проекта

```
tma/
├── build/                         # Скрипты сборки и управления
│   ├── build_ma.sh               # Главный скрипт сборки
│   ├── build_site.py             # Главный оркестратор (точка входа)
│   ├── builder.py                # Класс SiteBuilder - логика сборки
│   ├── template_engine.py        # Класс TemplateEngine - рендеринг шаблонов
│   ├── templates/                # Шаблоны HTML/CSS/JS
│   │   ├── quiz_page.html        # Шаблон страницы квиза
│   │   ├── catalog_page.html     # Шаблон каталога
│   │   ├── app.css               # Стили приложения
│   │   ├── app.js                # JavaScript квиза
│   │   └── storage.js            # Обертка для Telegram CloudStorage
│   ├── manage_vocabulary.py      # Управление данными (валидация, дедупликация, балансировка)
│   ├── dev_server.py             # Локальный HTTP-сервер
│   ├── validate_html.py          # Проверка HTML
│   └── requirements.txt          # Python зависимости
├── data/                          # Исходные данные
│   ├── config.json               # Конфигурация курсов, типов контента, уровней
│   ├── School/                   # Данные для школьного курса
│   │   ├── English/
│   │   └── Maths/
│   └── Turk/                     # Данные для турецкого языка (RU→TR)
│       ├── generate_grammar_prompt.md
│       ├── generate_questions_prompt.md
│       ├── generate_words_prompt.md
│       ├── self_check_prompt.md
│       ├── RU-TR_Words/          # Словарные записи
│       │   ├── A1/ (001.jsonl, 002.jsonl, ...)
│       │   ├── A2/
│       │   └── B1/
│       ├── RU-TR_Phrases/        # Фразы
│       │   ├── A1/
│       │   ├── A2/
│       │   └── B1/
│       └── RU-TR_Grammar/        # Грамматические вопросы
│           ├── A1/
│           ├── A2/
│           └── B1/
└── html/                          # Собранные статические сайты (output)
    ├── ma/                        # Курс "ma" (турецкий язык)
    │   ├── index.html             # Главная страница (каталог)
    │   ├── assets/
    │   │   ├── app.css
    │   │   ├── app.js
    │   │   └── storage.js
    │   ├── RU-TR_Words/
    │   │   ├── A1/ (index.html, questions.json)
    │   │   ├── A2/
    │   │   └── B1/
    │   ├── RU-TR_Phrases/
    │   │   └── ...
    │   └── RU-TR_Grammar/
    │       └── ...
    └── test/                      # Тестовый курс
        └── ...
```

---

## 🛠️ Основные скрипты

### Сборка

- **build_ma.sh** — Главный скрипт сборки. Выполняет валидацию, генерацию и проверку HTML.
- **build_site.py** — Главный оркестратор (точка входа). Использует конфигурацию из `data/config.json`.
- **builder.py** — Класс SiteBuilder с логикой сборки статического сайта из JSONL файлов.
- **template_engine.py** — Класс TemplateEngine для рендеринга шаблонов с помощью Jinja2.

### Управление данными

- **manage_vocabulary.py** — Универсальный инструмент для работы с Vocabulary
  - Валидация формата вопросов
  - Валидация словарных записей
  - Балансировка распределения ответов
  - Удаление дубликатов
  - **По умолчанию** (без аргументов) выполняет все проверки и исправления

### Утилиты

- **dev_server.py** — Локальный HTTP-сервер для тестирования
- **validate_html.py** — Проверка корректности сгенерированного HTML

---

## 📝 Управление данными

### Автоматическая проверка и исправление

```bash
# По умолчанию: валидация + балансировка + дедупликация
./build/manage_vocabulary.py

# Или конкретные команды:
./build/manage_vocabulary.py validate-questions  # Только валидация
./build/manage_vocabulary.py shuffle             # Только балансировка
./build/manage_vocabulary.py remove-duplicates   # Только дедупликация
./build/manage_vocabulary.py fix-all             # Всё сразу
```

### Что проверяется

**validate-questions** — проверяет все JSONL файлы:
- ✅ Корректность JSON
- ✅ Наличие обязательных полей: `id`, `question`, `options`, `correct`, `explanation`
- ✅ Уникальность ID (в пределах категории)
- ✅ Ровно 4 варианта ответа (все уникальные)
- ✅ Отсутствие кириллицы в турецких вариантах
- ✅ Отсутствие LLM-мусора ("правильный ответ", "as an AI")
- ✅ Корректное поле `explanation` с разделителями

**validate-words** — дополнительная проверка для RU-TR_Words:
- ✅ ID в формате `{LEVEL}-{SET}-{NUM}` (например, `A1-001-0001`)
- ⚠️ Русское слово должно быть одним словом (предупреждение)
- ✅ Консистентность: русское слово в `explanation`

**shuffle** — балансирует распределение правильных ответов:
- Проверяет распределение вариантов 1, 2, 3, 4
- Если отклонение от 25% > 5% (т.е. <20% или >30%), перемешивает варианты

**remove-duplicates** — удаляет дубликаты:
- Сравнивает нормализованный текст поля `question`
- Сохраняет первое вхождение, удаляет последующие

---

## 📝 Формат JSONL

Каждая строка в JSONL файле = один JSON объект вопроса.

### Обязательные поля

```json
{
  "id": "A1-001-0001",
  "question": "Где находится остановка?",
  "options": [
    "Durak nerede?",
    "Otobüs nerede?",
    "Burası neresi?",
    "Saat kaç?"
  ],
  "correct": 1,
  "explanation": "durak — остановка, nerede — где"
}
```

- **id**: Уникальный идентификатор в формате `<LEVEL>-<SET>-<NUM>`
  - Пример: `A1-001-0001`, `A2-003-0015`, `B1-002-0008`
- **question**: Текст на русском языке (слово/фраза/предложение)
- **options**: Массив из **ровно 4** вариантов перевода на турецкий
  - Только **один** правильный
  - Остальные 3 — правдоподобные дистракторы
- **correct**: Номер правильного варианта (1, 2, 3 или 4)
- **explanation**: Объяснение с базовыми формами турецких слов
  - Формат: `<слово> — <перевод>, <слово> — <перевод>`

### Опциональные поля

```json
{
  "tags": ["transport", "location"],
  "source": "llm"
}
```

---

## ➕ Добавление новых вопросов

### Вручную

1. Создайте или откройте JSONL файл в `data/Turk/RU-TR_{Words,Phrases,Grammar}/<LEVEL>/`
2. Добавьте строки с вопросами (каждая строка = один JSON объект)
3. Запустите: `./build/manage_vocabulary.py` (автоматическая проверка и исправление)
4. Соберите сайт: `./build/build_ma.sh`

**Примечание**: Все JSONL файлы одного уровня автоматически объединяются в один тест.

### С помощью LLM

1. Откройте промпт из `data/Turk/`:
   - `generate_words_prompt.md` — для слов
   - `generate_questions_prompt.md` — для фраз
   - `generate_grammar_prompt.md` — для грамматики
2. Укажите параметры: уровень, набор, темы, количество
3. Скопируйте промпт в LLM (ChatGPT, Claude и т.д.)
4. Сохраните JSONL вывод в соответствующий файл
5. Опционально: используйте `self_check_prompt.md` для проверки
6. Запустите: `./build/build_ma.sh`

---

## 🎨 Frontend

### Технологии

- Чистый HTML/CSS/JavaScript (без фреймворков)
- Telegram WebApp API
- CloudStorage / localStorage

### Функции

- 📱 Адаптивный дизайн (мобильный и десктоп)
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

// Сохранение прогресса
await storage.set('quiz:ru-tr-words:a1', JSON.stringify({
  bestScore: 4,
  lastScore: 3,
  attempts: 2,
  lastAttemptAt: '2025-12-25T10:30:00Z'
}));
```

---

## 🔍 Примеры вопросов

### Слова (Words) — A1

```json
{
  "id": "A1-001-0001",
  "question": "собака",
  "options": ["köpek", "kedi", "kuş", "balık"],
  "correct": 1,
  "explanation": "köpek — собака",
  "tags": ["animals"]
}
```

### Фразы (Phrases) — A1

```json
{
  "id": "A1-003-0001",
  "question": "Где находится остановка?",
  "options": ["Durak nerede?", "Otobüs nerede?", "Burası neresi?", "Saat kaç?"],
  "correct": 1,
  "explanation": "durak — остановка, nerede — где",
  "tags": ["transport", "location"]
}
```

### Грамматика (Grammar) — B1

```json
{
  "id": "B1-001-0001",
  "question": "Если бы у меня было время, я бы пришёл",
  "options": [
    "Vaktim olsaydı gelirdim",
    "Vaktim olursa gelirim",
    "Vaktim var geldim",
    "Vaktim olacak geleceğim"
  ],
  "correct": 1,
  "explanation": "vakit — время, olsaydı — если бы было, gelirdim — пришёл бы",
  "tags": ["conditional", "hypothetical"]
}
```

---

## ❓ FAQ

### Как изменить количество вопросов в квизе?

Откройте `build/builder.py`, найдите метод `_build_quiz_page()` и измените параметр `quiz_length`:
```python
html_content = self.template_engine.render_quiz_page(
    quiz_length=5,  # Измените на нужное число
    ...
)
```
Пересоберите: `./build/build_ma.sh`

### Как добавить новый уровень (например, B2)?

1. Создайте директории: `data/Turk/RU-TR_{Words,Phrases,Grammar}/B2/`
2. Добавьте JSONL файлы с вопросами
3. Обновите `data/config.json`: добавьте `"B2"` в `levels` для нужных типов контента
4. Запустите сборку: `./build/build_ma.sh`

### Как работает перемешивание ответов?

В `app.js` варианты перемешиваются перед показом, и индекс `correct` пересчитывается:
```javascript
const shuffled = shuffleArray(variants);
const newCorrectIndex = shuffled.indexOf(correctAnswer);
```

### Можно ли использовать без Telegram?

Да! Приложение работает как обычный веб-сайт. CloudStorage недоступен, используется localStorage.

### Где хранятся результаты?

- В Telegram: CloudStorage (ключ: `quiz:ru-tr-{category}:{level}`)
- В браузере: localStorage
- Формат: JSON с полями `bestScore`, `lastScore`, `attempts`, `lastAttemptAt`

---

## 🛠️ Разработка

### Требования

- Python 3.7+
- Браузер с поддержкой ES6+
- (Опционально) Telegram Mini App для тестирования CloudStorage

### Зависимости

Проект использует только стандартную библиотеку Python. Внешние зависимости не требуются.

### Скрипты разработки

```bash
# Валидация данных
./build/manage_vocabulary.py

# Сборка сайта
python3 build/build_site.py

# Dev-сервер
python3 build/dev_server.py

# Полная сборка (валидация + генерация + проверка HTML)
./build/build_ma.sh

# Или встроенный HTTP-сервер Python
python3 -m http.server -d html/ma 8000
```

---

## 📚 История изменений

### 27 декабря 2024 — Рефакторинг системы сборки

**Модульная архитектура:**
- Старый монолитный `build_site.py` (1915 строк) разделён на:
  - `build_site.py` — точка входа (44 строки)
  - `builder.py` — класс SiteBuilder с логикой сборки
  - `template_engine.py` — рендеринг шаблонов через Jinja2
  - `templates/` — шаблоны HTML/CSS/JS в отдельных файлах

**Унификация формата данных:**
- Формат JSONL обновлён: `ru` → `question`, `tr` → `options`, `explain_ru` → `explanation`
- Все данные конвертированы в новый формат

**Удалены устаревшие файлы:**
- `build_site_old.py` — старая версия после рефакторинга
- `convert_quiz_format.py` — скрипт конвертации (больше не нужен)

**Централизация конфигурации:**
- Вся конфигурация курсов в `data/config.json`
- Метаданные курсов, типов контента, уровней и настроек квизов

**Результат:**
- Более модульный и поддерживаемый код
- Шаблоны с подсветкой синтаксиса в VS Code
- Универсальный `manage_vocabulary.py` для всех операций с данными

### 25 декабря 2024 — Объединение инструментов

**Объединены скрипты управления данными:**
- Создан универсальный `manage_vocabulary.py`
- Удалены: `validate_questions.py`, `validate_vocabulary.py`, `shuffle_answers.py`, `remove_duplicates.py`
- Удалены устаревшие: `generate_ma.py`, `index.html` (шаблон)

**Объединена документация:**
- `README.md` и `README_VOCABULARY_QUIZ.md` → один `README.md`

---

## 🤝 Контрибуция

1. Форкните репозиторий
2. Создайте ветку: `git checkout -b feature/new-questions`
3. Добавьте вопросы в JSONL
4. Запустите: `./build_ma/manage_vocabulary.py`
5. Закоммитьте: `git commit -am 'Add new A2 questions'`
6. Запушьте: `git push origin feature/new-questions`
7. Создайте Pull Request

---

**Приятного изучения турецкого! 🇹🇷**
