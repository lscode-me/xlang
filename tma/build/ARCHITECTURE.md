# Build System Architecture

## 📁 Новая структура

```
build/
├── build_site.py          # Главный оркестратор (точка входа)
├── builder.py             # Класс SiteBuilder - логика сборки
├── template_engine.py     # Класс TemplateEngine - рендеринг шаблонов
├── templates/             # Шаблоны HTML/CSS/JS
│   ├── quiz_page.html     # Шаблон страницы квиза
│   ├── catalog_page.html  # Шаблон каталога
│   ├── app.css            # Стили приложения
│   ├── app.js             # JavaScript квиза (с переменной {{ quiz_length }})
│   └── storage.js         # Обертка для Telegram CloudStorage
├── check_data.py          # Валидация и управление данными
├── quizes.py             # Конфигурация типов контента
└── requirements.txt       # Зависимости (jinja2)
```

## 🔧 Компоненты

### build_site.py
Простой оркестратор, который:
- Принимает course_id из аргументов командной строки
- Создает экземпляр SiteBuilder
- Запускает процесс сборки

### builder.py (SiteBuilder)
Класс, инкапсулирующий всю логику сборки:
- Загрузка конфигурации из config.json
- Валидация данных
- Подготовка output директории
- Генерация ассетов (CSS/JS)
- Сборка страниц квизов
- Сборка каталога

### template_engine.py (TemplateEngine)
Обертка над Jinja2 для рендеринга шаблонов:
- `render_quiz_page()` - рендерит страницу квиза
- `render_catalog_page()` - рендерит каталог
- `render_app_js()` - рендерит app.js с переменными
- `get_static_file()` - читает статические файлы (CSS/storage.js)

### templates/
Все шаблоны вынесены в отдельные файлы:
- **HTML** - с подсветкой синтаксиса, автокомплитом
- **CSS** - легко редактировать стили
- **JS** - нормальная разработка JavaScript
- **Jinja2 переменные** - `{{ variable }}` для динамического контента

## 🚀 Использование

### Базовая сборка
```bash
cd build
./venv/bin/python build_site.py ma
```

### Через build_ma.sh (рекомендуется)
```bash
cd build
./build_ma.sh ma
```

### Установка зависимостей
```bash
cd build
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## ✨ Преимущества новой архитектуры

1. **Разделение ответственностей**
   - Сборка: `builder.py`
   - Шаблоны: `template_engine.py`
   - Оркестрация: `build_site.py`

2. **Удобство разработки**
   - HTML/CSS/JS в отдельных файлах
   - Подсветка синтаксиса в редакторе
   - Автокомплит для HTML/CSS/JS
   - Легко тестировать изменения

3. **Переиспользование**
   - Шаблоны можно использовать повторно
   - Template engine можно расширять
   - Builder легко модифицировать

4. **Поддержка**
   - Код проще читать (меньше строк в файле)
   - Легче находить и исправлять баги
   - Проще добавлять новые функции

## 📝 Примеры изменений

### Изменить стили
Редактируйте `templates/app.css` напрямую в VS Code с полной поддержкой CSS.

### Изменить HTML структуру
Редактируйте `templates/quiz_page.html` или `templates/catalog_page.html`.

### Добавить новую переменную в шаблон
1. Добавьте `{{ new_variable }}` в шаблон
2. Передайте значение в `template_engine.render_*()` методе
3. Обновите вызов в `builder.py`

## 🔄 Миграция со старой версии

Старый `build_site.py` сохранен как `build_site_old.py` (1915 строк).

Новая система:
- `build_site.py` - 40 строк
- `builder.py` - 330 строк
- `template_engine.py` - 110 строк
- `templates/*` - шаблоны в отдельных файлах

**Итого**: Более модульный, читаемый и поддерживаемый код!
