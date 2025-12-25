# 📦 Документация по форматам хранения данных

## Обзор системы хранения

Приложение использует трёхуровневую систему хранения данных:

1. **CloudStorage (Telegram)** — основное облачное хранилище
2. **localStorage (Browser)** — локальный кэш для быстрого доступа и fallback
3. **In-memory cache** — оперативная память для минимизации обращений к storage

## 🔑 Форматы ключей

### Прогресс по уровням и типам контента

**Формат ключа:**
```
quiz:ru-tr-{type}:{level}
```

**Параметры:**
- `{type}` — тип контента: `words` (слова) или `phrases` (фразы)
- `{level}` — уровень сложности: `a1`, `a2`, `b1` (в нижнем регистре)

**Примеры:**
```
quiz:ru-tr-words:a1
quiz:ru-tr-words:a2
quiz:ru-tr-words:b1
quiz:ru-tr-phrases:a1
quiz:ru-tr-phrases:a2
quiz:ru-tr-phrases:b1
```

### Глобальный счётчик уникальных дней

**Формат ключа:**
```
quiz:global:days-counter
```

## 📊 Форматы данных

### 1. Статистика прогресса по уровню

**Ключ:** `quiz:ru-tr-{type}:{level}`

**Формат JSON:**
```json
{
  "bestScore": 5,
  "lastScore": 4,
  "totalCorrect": 85,
  "totalQuestions": 100,
  "attempts": 20,
  "lastAttemptAt": "2025-12-25T10:30:00.000Z"
}
```

**Поля:**
- `bestScore` (number) — лучший результат за одну попытку (из 5)
- `lastScore` (number) — результат последней попытки (из 5)
- `totalCorrect` (number) — общее количество правильных ответов за все попытки
- `totalQuestions` (number) — общее количество вопросов за все попытки (попытки × 5)
- `attempts` (number) — количество пройденных тестов
- `lastAttemptAt` (string) — ISO 8601 дата последней попытки

**Вычисление процента прогресса:**
```javascript
const avgPercent = Math.round((totalCorrect / totalQuestions) * 100);
```

**Пример вычисления:**
- 85 правильных ответов из 100 вопросов = 85%
- 20 попыток × 5 вопросов = 100 всего вопросов

### 2. Глобальный счётчик уникальных дней

**Ключ:** `quiz:global:days-counter`

**Формат JSON:**
```json
{
  "uniqueDays": 7,
  "lastPassed": "2025-12-25"
}
```

**Поля:**
- `uniqueDays` (number) — количество уникальных дней, когда пользователь проходил тесты
- `lastPassed` (string) — дата последнего прохождения теста в формате `YYYY-MM-DD`

**Логика обновления:**
```javascript
const today = new Date().toISOString().split('T')[0]; // "2025-12-25"

if (prev.lastPassed !== today) {
  // Новый день — увеличиваем счётчик
  uniqueDays = prev.uniqueDays + 1;
  lastPassed = today;
} else {
  // Тот же день — счётчик не меняется
  uniqueDays = prev.uniqueDays;
}
```

## 🔄 Механизм синхронизации

### Чтение данных (`storage.get()`)

1. **Проверка in-memory кэша** (TTL: 30 секунд)
   ```javascript
   const cached = storage._cache[key];
   if (cached && Date.now() - cached.timestamp < 30000) {
     return cached.value; // Мгновенный возврат
   }
   ```

2. **Чтение из localStorage** — быстрый локальный доступ
   ```javascript
   const localValue = localStorage.getItem(key);
   ```

3. **Запрос к CloudStorage** с таймаутом 800ms
   ```javascript
   Telegram.WebApp.CloudStorage.getItem(key, callback);
   ```

4. **Синхронизация и кэширование**
   - Если CloudStorage вернул данные → обновляем localStorage
   - Обновляем in-memory кэш с текущей меткой времени
   - Если CloudStorage не ответил → используем localStorage

### Запись данных (`storage.set()`)

1. **Мгновенное обновление in-memory кэша**
   ```javascript
   storage._cache[key] = { value, timestamp: Date.now() };
   ```

2. **Запись в localStorage** (синхронно)
   ```javascript
   localStorage.setItem(key, value);
   ```

