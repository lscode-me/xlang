#!/usr/bin/env python3
"""
Генератор Mini App тестов для изучения языков.
Создаёт index.html в html/ma/ на основе шаблона.

В будущем будет генерировать тесты из курсов в папке Courses/
"""

import os
import sys
import shutil
from pathlib import Path


class MiniAppGenerator:
    """Генератор Mini App тестов для изучения языков"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.script_dir = Path(__file__).parent
        self.template_path = self.script_dir / "index.html"
        self.output_dir = self.base_dir / "html" / "ma"
        
    def ensure_output_dir(self):
        """Создаёт директорию для вывода, если её нет"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        print(f"📁 Директория вывода: {self.output_dir}")
        
    def copy_template(self):
        """Копирует шаблон index.html в html/ma/"""
        if not self.template_path.exists():
            print(f"❌ Ошибка: Шаблон {self.template_path} не найден")
            return False
            
        output_path = self.output_dir / "index.html"
        shutil.copy2(self.template_path, output_path)
        print(f"✅ Скопирован: {self.template_path} -> {output_path}")
        return True
        
    def generate(self):
        """Основной метод генерации"""
        print("🎯 Начинаем генерацию Mini App...")
        print("")
        
        self.ensure_output_dir()
        
        if not self.copy_template():
            return False
            
        print("")
        print("🎉 Генерация завершена успешно!")
        return True


def main():
    # Определяем базовую директорию
    if len(sys.argv) > 1:
        base_dir = sys.argv[1]
    else:
        # По умолчанию - родительская директория относительно скрипта
        base_dir = Path(__file__).parent.parent
    
    generator = MiniAppGenerator(base_dir)
    success = generator.generate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
