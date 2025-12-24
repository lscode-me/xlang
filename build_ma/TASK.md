Сгенерируй полностью рабочий репозиторий для Telegram Mini App (статический сайт) “RU→TR Vocabulary Quiz” (5–20 вопросов) в стиле “Кто хочет стать миллионером”.

СТРУКТУРА РЕПО (строго)
- build_ma/                  # скрипты сборки/валидации
- html/ma/                   # destination собранных файлов (output, статика)
- Vocabulary/RU-TR/A1/       # наборы jsonl
- Vocabulary/RU-TR/A2/
- Vocabulary/RU-TR/B1/

ВХОДНЫЕ ДАННЫЕ (JSONL)
В каждом файле Vocabulary/RU-TR/<LEVEL>/<SET>.jsonl:
- 1 строка = 1 JSON object
- обязательные поля:
  - id: string, уникальный во всем репо
  - ru: string (фраза на русском)
  - tr: array[string] длины 4 (варианты на турецком)
  - correct: integer 1..4 (номер правильного варианта)
  - explain_ru: string (словарный разбор, базовая форма/инфинитив с TR на RU)
- опционально: tags: array[string], source: string

ПРИМЕР ОДНОЙ СТРОКИ JSONL (без переносов)
{"id":"A1-001-0001","ru":"Где находится остановка?","tr":["Durak nerede?","Otobüs nerede?","Burası neresi?","Saat kaç?"],"correct":1,"explain_ru":"durak — остановка; nerede — где","tags":["A1","transport"],"source":"llm"}

ЦЕЛЬ
1) build_ma/validate_questions.py:
   - рекурсивно проходит Vocabulary/RU-TR/{A1,A2,B1}/**/*.jsonl
   - проверяет формат и контент:
     * строка валидный JSON объект
     * обязательные поля есть
     * tr — массив из 4 непустых строк
     * correct — int 1..4
     * id уникален глобально
     * варианты tr уникальны после нормализации (trim, lower, collapse spaces)
     * в tr нет кириллицы
     * нет мусорных маркеров LLM (“Правильный ответ”, “вариант 1”, “As an AI”, “ChatGPT”)
     * explain_ru не пустой и содержит хотя бы один разделитель перевода (“—” или “-”)
   - печатает отчет с указанием файла и номера строки
   - exit code 1 при ошибках

2) build_ma/build_site.py:
   - запускает validate (или импортирует общий модуль)
   - генерирует html/ma/ целиком (очищая старое содержимое, кроме .gitkeep если будет)
   - создает:
     - html/ma/index.html — каталог уровней и наборов
     - html/ma/RU-TR/<LEVEL>/<SET>/index.html — страница квиза
     - html/ma/RU-TR/<LEVEL>/<SET>/questions.json — вопросы для этого квиза
     - html/ma/assets/app.css, app.js, storage.js
   - index.html должен показывать список уровней (A1/A2/B1), под каждым — наборы по имени файла

3) Frontend (чистый HTML/CSS/JS, без бэкенда):
   - посмотри index.html
   - quiz UI:
     - заголовок: “Выбери правильный перевод:”
     - затем RU фраза
     - 4 кнопки A/B/C/D с TR вариантами
     - подсветка correct/wrong
     - прогресс-бар и счет
     - финальный экран с результатом
     - “Сыграть ещё”
   - перемешивание:
     - перемешивать порядок вопросов
     - опционально перемешивать варианты ответа (если перемешиваешь — не забудь корректно переносить correct)
   - 15 вопросов и после этого результаты
   - загрузка вопросов: fetch("./questions.json")
   - интеграция Telegram:
     - если window.Telegram.WebApp есть: tg.ready(); tg.expand();
     - прогресс хранить через CloudStorage с fallback localStorage
     - ключ прогресса: "quiz:ru-tr:<level>:<set>" (lowercase)
     - значение JSON: {bestScore,lastScore,attempts,lastAttemptAt}
   - storage.js:
     - async get(key), set(key,value)
     - CloudStorage.getItem/setItem если доступен
     - иначе localStorage

4) Добавь build_ma/dev_server.py (опционально) или README, как запустить:
   - python3 -m http.server -d html/ma 8000

5) Добавь prompts/:
   - prompts/generate_questions_prompt.md:
     * промпт для LLM который генерирует ТОЛЬКО JSONL строки (без оберток, без комментариев)
     * строго поля id/ru/tr/correct/explain_ru (+tags/source опционально)
     * корректный турецкий A1/A2/B1 по уровню
     * 4 TR варианта должны быть правдоподобными, но только 1 правильный перевод
     * explain_ru — словарные формы (инфинитив/базовая) TR слов + перевод
   - prompts/self_check_prompt.md:
     * промпт для LLM который берет JSONL и возвращает исправленный JSONL, устраняя дубли, кириллицу в tr, неверный correct, пустые поля

6) Демо-контент:
   - Создай минимум:
     - Vocabulary/RU-TR/A1/001.jsonl (5 вопросов)
     - Vocabulary/RU-TR/A1/002.jsonl (5 вопросов)
     - Vocabulary/RU-TR/A2/001.jsonl (5 вопросов)
     - Vocabulary/RU-TR/B1/001.jsonl (5 вопросов)
   - Вопросы в формате RU → выбор TR перевода, темы бытовые (дом, город, еда, время, просьбы), без сложной лексики

7) Python стиль:
   - в каждом py: #!/usr/bin/env python3 и if __name__ == "__main__": main()
   - без тяжелых зависимостей (только stdlib); можно добавить ruff/pytest как dev-зависимости, но проект должен работать без них

8) README.md:
   - как добавить новый набор jsonl
   - как прогнать validate
   - как собрать сайт
   - как открыть локально
   - заметки про Telegram CloudStorage ограничения и fallback localStorage

СГЕНЕРИРУЙ ВСЕ ФАЙЛЫ СРАЗУ. ПИШИ КОД ПОЛНОСТЬЮ, БЕЗ “заглушек”.