3. **Запись в CloudStorage** (асинхронно в фоне)
   ```javascript
   Telegram.WebApp.CloudStorage.setItem(key, value, callback);
   ```

### Удаление данных (`storage.remove()`)

1. Удаление из localStorage
2. Удаление из CloudStorage (асинхронно)
3. In-memory кэш автоматически истекает через 30 секунд

## 🎯 Примеры использования

### Загрузка прогресса на главной странице

```javascript
const storageKey = `quiz:ru-tr-words:a1`;
const data = await storage.get(storageKey);

if (data) {
  const stats = JSON.parse(data);
  const avgPercent = Math.round((stats.totalCorrect / stats.totalQuestions) * 100);
  console.log(`Progress: ${avgPercent}%`); // Progress: 85%
}
```

### Сохранение результатов теста

```javascript
const stats = {
  bestScore: 5,
  lastScore: 4,
  totalCorrect: 89,
  totalQuestions: 105,
  attempts: 21,
  lastAttemptAt: new Date().toISOString()
};

await storage.set('quiz:ru-tr-words:a1', JSON.stringify(stats));
```

### Обновление счётчика уникальных дней

```javascript
const today = new Date().toISOString().split('T')[0];
const globalKey = 'quiz:global:days-counter';
const globalData = await storage.get(globalKey);

let globalStats = { uniqueDays: 1, lastPassed: today };

if (globalData) {
  const prev = JSON.parse(globalData);
  if (prev.lastPassed !== today) {
    globalStats.uniqueDays = prev.uniqueDays + 1;
  } else {
    globalStats.uniqueDays = prev.uniqueDays;
  }
}

await storage.set(globalKey, JSON.stringify(globalStats));
```

## 🛡️ Обработка ошибок и валидация

### Проверка на повреждённые данные

При загрузке данных проверяется корректность процента:

```javascript
const avgPercent = (stats.totalCorrect / stats.totalQuestions) * 100;

if (avgPercent > 100) {
  console.warn('Corrupted stats detected! Resetting...');
  await storage.remove(storageKey);
  // Данные сбрасываются, начинаем с чистого листа
}
```

### Миграция старого формата

Старые версии использовали упрощённый формат с только `lastScore`. При обнаружении старого формата происходит автоматическая миграция:

```javascript
if (prev.lastScore !== undefined && prev.totalCorrect === undefined) {
  // Старый формат — инициализируем новый
  stats.totalCorrect = prev.lastScore + currentScore;
  stats.totalQuestions = 5 + 5; // Предыдущая + текущая попытка
}
```

## ⚡️ Оптимизация производительности

### Параллельная загрузка на главной странице

```javascript
const promises = [];
levels.forEach(level => {
  types.forEach(type => {
    promises.push(loadStats(level, type));
  });
});

await Promise.all(promises); // Все уровни загружаются одновременно
```

### Пропуск повторных запросов

```javascript
const cached = storage._cache[key];
if (cached && Date.now() - cached.timestamp < 30000) {
  console.log('Using cached data, skipping storage request');
  return; // Не делаем лишний запрос
}
```

### Мгновенное отображение кэшированных значений

На главной странице сначала показываются кэшированные значения (если есть), затем происходит фоновая загрузка актуальных данных.

## 📝 Места использования

| Файл | Назначение |
|------|-----------|
| [html/ma/assets/storage.js](../html/ma/assets/storage.js) | Реализация storage API с CloudStorage + localStorage |
| [html/ma/assets/app.js](../html/ma/assets/app.js) | Сохранение результатов тестов, обновление счётчиков |
| [html/ma/index.html](../html/ma/index.html) | Загрузка и отображение прогресса на главной странице |

## 🔍 Отладка

Для просмотра логов хранилища откройте консоль браузера. Все операции логируются с префиксом `[Storage]`:

```
[Storage] GET quiz:ru-tr-words:a1 from cache: {...}
[Storage] SET quiz:ru-tr-words:a1 to localStorage: {...}
[Storage] SET quiz:ru-tr-words:a1 to CloudStorage: OK
```

На главной странице используется префикс `[catalog]`:

```
[catalog] Using cached data for A1 (words)
[catalog] Calculated percent for A1 (words): 85%
```
