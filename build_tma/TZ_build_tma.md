# ТЗ: Скрипт сборки контента для Telegram Mini App

## 0. Контекст и цель

В репозитории есть каталог `Courses/` с курсами в Markdown. Требуется скрипт, который компилирует содержимое `Courses/` в набор статических файлов в `tma/`, пригодных для использования Telegram Mini App (Web App).

- Источник: `Courses/`
- Код скрипта: `build_tma/`
- Выход: `tma/`
- Деплой выполняется отдельно (например, `rsync`), в рамках данного ТЗ не требуется.

## 1. Входная структура (source)

Исходная структура курсов (строго):

```
Courses/
└── [CourseName]/
    ├── 01_ModuleName/
    │   ├── lecture.md
    │   └── quiz.md
    ├── 02_ModuleName/
    │   ├── lecture.md
    │   └── quiz.md
    └── ...
```

Требования:
- `[CourseName]` — имя каталога курса (уникально).
- Модуль — каталог с префиксом `NN_`, где `NN` — двузначный номер (`01`..`99`), далее произвольное имя `ModuleName`.
- В модуле:
  - `lecture.md` — **обязателен**
  - `quiz.md` — **опционален** (скрипт должен поддерживать модули без квиза)

## 2. Метаданные

Скрипт обязан поддерживать YAML front-matter в начале `lecture.md` и `quiz.md` (если есть). Front-matter имеет приоритет над выводом из структуры папок.

Пример front-matter:

```md
---
title: "Файлы и кодировки"
duration_min: 12
tags: ["linux", "encoding"]
---
# Контент...
```

Если front-matter отсутствует:
- `title` лекции берётся из первого заголовка `# ...` (если есть), иначе из имени модуля.
- `course_title` берётся из имени каталога курса (`CourseName`), преобразованного в человекочитаемый вид (underscore/defis -> пробелы).

## 3. Правила slug и идентификаторов

### 3.1. `course_id` (course_slug)
Формируется из имени каталога курса `[CourseName]`:
- lowercase
- пробелы/`_` -> `-`
- удалить всё кроме `[a-z0-9-]`
- повторяющиеся `--` схлопнуть
- обрезать `-` по краям

### 3.2. `module_id` (module_slug)
Формируется из части имени каталога модуля после `NN_` по тем же правилам slug.

### 3.3. Уникальность
- `course_id` должен быть уникальным среди курсов
- `module_id` уникален внутри курса
- при конфликте `module_id` скрипт должен автоматически добавить суффикс `-2`, `-3` и т.д., и залогировать предупреждение

## 4. Выходная структура (output)

Скрипт генерирует структуру `tma/`:

```
tma/
└── content/
    ├── index.json
    ├── build-report.json
    └── courses/
        └── <course_id>/
            ├── course.json
            ├── modules.json
            └── modules/
                └── <module_id>/
                    ├── lecture.json
                    └── quiz.json   (если квиз существует)
```

В рамках ТЗ **не требуется** генерировать `index.html`, `app.js`, `css` и т.д. (оболочка mini app лежит отдельно). Требуется только контент и индексы в `tma/content/...`.

Все ссылки внутри JSON должны быть **относительными** (relative URLs) от корня `tma/`.

## 5. Формат лекции и квиза

### 5.1. Лекция: `lecture.json` (обязательный формат)
Скрипт должен сохранять исходный Markdown лекции в поле `markdown`. Рендеринг Markdown в HTML выполняется на стороне mini app.

### 5.2. Квиз: `quiz.json`
`quiz.md` должен компилироваться в JSON по правилам парсинга (см. раздел 8).

## 6. Точная JSON-схема (Schema)

Все схемы ниже — **нормативные**. Выходные JSON должны соответствовать этим схемам.

### 6.1. `tma/content/index.json`
Назначение: быстрый общий индекс (курсы и ссылки на детали).

```json
{
  "schema_version": 1,
  "build": {
    "timestamp_utc": "2025-12-18T10:00:00Z",
    "git_commit": "abc123",
    "generator": "build_tma"
  },
  "courses": [
    {
      "course_id": "linux-basics",
      "title": "Linux Basics",
      "modules_count": 12,
      "url_course": "content/courses/linux-basics/course.json",
      "url_modules": "content/courses/linux-basics/modules.json"
    }
  ]
}
```

