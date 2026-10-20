# Промпт для генерации грамматических вопросов RU→EN Quiz (Grammar)

Ты - эксперт по английскому языку и создатель учебных материалов. Твоя задача - генерировать вопросы для теста на **грамматику** английского языка.

## Формат вывода

Генерируй ТОЛЬКО JSONL (JSON Lines) - каждая строка = один валидный JSON объект.

**НЕ ДОБАВЛЯЙ**:
- Никаких markdown блоков кода (```json)
- Никаких комментариев
- Никаких пояснений
- Только чистые JSONL строки

## Структура каждого JSON объекта

```json
{"id":"<LEVEL>-<KEY>-<NUM>","question":"<Russian phrase>","options":["<Option 1>","<Option 2>","<Option 3>","<Option 4>"],"correct":<1-4>,"explanation":"<Explanation>","tags":["<tag1>","<tag2>"],"source":"llm"}
```

## Обязательные поля

- **id**: Уникальный идентификатор в формате `<LEVEL>-<KEY>-<NUM>`
  - Примеры: `A1-GRAM-0001`, `A2-TENSE-0023`
  - LEVEL: A1 или A2
  - KEY: Код темы (например, GRAM, TENSE, ARTICLES, PREP) или номер набора (001)
  - NUM: четырёхзначный порядковый номер

- **question**: Фраза или предложение на русском языке
  - Четко иллюстрирует определенное грамматическое правило (время, артикли, предлоги, порядок слов и т.д.)
  - Примеры: "Я **иду** в школу" (настоящее время), "Это **яблоко**" (артикли)

- **options**: Массив из **ровно 4** вариантов перевода на английский
  - **ВАЖНО**: Все 4 варианта должны быть **одним и тем же предложением**, отличающимся ТОЛЬКО грамматической формой.
  - Используй одну и ту же лексику (те же корни слов).
  - Меняй только грамматические элементы (времена, артикли, предлоги, порядок слов, формы глаголов).
  - Только **ОДИН** вариант - правильный перевод.
  - Остальные 3 - неправильные формы (другое время, другой артикль, неправильный предлог).
  - Варианты должны быть сами по себе грамматически возможными (реальные слова), но неверными по смыслу перевода.

- **correct**: Номер правильного варианта (1, 2, 3, или 4)
  - Индексация с 1.

- **explanation**: Объяснение грамматики на русском
  - Объясни, почему выбран именно эта грамматическая форма.
  - Укажи название времени, правила использования артикля, предлога и т.д.
  - Пример: `"Я иду (регулярное действие) — Present Simple. I go to school."`
  - Пример: `"Вчера (прошлое) — Past Simple. I went yesterday."`

## Опциональные поля

- **tags**: Массив строк (темы грамматики)
  - Примеры: `["grammar", "present_simple"]`, `["tenses", "past"]`, `["articles"]`
  
- **source**: `"llm"`

## Требования по грамматике и уровням

### A1 (Базовая грамматика)
- **Present Simple** (настоящее простое время)
  - *Пример:* I go, You go, He/She/It goes, We go, They go
- **Present Continuous** (настоящее длительное время)
  - *Пример:* I am going, You are going, He/She/It is going
- **Артикли**: a/an (неопределенный), the (определенный)
  - *Пример:* a book, an apple, the book
- **Множественное число** (-s/-es)
  - *Пример:* books, apples, boxes
- **Притяжательные местоимения**: my, your, his, her, our, their
- **Предлоги места**: in, on, at, under, next to
- **Вопросительные слова**: what, where, when, who, how
- **Отрицание**: don't, doesn't, isn't, aren't
- **There is / There are**

### A2 (Элементарная грамматика)
- **Past Simple** (прошедшее простое время)
  - *Пример:* I went, You went, He/She/It went
- **Past Continuous** (прошедшее длительное время)
  - *Пример:* I was going, You were going
- **Future Simple** (будущее простое время)
  - *Пример:* I will go, I am going to go
- **Present Perfect** (настоящее совершенное время)
  - *Пример:* I have gone, He has gone
- **Степени сравнения прилагательных**: big - bigger - biggest, good - better - best
- **Модальные глаголы**: can, could, should, must, may
- **Предлоги времени**: in, on, at, for, since
- **Условные предложения** (1st conditional): If I go, I will...
- **Счетные и несчетные существительные**: many/much, few/little

## Примеры (Grammar Focus)

### Пример A1 (Времена - Present Simple):
```json
{"id":"A1-GRAM-0001","question":"Я хожу в школу каждый день","options":["I go to school every day","I am going to school every day","I went to school every day","I will go to school every day"],"correct":1,"explanation":"Каждый день (регулярное действие) — Present Simple. I go (не I am going — это Present Continuous для действия сейчас).","tags":["grammar","present_simple"],"source":"llm"}
```

### Пример A1 (Артикли):
```json
{"id":"A1-GRAM-0002","question":"Это яблоко","options":["This is an apple","This is a apple","This is the apple","This is apple"],"correct":1,"explanation":"Яблоко начинается с гласной (apple) — нужен артикль 'an'. 'A' для согласных, 'the' для определенного предмета.","tags":["grammar","articles"],"source":"llm"}
```

### Пример A1 (Предлоги места):
```json
{"id":"A1-GRAM-0003","question":"Книга на столе","options":["The book is on the table","The book is in the table","The book is at the table","The book is under the table"],"correct":1,"explanation":"На столе (поверхность) — предлог 'on'. 'In' — внутри, 'at' — у/около, 'under' — под.","tags":["grammar","prepositions"],"source":"llm"}
```

### Пример A2 (Времена - Past Simple):
```json
{"id":"A2-GRAM-0010","question":"Вчера я пришел домой","options":["Yesterday I came home","Yesterday I come home","Yesterday I am coming home","Yesterday I will come home"],"correct":1,"explanation":"Вчера (yesterday) требует Past Simple. Came (неправильная форма от come). Come — настоящее, coming — длительное, will come — будущее.","tags":["grammar","tenses","past_simple"],"source":"llm"}
```

### Пример A2 (Present Perfect):
```json
{"id":"A2-GRAM-0015","question":"Я уже сделал домашнее задание","options":["I have already done my homework","I did already my homework","I am already doing my homework","I will already do my homework"],"correct":1,"explanation":"Уже (already) + результат — Present Perfect. Have done (не did — это Past Simple).","tags":["grammar","present_perfect"],"source":"llm"}
```

### Пример A1 (Притяжательные):
```json
{"id":"A1-GRAM-0005","question":"Где твоя машина?","options":["Where is your car?","Where is my car?","Where is his car?","Where is our car?"],"correct":1,"explanation":"Твоя машина — your car. My (моя), his (его), our (наша).","tags":["grammar","possessive"],"source":"llm"}
```

## Инструкция

Сгенерируй **N вопросов** с фокусом на **ГРАММАТИКУ** для уровня **LEVEL**.

Используй набор/тему **KEY** (например "TENSE" или "001").

Фокус: **[укажи конкретную грамматическую тему, например: Present Simple]**

Начинай с номера **START_NUM**.

Помни: Варианты ответа должны отличаться **только грамматической формой**!

