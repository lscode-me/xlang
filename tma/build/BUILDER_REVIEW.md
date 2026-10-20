# Оценка и рекомендации по улучшению builder.py

## 📊 Общая оценка

**Текущее состояние:** Хорошо структурированный код с четким разделением ответственностей, но есть возможности для улучшения.

**Оценка:** 7/10

---

## ✅ Что хорошо

1. **Четкая архитектура** - класс SiteBuilder инкапсулирует всю логику сборки
2. **Хорошая типизация** - используются type hints
3. **Документация** - есть docstrings для методов
4. **Валидация** - проверка конфигурации и данных перед сборкой
5. **Разделение ответственностей** - builder отделен от template_engine

---

## 🔴 Критические проблемы

### 1. **Дублирование кода загрузки конфигурации**
- `load_config()` вызывается несколько раз
- `get_course_config()` вызывает `load_config()` каждый раз
- Нет кэширования конфигурации

**Проблема:**
```python
def get_course_config(self) -> Dict[str, Any]:
    config = self.load_config()  # Загружается каждый раз!
    for course in config.get("courses", []):
        ...
```

### 2. **Отсутствие обработки ошибок на уровне методов**
- Многие методы могут упасть с неинформативными ошибками
- Нет валидации путей перед использованием
- Нет проверки существования файлов перед чтением

### 3. **Тесная связанность с check_data**
- Прямой импорт `import check_data as vocab`
- Сложно тестировать и мокировать
- Нет абстракции для валидации

### 4. **Дублирование логики поиска файлов**
- `find_jsonl_files()` и логика в `validate_data()` дублируют друг друга
- Похожая логика в `build_quiz_pages()`

### 5. **Отсутствие прогресс-бара для больших сборок**
- При большом количестве файлов нет индикации прогресса
- Сложно понять, сколько осталось

---

## 🟡 Средние проблемы

### 6. **Магические значения**
- `quiz_length` по умолчанию = 5 (hardcoded в нескольких местах)
- Паттерны валидации определены внутри метода

### 7. **Отсутствие логирования**
- Только print() для вывода
- Нет уровней логирования (debug, info, warning, error)
- Нет возможности отключить verbose вывод

### 8. **Нет обработки частичных ошибок**
- Если один файл невалиден, весь процесс падает
- Нет режима "продолжить несмотря на ошибки"

### 9. **Отсутствие метрик и статистики**
- Нет подсчета времени сборки
- Нет статистики по обработанным файлам
- Нет информации о размере выходных файлов

### 10. **Нет dry-run режима**
- Невозможно проверить, что будет собрано без реальной сборки
- Полезно для отладки

---

## 🟢 Мелкие улучшения

### 11. **Кэширование статических файлов**
- `get_static_file()` в template_engine кэширует, но можно улучшить

### 12. **Валидация путей**
- Нет проверки на path traversal атаки
- Нет нормализации путей

### 13. **Константы вместо магических строк**
- `"courses"`, `"contents"`, `"levels"` - должны быть константами

### 14. **Отсутствие типов для конфигурации**
- Используется `Dict[str, Any]` вместо TypedDict или dataclass

### 15. **Нет параллельной обработки**
- Файлы обрабатываются последовательно
- Можно распараллелить чтение JSONL файлов

---

## 💡 Рекомендации по рефакторингу

### Приоритет 1 (Критично)

1. **Добавить кэширование конфигурации**
   ```python
   def __init__(self, ...):
       self._config_cache = None
   
   def load_config(self) -> Dict[str, Any]:
       if self._config_cache is None:
           self._config_cache = self._load_config_from_file()
       return self._config_cache
   ```

2. **Вынести валидацию в отдельный класс**
   ```python
   class ConfigValidator:
       def validate(self, config: Dict[str, Any]) -> ValidationResult
   
   class DataValidator:
       def validate(self, files: List[Path]) -> ValidationResult
   ```

3. **Добавить обработку ошибок с контекстом**
   ```python
   class BuildError(Exception):
       pass
   
   class ConfigError(BuildError):
       pass
   
   class DataError(BuildError):
       pass
   ```

### Приоритет 2 (Важно)

4. **Добавить логирование вместо print()**
   ```python
   import logging
   
   logger = logging.getLogger(__name__)
   logger.info("Building course...")
   ```

5. **Создать TypedDict для конфигурации**
   ```python
   from typing import TypedDict
   
   class CourseConfig(TypedDict):
       id: str
       name: str
       dest_folder: str
       quiz_length: int
       contents: List[ContentConfig]
   ```