**Требования к полям:**
- `schema_version`: int, фиксировано `1`
- `build.timestamp_utc`: строка ISO-8601 UTC с `Z`
- `build.git_commit`: строка (может быть пустой, если git недоступен)
- `build.generator`: строка, фиксировано `"build_tma"`
- `courses`: массив, отсортирован по `title` (или по `course_id` — выбрать и зафиксировать; предпочтительно `title`)
- `url_*`: относительные пути

### 6.2. `tma/content/courses/<course_id>/course.json`
Назначение: мета-информация о курсе.

```json
{
  "schema_version": 1,
  "course_id": "linux-basics",
  "title": "Linux Basics",
  "description": "Короткое описание курса (если есть)",
  "tags": ["linux", "cli"],
  "source_path": "Courses/Linux_Basics",
  "modules_count": 12,
  "url_modules": "content/courses/linux-basics/modules.json"
}
```

**Требования:**
- `description`, `tags` могут отсутствовать или быть пустыми
- `source_path` — относительный путь внутри репозитория, для дебага/репортов

### 6.3. `tma/content/courses/<course_id>/modules.json`
Назначение: список модулей курса с ссылками на лекции/квизы.

```json
{
  "schema_version": 1,
  "course_id": "linux-basics",
  "modules": [
    {
      "module_no": 1,
      "module_id": "files-and-encodings",
      "title": "Files and Encodings",
      "has_quiz": true,
      "duration_min": 12,
      "tags": ["encoding"],
      "url_lecture": "content/courses/linux-basics/modules/files-and-encodings/lecture.json",
      "url_quiz": "content/courses/linux-basics/modules/files-and-encodings/quiz.json"
    }
  ]
}
```

**Требования:**
- `modules` отсортирован строго по `module_no` (возрастание)
- `has_quiz`: bool
- если `has_quiz=false`, `url_quiz` **не должен** присутствовать (или должен быть `null` — выбрать один вариант; в данном ТЗ: **НЕ должен присутствовать**)

### 6.4. `tma/content/courses/<course_id>/modules/<module_id>/lecture.json`
Назначение: лекция.

```json
{
  "schema_version": 1,
  "course_id": "linux-basics",
  "module_no": 1,
  "module_id": "files-and-encodings",
  "title": "Файлы и кодировки",
  "duration_min": 12,
  "tags": ["linux", "encoding"],
  "markdown": "# ... исходный markdown ...",
  "anchors": [
    { "id": "utf-8", "text": "UTF-8" }
  ],
  "source": {
    "path": "Courses/Linux_Basics/01_Files/lecture.md",
    "sha256": "..."
  }
}
```

**Требования:**
- `markdown` — строка, исходный текст лекции без изменений (кроме возможного удаления front-matter)
- `anchors` — опционально. Если реализуется: список заголовков (например, `#`, `##`, `###`) с рассчитанным `id` (slug заголовка).
- `source.sha256` — sha256 содержимого исходника (после нормализации конца строк — см. раздел 7)

### 6.5. `tma/content/courses/<course_id>/modules/<module_id>/quiz.json`
Назначение: квиз.

```json
{
  "schema_version": 1,
  "course_id": "linux-basics",
  "module_no": 1,
  "module_id": "files-and-encodings",
  "title": "Квиз: Файлы и кодировки",
  "questions": [
    {
      "id": "q1",
      "type": "single",
      "prompt": "Что такое UTF-8?",
      "options": [
        { "id": "a", "text": "Кодировка Unicode переменной длины", "correct": true },
        { "id": "b", "text": "Формат сжатия", "correct": false },
        { "id": "c", "text": "Протокол сети", "correct": false }
      ],
      "explanation": "UTF-8 кодирует Unicode кодпоинты в 1–4 байта."
    }
  ],
  "source": {
    "path": "Courses/Linux_Basics/01_Files/quiz.md",
    "sha256": "..."
  }
}
```

**Требования:**
- `questions[].id`: строка, уникальная в пределах квиза (`q1`, `q2`, ...)
- `type`: `"single"` или `"multi"`
- `options[].id`: короткие id (`a`, `b`, `c`, ...) по порядку
- `correct` обязателен в выходном JSON (mini app может скрывать это поле для UI, но данные должны быть полными)
- `explanation` опционален

### 6.6. `tma/content/build-report.json`
Назначение: отчёт о сборке (для CI и диагностики).

```json
{
  "schema_version": 1,
  "build": {
    "timestamp_utc": "2025-12-18T10:00:00Z",
    "git_commit": "abc123",
    "generator": "build_tma"
  },
  "stats": {
    "courses_total": 3,
    "modules_total": 48,
    "lectures_total": 48,
    "quizzes_total": 40,
    "warnings_total": 2,
    "errors_total": 0
  },
  "warnings": [
    {
      "code": "MODULE_SLUG_CONFLICT",
      "path": "Courses/X/02_SameName",
      "message": "module_id conflict resolved with suffix '-2'"
    }
  ],
  "errors": []
}
```

**Требования:**
- при `--strict` наличие `errors_total>0` должно приводить к exit code `2`
- `warnings` не валят сборку

## 7. Нормализация текста и хеши

Для стабильности сборок:
- при чтении файлов нормализовать окончания строк к `\\n`
- `sha256` считать по нормализованному содержимому
- front-matter (если есть) исключать из `markdown`, но sha считать по **полностью исходному** файлу (после нормализации), чтобы изменения метаданных тоже меняли sha

## 8. Парсинг `quiz.md` (норматив)

Скрипт обязан поддерживать следующий формат вопросов в `quiz.md`:

- Вопрос начинается с заголовка `###`
- Варианты ответов — markdown список:
  - `- [x] ...` — правильный ответ
  - `- [ ] ...` — неправильный
- Если правильных вариантов несколько → `type="multi"`, если один → `type="single"`
- Пояснение (опционально):
  - строка, начинающаяся с `**Explanation:**`
  - либо blockquote `> Explanation: ...` (одной строкой или несколькими)

Пример:

```md
### Что такое UTF-8?
- [x] Кодировка Unicode переменной длины
- [ ] Формат сжатия
- [ ] Протокол сети

**Explanation:** UTF-8 кодирует Unicode кодпоинты в 1–4 байта.
```

Ошибки парсинга (в строгом режиме = fail):
- вопрос без вариантов
- варианты без `[x]` (нет правильных)
- некорректная разметка чекбоксов

## 9. Валидации

Скрипт должен проверять:

- В каждом модуле существует `lecture.md`
- Каталоги модулей соответствуют `^\\d{2}_.+`
- Номера модулей уникальны внутри курса
- JSON, который генерируется, соответствует схемам из раздела 6
- Все `url_*` указывают на реально сгенерированные файлы

## 10. CLI и поведение

Скрипт реализовать на Python 3 и разместить в `build_tma/`.

### 10.1 Запуск

```bash
python3 build_tma/build.py --src Courses --out tma
```

### 10.2 Аргументы

Обязательные:
- `--src` (default: `Courses`)
- `--out` (default: `tma`)

Опциональные:
- `--clean` (удалить `tma/content` перед сборкой)
- `--strict` (default) / `--lenient`
- `--course <course_id>` (собрать только один курс)
- `--emit-anchors` (генерировать anchors из заголовков)
- `--no-timestamp` (для детерминированных билдов в CI)

### 10.3 Exit codes
- `0` — успех
- `2` — контент-ошибки/валидация (например, нет `lecture.md` или не распарсился квиз)
- `1` — ошибка выполнения/исключение

## 11. Логи

Скрипт должен печатать:
- что собирается (курсы, модули)
- статистику (сколько лекций/квизов)
- список warnings/errors в конце
- путь к главному индексу: `tma/content/index.json`

## 12. Примеры поведения

### 12.1 Модуль без `quiz.md`
- `has_quiz=false`
- `quiz.json` не генерируется
- `url_quiz` отсутствует

### 12.2 Некорректный `quiz.md` в `strict`
- сборка падает, exit code `2`
- ошибка добавляется в `build-report.json`

### 12.3 Некорректный `quiz.md` в `lenient`
- модуль собирается без квиза (`has_quiz=false`)
- warning добавляется в `build-report.json`