6. **Унифицировать поиск файлов**
   ```python
   class FileFinder:
       def find_jsonl_files(self, content_dir: str, levels: List[str]) -> Dict[str, List[Path]]
       def find_all_jsonl_files(self, contents: List[Dict]) -> List[Tuple[Path, str]]
   ```

### Приоритет 3 (Желательно)

7. **Добавить прогресс-бар**
   ```python
   from tqdm import tqdm
   
   for filepath in tqdm(files, desc="Processing files"):
       ...
   ```

8. **Добавить метрики**
   ```python
   class BuildMetrics:
       start_time: float
       files_processed: int
       questions_total: int
       ...
   ```

9. **Добавить dry-run режим**
   ```python
   def build(self, dry_run: bool = False) -> int:
       if dry_run:
           return self._simulate_build()
       return self._actual_build()
   ```

10. **Параллельная обработка файлов**
    ```python
    from concurrent.futures import ThreadPoolExecutor
    
    with ThreadPoolExecutor() as executor:
        results = executor.map(load_questions_from_jsonl, files)
    ```

---

## 📝 Конкретные улучшения кода

### Улучшение 1: Кэширование конфигурации

**Было:**
```python
def get_course_config(self) -> Dict[str, Any]:
    config = self.load_config()  # Загружается каждый раз
    ...
```

**Стало:**
```python
def __init__(self, ...):
    self._config_cache: Optional[Dict[str, Any]] = None

def load_config(self) -> Dict[str, Any]:
    if self._config_cache is None:
        config_path = self.repo_root / "data" / "config.json"
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with open(config_path, "r", encoding="utf-8") as f:
            self._config_cache = json.load(f)
    return self._config_cache
```

### Улучшение 2: Константы вместо магических строк

**Было:**
```python
for course in config.get("courses", []):
    if course["id"] == self.course_id:
```

**Стало:**
```python
CONFIG_KEY_COURSES = "courses"
CONFIG_KEY_CONTENTS = "contents"
CONFIG_KEY_LEVELS = "levels"

for course in config.get(CONFIG_KEY_COURSES, []):
    if course["id"] == self.course_id:
```

### Улучшение 3: Типизированная конфигурация

**Было:**
```python
def get_course_config(self) -> Dict[str, Any]:
```

**Стало:**
```python
from typing import TypedDict, List, Optional

class ContentConfig(TypedDict):
    id: str
    name: str
    dir: Optional[str]
    levels: List[str]

class CourseConfig(TypedDict):
    id: str
    name: str
    dest_folder: str
    quiz_length: int
    contents: List[ContentConfig]

def get_course_config(self) -> CourseConfig:
```

### Улучшение 4: Обработка ошибок с контекстом

**Было:**
```python
except Exception as e:
    print(f"\n❌ Build failed: {e}")
```

**Стало:**
```python
class BuildError(Exception):
    """Base exception for build errors"""
    pass

class ConfigError(BuildError):
    """Configuration-related errors"""
    pass

class DataError(BuildError):
    """Data validation errors"""
    pass

try:
    ...
except FileNotFoundError as e:
    raise ConfigError(f"Configuration file not found: {e}") from e
except ValueError as e:
    raise ConfigError(f"Invalid configuration: {e}") from e
except BuildError:
    raise
except Exception as e:
    raise BuildError(f"Unexpected error during build: {e}") from e
```

---

## 🎯 План рефакторинга

### Фаза 1: Критичные исправления (1-2 дня)
- [ ] Добавить кэширование конфигурации
- [ ] Вынести валидацию в отдельные классы
- [ ] Добавить кастомные исключения
- [ ] Унифицировать поиск файлов

### Фаза 2: Улучшения (2-3 дня)
- [ ] Заменить print() на logging
- [ ] Добавить TypedDict для конфигурации
- [ ] Добавить константы вместо магических строк
- [ ] Добавить валидацию путей

### Фаза 3: Оптимизации (1-2 дня)
- [ ] Добавить прогресс-бар
- [ ] Добавить метрики сборки
- [ ] Добавить dry-run режим
- [ ] Оптимизировать обработку файлов (параллелизм)

---

## 📈 Ожидаемые результаты

После рефакторинга:
- ✅ Код станет более тестируемым
- ✅ Улучшится обработка ошибок
- ✅ Упростится поддержка
- ✅ Повысится производительность
- ✅ Улучшится читаемость

---

## ❓ Вопросы для обсуждения

1. Нужен ли dry-run режим?
2. Нужна ли параллельная обработка файлов?
3. Какой уровень логирования нужен?
4. Нужны ли метрики сборки?
5. Планируется ли расширение функциональности?

