#!/usr/bin/env python3
"""
Сборщик контента для Telegram Mini App (Web App).

Читает структуру курсов в `Courses/` и генерирует JSON-структуру в `tma/content/...`
согласно ТЗ в `build_tma/TZ_build_tma.md`.

Запуск из корня репозитория (по умолчанию):

    python3 build_tma/build.py --src Courses --out tma
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

# Импортируем названия курсов из отдельного файла
sys.path.insert(0, str(Path(__file__).parent.parent))
try:
    from Courses.course_names import COURSE_NAMES
except ImportError as e:
    print(f"⚠️  Не удалось импортировать COURSE_NAMES: {e}", file=sys.stderr)
    print("   Используется пустой словарь COURSE_NAMES", file=sys.stderr)
    COURSE_NAMES = {}


SCHEMA_VERSION = 1
GENERATOR_NAME = "build_tma"

INDEX_HTML_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>XLang Mini App</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
  <style>
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    :root {
      --tg-bg: #ffffff;
      --tg-text: #111827;
      --tg-subtle: #6b7280;
      --tg-accent: #2563eb;
      --tg-accent-soft: #dbeafe;
      --tg-border: #e5e7eb;
      --tg-surface: #ffffff;
    }

    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--tg-bg);
      color: var(--tg-text);
    }

    #app {
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--tg-border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      background: linear-gradient(90deg, rgba(37, 99, 235, 0.06), rgba(255, 255, 255, 0));
    }

    .app-title {
      font-size: 16px;
      font-weight: 600;
    }

    .app-subtitle {
      font-size: 12px;
      color: var(--tg-subtle);
    }

    .app-subtitle a {
      color: var(--tg-accent);
      text-decoration: none;
    }

    .app-subtitle a:hover {
      text-decoration: underline;
    }

    .user-pill {
      font-size: 12px;
      padding: 4px 8px;
      border-radius: 999px;
      border: 1px solid var(--tg-border);
      color: var(--tg-subtle);
      max-width: 50%;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
      text-align: right;
    }

    main {
      flex: 1;
      display: flex;
      flex-direction: column;
      padding: 8px;
      gap: 8px;
      overflow: hidden;
    }

    .layout {
      display: flex;
      flex-direction: column;
      gap: 8px;
      flex: 1;
      min-height: 0;
    }

    @media (min-width: 768px) {
      .layout {
        flex-direction: row;
      }
    }

    .column {
      background: var(--tg-surface);
      border-radius: 12px;
      border: 1px solid var(--tg-border);
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-height: 0;
    }

    .column h2 {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 2px;
    }

    .column-caption {
      font-size: 12px;
      color: var(--tg-subtle);
    }

    #courses-column {
      flex: 1;
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.06), var(--tg-surface));
    }

    #modules-column {
      flex: 1;
      background: linear-gradient(135deg, rgba(16, 185, 129, 0.06), var(--tg-surface));
      display: none;
    }

    #content-column {
      flex: 1;
      background: linear-gradient(135deg, rgba(249, 115, 22, 0.05), var(--tg-surface));
      display: none;
    }

    @media (min-width: 768px) {
      #courses-column {
        flex: 0 0 32%;
        max-height: none;
      }
      #modules-column {
        flex: 0 0 32%;
        max-height: none;
      }
      #content-column {
        flex: 0 0 36%;
      }
    }

    .scroll {
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
    }

    .list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .section-header {
      font-size: 12px;
      font-weight: 600;
      color: var(--tg-accent);
      padding: 8px 10px 4px 10px;
      margin-top: 8px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px solid var(--tg-border);
    }

    .section-header:first-child {
      margin-top: 0;
    }

    .list-item {
      width: 100%;
      text-align: left;
      border-radius: 999px;
      border: 1px solid var(--tg-border);
      padding: 6px 10px;
      font-size: 13px;
      background: #ffffff;
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      transition: background 0.15s ease, border-color 0.15s ease, transform 0.05s ease;
    }

    .list-item:hover {
      background: #f9fafb;
    }

    .list-item.active {
      border-color: var(--tg-accent);
      background: var(--tg-accent-soft);
      color: var(--tg-text);
    }

    .badge {
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 999px;
      background: #f3f4f6;
      color: var(--tg-subtle);
      flex-shrink: 0;
    }

    .badge-strong {
      background: var(--tg-accent-soft);
      color: var(--tg-accent);
    }

    .badge-completed {
      background: #16a34a;
      color: #ffffff;
    }

    .badge-progress {
      background: #f59e0b;
      color: #ffffff;
    }

    .item-title {
      font-size: 13px;
      flex: 1;
      min-width: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .local-tabs {
      display: flex;
      gap: 4px;
      margin-top: 6px;
    }

    .tab-btn {
      flex: 1;
      font-size: 12px;
      padding: 4px 6px;
      border-radius: 999px;
      border: 1px solid var(--tg-border);
      background: transparent;
      color: var(--tg-subtle);
      cursor: pointer;
    }

    .tab-btn.active {
      background: var(--tg-accent-soft);
      color: var(--tg-accent);
      border-color: var(--tg-accent);
    }

    .tab-btn:disabled {
      opacity: 0.4;
      cursor: default;
    }

    .content-tabs {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
      gap: 4px;
    }

    #lecture,
    #quiz {
      font-size: 13px;
      line-height: 1.5;
    }

    #lecture.active {
      display: block;
    }

    #lecture:not(.active) {
      display: none;
    }

    #quiz {
      display: none;
    }

    #quiz.active {
      display: block;
    }

    #lecture h1, #lecture h2, #lecture h3 {
      font-size: 15px;
      margin-top: 8px;
      margin-bottom: 4px;
    }

    #lecture p {
      margin: 4px 0;
    }

    #lecture ul, #lecture ol {
      padding-left: 18px;
      margin: 4px 0;
    }

    #lecture pre {
      background: #f6f8fa;
      color: #24292e;
      border-radius: 8px;
      padding: 8px;
      font-size: 12px;
      overflow-x: auto;
    }

    #lecture code {
      padding: 1px 4px;
      border-radius: 4px;
      font-family: ui-monospace, Menlo, Monaco, "SF Mono", monospace;
      font-size: 12px;
    }

    /* Инлайн-код внутри текста (не в блоках pre) — светлый фон, тёмный текст */
    #lecture :not(pre) > code {
      background: #e5e7eb;
      color: #111827;
    }

    #lecture pre code {
      background: transparent;
      padding: 0;
    }

    /* Цвета для подсветки синтаксиса (highlight.js и/или кастомные классы) - светлая тема */
    #lecture pre .hljs-keyword,
    #lecture pre .tok-kw {
      color: #d73a49;
    }

    #lecture pre .hljs-built_in,
    #lecture pre .hljs-type,
    #lecture pre .hljs-literal,
    #lecture pre .tok-builtin {
      color: #005cc5;
    }

    #lecture pre .hljs-string,
    #lecture pre .hljs-attr,
    #lecture pre .tok-str {
      color: #032f62;
    }

    #lecture pre .hljs-number,
    #lecture pre .tok-key {
      color: #005cc5;
    }

    #lecture pre .hljs-comment,
    #lecture pre .tok-comment {
      color: #6a737d;
      font-style: italic;
    }

    #quiz .quiz-question {
      border-radius: 8px;
      border: 1px solid var(--tg-border);
      padding: 8px;
      margin-bottom: 6px;
      background: var(--tg-surface);
    }

    .quiz-question-title {
      font-weight: 600;
      font-size: 13px;
      margin-bottom: 4px;
    }

    .quiz-question-prompt {
      font-size: 13px;
    }

    .quiz-options {
      display: flex;
      flex-direction: column;
      gap: 4px;
      margin-top: 4px;
    }

    .quiz-option {
      border-radius: 999px;
      border: 1px solid var(--tg-border);
      padding: 4px 8px;
      background: #ffffff;
      font-size: 13px;
      text-align: left;
      cursor: pointer;
    }

    .quiz-option.selected {
      border-color: var(--tg-accent);
      background: var(--tg-accent-soft);
    }

    .quiz-option.correct {
      border-color: #16a34a;
      background: linear-gradient(135deg, rgba(22, 163, 74, 0.15), rgba(22, 163, 74, 0.08));
      border-width: 2px;
      font-weight: 600;
      color: #15803d;
    }

    .quiz-option.incorrect {
      border-color: #dc2626;
      background: linear-gradient(135deg, rgba(220, 38, 38, 0.15), rgba(220, 38, 38, 0.08));
      border-width: 2px;
      font-weight: 600;
      color: #b91c1c;
      opacity: 1;
    }

    .quiz-explanation {
      margin-top: 4px;
      font-size: 12px;
      color: var(--tg-subtle);
    }

    .quiz-footer {
      margin-top: 6px;
      font-size: 12px;
      color: var(--tg-subtle);
    }

    .quiz-footer.has-results {
      margin-top: 12px;
      padding: 12px;
      border-radius: 8px;
      font-size: 14px;
      font-weight: 600;
      text-align: center;
      background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(37, 99, 235, 0.05));
      border: 2px solid var(--tg-accent);
      color: var(--tg-accent);
    }

    .quiz-check-btn {
      margin-top: 4px;
      width: 100%;
      padding: 6px 8px;
      border-radius: 999px;
      border: none;
      background: var(--tg-accent);
      color: #ffffff;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
    }

    .quiz-check-btn:active {
      transform: scale(0.99);
    }

    .lecture-quiz-btn {
      margin-top: 24px;
      margin-bottom: 8px;
      width: 100%;
      padding: 10px 16px;
      border-radius: 999px;
      border: 2px solid var(--tg-accent);
      background: var(--tg-accent);
      color: #ffffff;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      text-align: center;
      transition: background 0.15s ease, transform 0.05s ease;
    }

    .lecture-quiz-btn:hover {
      background: #1d4ed8;
    }

    .lecture-quiz-btn:active {
      transform: scale(0.98);
    }

    .lecture-quiz-btn:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    #status {
      font-size: 12px;
      color: var(--tg-subtle);
      text-align: left;
    }

    #debug {
      margin-top: 4px;
      font-size: 11px;
    }

    #debug summary {
      cursor: pointer;
      color: var(--tg-subtle);
    }

    #out {
      margin-top: 4px;
      max-height: 140px;
      overflow: auto;
      background: #f6f8fa;
      color: #24292e;
      padding: 6px;
      border-radius: 8px;
    }
  </style>
</head>
<body>
  <div id="app">
    <header>
      <div>
        <div class="app-title">XLang Mini App</div>
        <div class="app-subtitle">Курсы и квизы из <a href="https://xlang.me" target="_blank" rel="noopener noreferrer">xlang.me</a> | <a href="mailto:admin@xlang.me">admin@xlang.me</a></div>
      </div>
      <div id="user-pill" class="user-pill" title=""></div>
    </header>
    <main>
      <div id="status">Загружаем список курсов…</div>
      <div class="layout">
        <section id="courses-column" class="column">
          <div>
            <h2>Курсы</h2>
            <div class="column-caption">Выберите направление</div>
          </div>
          <div id="courses" class="list scroll"></div>
        </section>
        <section id="modules-column" class="column">
          <div>
            <h2 id="modules-title">Модули</h2>
            <div class="column-caption">Сначала выберите курс</div>
          </div>
          <div id="modules" class="list scroll"></div>
        </section>
        <section id="content-column" class="column">
          <div>
            <h2 id="content-title">Лекция</h2>
            <div class="column-caption">Текст лекции и интерактивный квиз</div>
            <div class="local-tabs">
              <button id="tab-lecture" class="tab-btn active" type="button">Лекция</button>
              <button id="tab-quiz" class="tab-btn" type="button" disabled>Квиз</button>
            </div>
          </div>
          <div class="content-tabs">
            <div id="lecture" class="scroll active"></div>
            <div id="quiz" class="scroll"></div>
          </div>
        </section>
      </div>
      <section id="debug">
        <details>
          <summary>Debug: Telegram initData</summary>
          <pre id="out"></pre>
        </details>
      </section>
    </main>
  </div>

  <script>
    (function () {
      const tg = window.Telegram && window.Telegram.WebApp;

      if (tg && typeof tg.ready === "function") {
        tg.ready();
      }

      function applyTheme(themeParams, colorScheme) {
        const root = document.documentElement;
        // Жестко задаем светлую тему, игнорируя настройки Telegram
        const isDark = false;

        // Всегда используем светлые цвета, независимо от настроек
        root.style.setProperty("--tg-bg", "#ffffff");
        root.style.setProperty("--tg-text", "#111827");
        root.style.setProperty("--tg-subtle", "#6b7280");
        root.style.setProperty("--tg-accent", "#2563eb");
        root.style.setProperty("--tg-accent-soft", "#dbeafe");
        root.style.setProperty("--tg-border", "#e5e7eb");
        root.style.setProperty("--tg-surface", "#ffffff");
      }

      if (tg) {
        try {
          if (typeof tg.expand === "function") {
            tg.expand();
          }
          // Отключаем закрытие при скролле вверх
          if (typeof tg.disableVerticalSwipes === "function") {
            tg.disableVerticalSwipes();
          }
          // Требуем подтверждение перед закрытием
          if (typeof tg.enableClosingConfirmation === "function") {
            tg.enableClosingConfirmation();
          }
        } catch (e) {
          console.warn("Telegram API call failed:", e);
        }
        // Всегда применяем светлую тему, игнорируя настройки Telegram
        applyTheme({}, "light");
      } else {
        // В браузере вне Telegram используем светлую тему по умолчанию
        applyTheme({}, "light");
      }

      const statusEl = document.getElementById("status");
      const coursesEl = document.getElementById("courses");
      const modulesEl = document.getElementById("modules");
      const lectureEl = document.getElementById("lecture");
      const quizEl = document.getElementById("quiz");
      const modulesTitleEl = document.getElementById("modules-title");
      const contentTitleEl = document.getElementById("content-title");
      const userPillEl = document.getElementById("user-pill");
      const outEl = document.getElementById("out");
      const tabLectureBtn = document.getElementById("tab-lecture");
      const tabQuizBtn = document.getElementById("tab-quiz");

      const VIEW_COURSES = "courses";
      const VIEW_MODULES = "modules";
      const VIEW_CONTENT = "content";

      // Показ данных пользователя Telegram
      if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user && userPillEl) {
        const u = tg.initDataUnsafe.user;
        const name = [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username || "Пользователь";
        userPillEl.textContent = "@" + (u.username || name);
        userPillEl.title = JSON.stringify(u, null, 2);
      } else if (userPillEl) {
        userPillEl.textContent = "Гость";
      }

      if (tg && outEl) {
        outEl.textContent = JSON.stringify(
          { initData: tg.initData, user: tg.initDataUnsafe && tg.initDataUnsafe.user },
          null,
          2
        );
      }

      // Настройки marked: подсветку делаем через highlight.js после рендера
      if (window.marked && typeof window.marked.setOptions === "function") {
        window.marked.setOptions({});
      }

      const COURSE_ICONS = {
{COURSE_ICONS_PLACEHOLDER}
      };

      function getCourseIcon(course) {
        const id = (course && course.course_id ? String(course.course_id) : "").toLowerCase();
        return COURSE_ICONS[id] || "📚";
      }

      const canUseBackButton =
        !!(
          tg &&
          tg.BackButton &&
          typeof tg.BackButton.show === "function" &&
          typeof tg.isVersionAtLeast === "function" &&
          tg.isVersionAtLeast("6.1")
        );

      const canUseCloudStorage =
        !!(
          tg &&
          tg.CloudStorage &&
          typeof tg.CloudStorage.getItems === "function" &&
          typeof tg.isVersionAtLeast === "function" &&
          tg.isVersionAtLeast("6.9")
        );

      function setView(view) {
        const coursesCol = document.getElementById("courses-column");
        const modulesCol = document.getElementById("modules-column");
        const contentCol = document.getElementById("content-column");
        if (coursesCol) {
          coursesCol.style.display = view === VIEW_COURSES ? "flex" : "none";
        }
        if (modulesCol) {
          modulesCol.style.display = view === VIEW_MODULES ? "flex" : "none";
        }
        if (contentCol) {
          contentCol.style.display = view === VIEW_CONTENT ? "flex" : "none";
        }
      }

      let indexData = null;
      let currentCourseId = null;
      let currentModules = [];
      let currentModuleId = null;
      let quizProgress = {}; // { "course_id:module_id": { correctCount, total, pct, timestamp } }

      function processModuleLinks(container) {
        /**
         * Обрабатывает ссылки на другие модули в контейнере.
         * Находит ссылки вида content/courses/{course_id}/modules/{module_id}/lecture.json
         * и добавляет обработчик клика для навигации к соответствующему модулю.
         */
        if (!container || !currentModules || currentModules.length === 0) {
          return;
        }

        const links = container.querySelectorAll('a[href]');
        links.forEach((link) => {
          const href = link.getAttribute('href');
          if (!href) return;

          // Проверяем, является ли ссылка ссылкой на модуль TMA
          // Формат: content/courses/{course_id}/modules/{module_id}/lecture.json
          // или courses/{course_id}/modules/{module_id}/lecture.json
          const moduleLinkMatch = href.match(/(?:content\/)?courses\/[^\/]+\/modules\/([^\/]+)\/lecture\.json/);
          if (moduleLinkMatch) {
            const targetModuleId = moduleLinkMatch[1];
            
            // Ищем модуль в текущем списке модулей
            const targetModule = currentModules.find((m) => m.module_id === targetModuleId);
            if (targetModule) {
              // Предотвращаем стандартное поведение ссылки
              link.addEventListener('click', (e) => {
                e.preventDefault();
                // Выбираем целевой модуль
                selectModule(targetModule);
              });
              // Добавляем визуальный индикатор, что это ссылка на модуль
              link.style.cursor = 'pointer';
              link.style.textDecoration = 'underline';
            }
          }
        });
      }
      let pendingModuleId = null;
      let currentQuiz = null;

      function setStatus(text) {
        if (statusEl) {
          statusEl.textContent = text || "";
        }
      }

      function escapeHtml(str) {
        return String(str)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
      }

      function clearActive(listEl) {
        if (!listEl) return;
        listEl.querySelectorAll(".list-item.active").forEach((el) => {
          el.classList.remove("active");
        });
      }

      function setActiveTab(tab) {
        if (!lectureEl || !quizEl || !tabLectureBtn || !tabQuizBtn) return;
        if (tab === "quiz" && tabQuizBtn.disabled) {
          return;
        }
        if (tab === "quiz" && !currentQuiz) {
          return;
        }
        if (tab === "lecture") {
          lectureEl.classList.add("active");
          quizEl.classList.remove("active");
          tabLectureBtn.classList.add("active");
          tabQuizBtn.classList.remove("active");
        } else {
          lectureEl.classList.remove("active");
          quizEl.classList.add("active");
          tabLectureBtn.classList.remove("active");
          tabQuizBtn.classList.add("active");
        }
      }

      function updateBackButton() {
        if (!canUseBackButton) return;
        if (!currentCourseId) {
          try {
            tg.BackButton.hide();
          } catch (e) {
            // ignore
          }
          return;
        }
        try {
          tg.BackButton.show();
        } catch (e) {
          // ignore
        }
      }

      function updateMainButton() {
        if (!tg || !tg.MainButton) return;
        if (!currentCourseId || !currentModules || currentModules.length === 0 || !currentModuleId) {
          tg.MainButton.hide();
          return;
        }
        const idx = currentModules.findIndex((m) => m.module_id === currentModuleId);
        if (idx === -1) {
          tg.MainButton.hide();
          return;
        }
        const hasNext = idx < currentModules.length - 1;
        tg.MainButton.setText(hasNext ? "Следующий модуль" : "К первому модулю");
        tg.MainButton.show();
      }

      function saveSelection(courseId, moduleId) {
        if (!canUseCloudStorage) return;
        const cVal = courseId ? String(courseId) : "";
        const mVal = moduleId ? String(moduleId) : "";
        try {
          tg.CloudStorage.setItem("last_course_id", cVal, function () {});
          tg.CloudStorage.setItem("last_module_id", mVal, function () {});
        } catch (e) {
          console.warn("CloudStorage.setItem error:", e);
        }
      }

      function saveQuizResult(courseId, moduleId, correctCount, total, pct) {
        if (!canUseCloudStorage || !courseId || !moduleId) return;
        const key = `quiz_result_${courseId}_${moduleId}`;
        const result = {
          correctCount: correctCount,
          total: total,
          pct: pct,
          timestamp: Date.now()
        };
        try {
          tg.CloudStorage.setItem(key, JSON.stringify(result), function (err) {
            if (err) {
              console.warn("CloudStorage.setItem error for quiz result:", err);
            } else {
              // Обновляем локальный кэш
              const cacheKey = `${courseId}:${moduleId}`;
              quizProgress[cacheKey] = result;
              // Обновляем отображение модулей, если мы на экране модулей
              if (currentCourseId === courseId && modulesEl) {
                renderModules();
              }
            }
          });
        } catch (e) {
          console.warn("CloudStorage.setItem exception:", e);
        }
      }

      function loadQuizProgress(courseId, callback) {
        if (!canUseCloudStorage || !courseId) {
          if (callback) callback({});
          return;
        }
        try {
          // Получаем все ключи из CloudStorage
          // К сожалению, CloudStorage не поддерживает получение всех ключей напрямую
          // Поэтому мы будем загружать прогресс для каждого модуля отдельно при рендеринге
          if (callback) callback({});
        } catch (e) {
          console.warn("CloudStorage.getItems exception for quiz progress:", e);
          if (callback) callback({});
        }
      }

      function getQuizResult(courseId, moduleId, callback) {
        if (!canUseCloudStorage || !courseId || !moduleId) {
          if (callback) callback(null);
          return;
        }
        const key = `quiz_result_${courseId}_${moduleId}`;
        const cacheKey = `${courseId}:${moduleId}`;
        
        // Проверяем кэш
        if (quizProgress[cacheKey]) {
          if (callback) callback(quizProgress[cacheKey]);
          return;
        }

        try {
          tg.CloudStorage.getItem(key, function (err, value) {
            if (err) {
              console.warn("CloudStorage.getItem error for quiz result:", err);
              if (callback) callback(null);
              return;
            }
            if (!value) {
              if (callback) callback(null);
              return;
            }
            try {
              const result = JSON.parse(value);
              quizProgress[cacheKey] = result;
              if (callback) callback(result);
            } catch (e) {
              console.warn("Failed to parse quiz result:", e);
              if (callback) callback(null);
            }
          });
        } catch (e) {
          console.warn("CloudStorage.getItem exception:", e);
          if (callback) callback(null);
        }
      }

      function restoreSelection() {
        if (!canUseCloudStorage) return;
        if (!indexData || !Array.isArray(indexData.courses) || !coursesEl) return;
        try {
          tg.CloudStorage.getItems(["last_course_id", "last_module_id"], function (err, data) {
            if (err) {
              console.warn("CloudStorage.getItems error:", err);
              return;
            }
            if (!data) return;
            const cid = data["last_course_id"];
            const mid = data["last_module_id"];
            if (!cid) return;
            const btn = coursesEl.querySelector('.list-item[data-course-id="' + cid + '"]');
            if (!btn || typeof btn.click !== "function") return;
            if (mid) {
              pendingModuleId = mid;
            }
            btn.click();
          });
        } catch (e) {
          console.warn("CloudStorage.getItems exception:", e);
        }
      }

      function handleBackClick() {
        if (!canUseBackButton) return;
        if (currentModuleId) {
          currentModuleId = null;
          clearActive(modulesEl);
          if (lectureEl) {
            lectureEl.innerHTML = "<p style='color: var(--tg-subtle);'>Выберите модуль, чтобы открыть лекцию.</p>";
          }
          setStatus("Выберите модуль, чтобы открыть лекцию.");
          saveSelection(currentCourseId, null);
          setView(VIEW_MODULES);
          updateBackButton();
          updateMainButton();
          return;
        }
        if (currentCourseId) {
          currentCourseId = null;
          clearActive(coursesEl);
          if (modulesEl) {
            modulesEl.innerHTML = "";
          }
          if (lectureEl) {
            lectureEl.innerHTML = "<p style='color: var(--tg-subtle);'>Выберите курс, чтобы начать.</p>";
          }
          if (modulesTitleEl) {
            modulesTitleEl.textContent = "Модули";
          }
          if (contentTitleEl) {
            contentTitleEl.textContent = "Лекция";
          }
          setStatus("Выберите курс.");
          saveSelection(null, null);
          setView(VIEW_COURSES);
          updateBackButton();
          updateMainButton();
        }
      }

      function handleMainButtonClick() {
        if (!tg || !tg.MainButton) return;
        if (!currentModules || !currentModules.length || !currentModuleId || !modulesEl) return;
        const idx = currentModules.findIndex((m) => m.module_id === currentModuleId);
        if (idx === -1) return;
        const nextIdx = idx < currentModules.length - 1 ? idx + 1 : 0;
        const target = currentModules[nextIdx];
        if (!target) return;
        const btn = modulesEl.querySelector('.list-item[data-module-id="' + target.module_id + '"]');
        if (btn && typeof btn.click === "function") {
          btn.click();
        }
      }

      if (canUseBackButton && tg && tg.BackButton && typeof tg.BackButton.onClick === "function") {
        try {
          tg.BackButton.hide();
        } catch (e) {
          // ignore
        }
        tg.BackButton.onClick(handleBackClick);
      }
      if (tg && tg.MainButton && typeof tg.MainButton.onClick === "function") {
        tg.MainButton.hide();
        tg.MainButton.onClick(handleMainButtonClick);
      }

      if (tabLectureBtn) {
        tabLectureBtn.addEventListener("click", () => setActiveTab("lecture"));
      }
      if (tabQuizBtn) {
        tabQuizBtn.addEventListener("click", () => setActiveTab("quiz"));
      }

      // Начальный экран — список курсов
      setView(VIEW_COURSES);

      async function loadIndex() {
        setStatus("Загружаем список курсов…");
        try {
          const res = await fetch("index.json", { cache: "no-store" });
          if (!res.ok) {
            throw new Error("HTTP " + res.status);
          }
          indexData = await res.json();
          renderCourses();
          restoreSelection();
          setStatus("Выберите курс и модуль, чтобы открыть лекцию.");
        } catch (err) {
          console.error(err);
          setStatus("Ошибка загрузки index.json: " + (err && err.message ? err.message : err));
          if (coursesEl) {
            coursesEl.textContent = "Не удалось загрузить список курсов.";
          }
        }
      }

      function renderCourses() {
        if (!coursesEl) return;
        coursesEl.innerHTML = "";

        if (!indexData || !Array.isArray(indexData.courses) || indexData.courses.length === 0) {
          coursesEl.textContent = "Курсы не найдены.";
          return;
        }

        // Группируем курсы по разделам
        const sectionsToCourses = {};
        const coursesWithoutSections = [];

        indexData.courses.forEach((course) => {
          const sections = course.sections || [];
          if (sections.length === 0) {
            coursesWithoutSections.push(course);
          } else {
            sections.forEach((section) => {
              if (!sectionsToCourses[section]) {
                sectionsToCourses[section] = [];
              }
              sectionsToCourses[section].push(course);
            });
          }
        });

        // Сортируем разделы по алфавиту
        const sortedSections = Object.keys(sectionsToCourses).sort();

        // Рендерим разделы
        sortedSections.forEach((section) => {
          // Заголовок раздела
          const sectionHeader = document.createElement("div");
          sectionHeader.className = "section-header";
          sectionHeader.textContent = section;
          coursesEl.appendChild(sectionHeader);

          // Курсы в разделе (сортируем по названию)
          const sectionCourses = sectionsToCourses[section].sort((a, b) => {
            const titleA = a.title || a.course_id;
            const titleB = b.title || b.course_id;
            return titleA.localeCompare(titleB);
          });

          sectionCourses.forEach((course) => {
            const btn = document.createElement("button");
            btn.className = "list-item";
            btn.dataset.courseId = course.course_id;

            const badge = document.createElement("span");
            badge.className = "badge";
            badge.textContent = String(course.modules_count || 0);

            const title = document.createElement("span");
            title.className = "item-title";
            const icon = getCourseIcon(course);
            const label = course.title || course.course_id;
            title.textContent = icon + " " + label;

            btn.appendChild(badge);
            btn.appendChild(title);

            btn.addEventListener("click", () => {
              clearActive(coursesEl);
              btn.classList.add("active");
              selectCourse(course);
            });

            coursesEl.appendChild(btn);
          });
        });

        // Курсы без разделов (если есть)
        if (coursesWithoutSections.length > 0) {
          const sectionHeader = document.createElement("div");
          sectionHeader.className = "section-header";
          sectionHeader.textContent = "Другие";
          coursesEl.appendChild(sectionHeader);

          coursesWithoutSections.sort((a, b) => {
            const titleA = a.title || a.course_id;
            const titleB = b.title || b.course_id;
            return titleA.localeCompare(titleB);
          }).forEach((course) => {
            const btn = document.createElement("button");
            btn.className = "list-item";
            btn.dataset.courseId = course.course_id;

            const badge = document.createElement("span");
            badge.className = "badge";
            badge.textContent = String(course.modules_count || 0);

            const title = document.createElement("span");
            title.className = "item-title";
            const icon = getCourseIcon(course);
            const label = course.title || course.course_id;
            title.textContent = icon + " " + label;

            btn.appendChild(badge);
            btn.appendChild(title);

            btn.addEventListener("click", () => {
              clearActive(coursesEl);
              btn.classList.add("active");
              selectCourse(course);
            });

            coursesEl.appendChild(btn);
          });
        }
      }

      async function selectCourse(course) {
        currentCourseId = course.course_id;
        currentModules = [];
        currentModuleId = null;
        saveSelection(currentCourseId, null);
        updateBackButton();
        updateMainButton();
        setView(VIEW_MODULES);

        if (modulesEl) {
          modulesEl.innerHTML = "";
        }
        if (lectureEl) {
          lectureEl.innerHTML = "<p style='color: var(--tg-subtle);'>Выберите модуль, чтобы открыть лекцию.</p>";
        }
        if (quizEl) {
          quizEl.innerHTML = "";
        }
        if (tabQuizBtn) {
          tabQuizBtn.disabled = true;
          tabQuizBtn.textContent = "Квиз";
        }
        setActiveTab("lecture");
        // Удаляем кнопку квиза из лекции при смене модуля
        if (lectureEl) {
          const oldBtn = lectureEl.querySelector(".lecture-quiz-btn");
          if (oldBtn) {
            oldBtn.remove();
          }
        }

        if (modulesTitleEl) {
          modulesTitleEl.textContent = "Модули: " + (course.title || course.course_id);
        }
        if (contentTitleEl) {
          contentTitleEl.textContent = "Лекция";
        }

        if (!course.url_modules) {
          if (modulesEl) {
            modulesEl.textContent = "Для этого курса ещё нет модулей.";
          }
          return;
        }

        setStatus("Загружаем модули курса…");
        try {
          const res = await fetch(course.url_modules, { cache: "no-store" });
          if (!res.ok) {
            throw new Error("HTTP " + res.status);
          }
          const data = await res.json();
          currentModules = Array.isArray(data.modules) ? data.modules : [];
          renderModules();
          setStatus("Выберите модуль, чтобы открыть лекцию.");
        } catch (err) {
          console.error(err);
          setStatus("Ошибка загрузки modules.json: " + (err && err.message ? err.message : err));
          if (modulesEl) {
            modulesEl.textContent = "Не удалось загрузить модули.";
          }
        }
      }

      function renderModules() {
        if (!modulesEl) return;
        modulesEl.innerHTML = "";

        if (!currentModules || currentModules.length === 0) {
          modulesEl.textContent = "В этом курсе пока нет модулей.";
          return;
        }

        // Сначала создаем все элементы модулей
        const moduleElements = [];
        currentModules.forEach((mod) => {
          const btn = document.createElement("button");
          btn.className = "list-item";
          btn.dataset.moduleId = mod.module_id;

          const badge = document.createElement("span");
          badge.className = "badge";
          const no = typeof mod.module_no === "number" ? mod.module_no : 0;
          badge.textContent = no.toString().padStart(2, "0");

          const title = document.createElement("span");
          title.className = "item-title";
          title.textContent = mod.title || mod.module_id;

          const quizBadge = document.createElement("span");
          quizBadge.className = "badge" + (mod.has_quiz ? " badge-strong" : "");
          quizBadge.textContent = mod.has_quiz ? "Квиз" : "Лекция";
          quizBadge.id = `quiz-badge-${mod.module_id}`;

          btn.appendChild(badge);
          btn.appendChild(title);
          btn.appendChild(quizBadge);

          btn.addEventListener("click", () => {
            clearActive(modulesEl);
            btn.classList.add("active");
            selectModule(mod);
          });

          modulesEl.appendChild(btn);
          moduleElements.push({ mod: mod, badge: quizBadge });
        });

        // Загружаем прогресс для каждого модуля с квизом
        moduleElements.forEach(({ mod, badge }) => {
          if (mod.has_quiz && currentCourseId) {
            getQuizResult(currentCourseId, mod.module_id, function (result) {
              if (result && result.total > 0) {
                const pct = result.pct || Math.round((result.correctCount / result.total) * 100);
                if (pct >= 90) {
                  badge.className = "badge badge-completed";
                  badge.textContent = "✓ " + pct + "%";
                } else if (pct >= 50) {
                  badge.className = "badge badge-progress";
                  badge.textContent = pct + "%";
                } else {
                  badge.className = "badge badge-strong";
                  badge.textContent = pct + "%";
                }
              }
            });
          }
        });

        if (pendingModuleId && modulesEl) {
          const autoBtn = modulesEl.querySelector('.list-item[data-module-id="' + pendingModuleId + '"]');
          if (autoBtn && typeof autoBtn.click === "function") {
            autoBtn.click();
          }
          pendingModuleId = null;
        }
      }

      async function selectModule(mod) {
        currentModuleId = mod.module_id;
        saveSelection(currentCourseId, currentModuleId);
        updateBackButton();
        updateMainButton();
        setView(VIEW_CONTENT);

        if (contentTitleEl) {
          contentTitleEl.textContent = mod.title || mod.module_id || "Лекция";
        }
        if (lectureEl) {
          lectureEl.innerHTML = "<p style='color: var(--tg-subtle);'>Загружаем лекцию…</p>";
        }
        if (quizEl) {
          quizEl.innerHTML = "";
        }
        if (tabQuizBtn) {
          tabQuizBtn.disabled = true;
          tabQuizBtn.textContent = "Квиз";
        }
        setActiveTab("lecture");
        // Удаляем старую кнопку квиза из лекции при загрузке нового модуля
        if (lectureEl) {
          const oldBtn = lectureEl.querySelector(".lecture-quiz-btn");
          if (oldBtn) {
            oldBtn.remove();
          }
        }
        setStatus("Загружаем lecture.json…");

        if (!mod.url_lecture) {
          if (lectureEl) {
            lectureEl.textContent = "Для этого модуля ещё нет лекции.";
          }
          setStatus("Для этого модуля нет lecture.json.");
          return;
        }

        try {
          const res = await fetch(mod.url_lecture, { cache: "no-store" });
          if (!res.ok) {
            throw new Error("HTTP " + res.status);
          }
          const data = await res.json();
          const md = data.markdown || "";

          let html = "";
          if (window.marked && typeof window.marked.parse === "function") {
            html = window.marked.parse(md);
          } else {
            html = "<pre>" + escapeHtml(md) + "</pre>";
          }

          if (lectureEl) {
            lectureEl.innerHTML = html;
            if (window.hljs && typeof window.hljs.highlightAll === "function") {
              try {
                window.hljs.highlightAll();
              } catch (e) {
                console.warn("hljs.highlightAll error:", e);
              }
            }
            // Обрабатываем ссылки на другие модули
            processModuleLinks(lectureEl);
            // Добавляем кнопку квиза в конец лекции, если квиз есть
            if (mod.has_quiz && mod.url_quiz) {
              const quizBtn = document.createElement("button");
              quizBtn.type = "button";
              quizBtn.className = "lecture-quiz-btn";
              quizBtn.id = "lecture-quiz-btn";
              quizBtn.textContent = "✅ Загрузка квиза...";
              quizBtn.disabled = true;
              quizBtn.style.opacity = "0.6";
              quizBtn.addEventListener("click", () => {
                if (currentQuiz && !tabQuizBtn.disabled) {
                  setActiveTab("quiz");
                  // Прокручиваем к началу квиза
                  if (quizEl) {
                    quizEl.scrollTop = 0;
                  }
                }
              });
              lectureEl.appendChild(quizBtn);
            }
          }
          setStatus("Лекция загружена.");

          if (mod.has_quiz && mod.url_quiz) {
            loadQuizForModule(mod);
          } else {
            currentQuiz = null;
          }
        } catch (err) {
          console.error(err);
          setStatus("Ошибка загрузки lecture.json: " + (err && err.message ? err.message : err));
          if (lectureEl) {
            lectureEl.textContent = "Не удалось загрузить лекцию.";
          }
        }
      }

      async function loadQuizForModule(mod) {
        if (!mod.url_quiz) {
          return;
        }
        setStatus("Лекция загружена. Загружаем quiz.json…");
        try {
          const res = await fetch(mod.url_quiz, { cache: "no-store" });
          if (!res.ok) {
            throw new Error("HTTP " + res.status);
          }
          const data = await res.json();
          currentQuiz = data;
          const questions = Array.isArray(data.questions) ? data.questions : [];
          const count = questions.length;

          renderQuiz();

          if (tabQuizBtn) {
            tabQuizBtn.disabled = count === 0;
            tabQuizBtn.textContent = count > 0 ? `Квиз (${count})` : "Квиз";
          }

          // Обновляем кнопку в конце лекции, если она уже была добавлена
          if (lectureEl) {
            const existingBtn = lectureEl.querySelector("#lecture-quiz-btn");
            if (existingBtn) {
              if (count > 0) {
                existingBtn.textContent = `✅ Перейти к квизу (${count} вопросов)`;
                existingBtn.disabled = false;
                existingBtn.style.opacity = "1";
              } else {
                existingBtn.textContent = "Квиз недоступен";
                existingBtn.disabled = true;
                existingBtn.style.opacity = "0.6";
              }
            }
          }

          setStatus(
            count > 0
              ? `Лекция и квиз загружены (${count} вопросов).`
              : "Лекция загружена, но квиз пустой."
          );
        } catch (err) {
          console.error(err);
          setStatus("Ошибка загрузки quiz.json: " + (err && err.message ? err.message : err));
          // Обновляем кнопку в конце лекции при ошибке
          if (lectureEl) {
            const existingBtn = lectureEl.querySelector("#lecture-quiz-btn");
            if (existingBtn) {
              existingBtn.textContent = "❌ Ошибка загрузки квиза";
              existingBtn.disabled = true;
              existingBtn.style.opacity = "0.6";
            }
          }
        }
      }

      function renderQuiz() {
        if (!quizEl) return;
        quizEl.innerHTML = "";

        if (!currentQuiz || !Array.isArray(currentQuiz.questions) || !currentQuiz.questions.length) {
          const p = document.createElement("p");
          p.style.color = "var(--tg-subtle)";
          p.style.fontSize = "13px";
          p.textContent = "Для этого модуля ещё нет квиза.";
          quizEl.appendChild(p);
          return;
        }

        const questions = currentQuiz.questions;

        questions.forEach((q, index) => {
          const qDiv = document.createElement("div");
          qDiv.className = "quiz-question";
          qDiv.dataset.qid = q.id;

          const titleEl = document.createElement("div");
          titleEl.className = "quiz-question-title";
          titleEl.textContent = `Вопрос ${index + 1}`;
          qDiv.appendChild(titleEl);

          const promptEl = document.createElement("div");
          promptEl.className = "quiz-question-prompt";
          const promptText = q.prompt || "";
          if (window.marked && typeof window.marked.parse === "function") {
            promptEl.innerHTML = window.marked.parse(promptText);
          } else {
            promptEl.innerHTML = escapeHtml(promptText).replace(/\\n/g, "<br>");
          }
          qDiv.appendChild(promptEl);

          const optsEl = document.createElement("div");
          optsEl.className = "quiz-options";

          const qType = (q.type || "single") === "multi" ? "multi" : "single";

          (q.options || []).forEach((opt) => {
            const optBtn = document.createElement("button");
            optBtn.type = "button";
            optBtn.className = "quiz-option";
            optBtn.dataset.optionId = String(opt.id);
            optBtn.dataset.qtype = qType;
            optBtn.innerHTML = escapeHtml(String(opt.text || ""));

            optBtn.addEventListener("click", () => {
              if (qType === "single") {
                optsEl.querySelectorAll(".quiz-option.selected").forEach((el) => {
                  el.classList.remove("selected");
                });
                optBtn.classList.add("selected");
              } else {
                optBtn.classList.toggle("selected");
              }
            });

            optsEl.appendChild(optBtn);
          });

          qDiv.appendChild(optsEl);

          const explEl = document.createElement("div");
          explEl.className = "quiz-explanation";
          explEl.style.display = "none";
          qDiv.appendChild(explEl);

          quizEl.appendChild(qDiv);
        });

        const checkBtn = document.createElement("button");
        checkBtn.type = "button";
        checkBtn.className = "quiz-check-btn";
        checkBtn.textContent = "Проверить ответы";
        checkBtn.addEventListener("click", () => checkQuizAnswers());
        quizEl.appendChild(checkBtn);

        const footer = document.createElement("div");
        footer.id = "quiz-footer";
        footer.className = "quiz-footer";
        footer.textContent = "Выберите ответы и нажмите «Проверить ответы».";
        quizEl.appendChild(footer);
      }

      function arraysEqualAsSets(a, b) {
        if (a.length !== b.length) return false;
        const sa = new Set(a);
        const sb = new Set(b);
        if (sa.size !== sb.size) return false;
        for (const v of sa) {
          if (!sb.has(v)) return false;
        }
        return true;
      }

      function checkQuizAnswers() {
        if (!quizEl || !currentQuiz || !Array.isArray(currentQuiz.questions)) return;
        const questions = currentQuiz.questions;
        let correctCount = 0;

        questions.forEach((q) => {
          const qDiv = quizEl.querySelector('.quiz-question[data-qid="' + q.id + '"]');
          if (!qDiv) return;
          const selected = Array.from(qDiv.querySelectorAll(".quiz-option.selected"));
          const selectedIds = selected.map((el) => String(el.dataset.optionId || ""));
          const correctIds = (q.options || [])
            .filter((o) => o.correct)
            .map((o) => String(o.id));

          const isCorrect = arraysEqualAsSets(selectedIds, correctIds);
          if (isCorrect) {
            correctCount++;
          }

          (q.options || []).forEach((opt) => {
            const optEl = qDiv.querySelector(
              '.quiz-option[data-option-id="' + String(opt.id) + '"]'
            );
            if (!optEl) return;
            optEl.classList.remove("correct", "incorrect");
            if (opt.correct) {
              optEl.classList.add("correct");
            }
            if (!opt.correct && selectedIds.includes(String(opt.id))) {
              optEl.classList.add("incorrect");
            }
          });

          const explEl = qDiv.querySelector(".quiz-explanation");
          if (explEl) {
            const explText = q.explanation || "";
            if (explText) {
              explEl.textContent = explText;
              explEl.style.display = "block";
            } else {
              explEl.style.display = "none";
            }
          }
        });

        const total = questions.length || 1;
        const pct = Math.round((correctCount / total) * 100);
        const footer = quizEl.querySelector("#quiz-footer");
        if (footer) {
          footer.classList.add("has-results");
          footer.textContent = `🎯 Результат: ${correctCount}/${total} (${pct}%)`;
          // Добавляем цветовую индикацию в зависимости от результата
          footer.style.borderColor = pct >= 90 ? "#16a34a" : pct >= 70 ? "#2563eb" : pct >= 50 ? "#f59e0b" : "#dc2626";
          footer.style.color = pct >= 90 ? "#16a34a" : pct >= 70 ? "#2563eb" : pct >= 50 ? "#f59e0b" : "#dc2626";
          footer.style.background = pct >= 90 
            ? "linear-gradient(135deg, rgba(22, 163, 74, 0.1), rgba(22, 163, 74, 0.05))"
            : pct >= 70 
            ? "linear-gradient(135deg, rgba(37, 99, 235, 0.1), rgba(37, 99, 235, 0.05))"
            : pct >= 50
            ? "linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(245, 158, 11, 0.05))"
            : "linear-gradient(135deg, rgba(220, 38, 38, 0.1), rgba(220, 38, 38, 0.05))";
        }

        // Сохраняем результат quiz-а
        if (currentCourseId && currentModuleId) {
          saveQuizResult(currentCourseId, currentModuleId, correctCount, total, pct);
        }

        if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.notificationOccurred === "function") {
          let type = "warning";
          const ratio = correctCount / total;
          if (ratio >= 0.9) type = "success";
          else if (ratio < 0.5) type = "error";
          try {
            tg.HapticFeedback.notificationOccurred(type);
          } catch (e) {
            console.warn("Haptic feedback failed:", e);
          }
        }
      }

      loadIndex();
    })();
  </script>
</body>
</html>
"""


@dataclasses.dataclass
class BuildWarning:
    code: str
    path: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class BuildError:
    code: str
    path: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class BuildStats:
    courses_total: int = 0
    modules_total: int = 0
    lectures_total: int = 0
    quizzes_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "courses_total": self.courses_total,
            "modules_total": self.modules_total,
            "lectures_total": self.lectures_total,
            "quizzes_total": self.quizzes_total,
        }


@dataclasses.dataclass
class BuildReport:
    build_timestamp_utc: str
    git_commit: str
    stats: BuildStats = dataclasses.field(default_factory=BuildStats)
    warnings: List[BuildWarning] = dataclasses.field(default_factory=list)
    errors: List[BuildError] = dataclasses.field(default_factory=list)

    def add_warning(self, code: str, path: Path, message: str) -> None:
        self.warnings.append(
            BuildWarning(code=code, path=str(path).replace(os.sep, "/"), message=message)
        )

    def add_error(self, code: str, path: Path, message: str) -> None:
        self.errors.append(
            BuildError(code=code, path=str(path).replace(os.sep, "/"), message=message)
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "build": {
                "timestamp_utc": self.build_timestamp_utc,
                "git_commit": self.git_commit,
                "generator": GENERATOR_NAME,
            },
            "stats": {
                **self.stats.to_dict(),
                "warnings_total": len(self.warnings),
                "errors_total": len(self.errors),
            },
            "warnings": [w.to_dict() for w in self.warnings],
            "errors": [e.to_dict() for e in self.errors],
        }


@dataclasses.dataclass
class LectureSource:
    markdown: str
    meta: Dict[str, Any]
    sha256: str


@dataclasses.dataclass
class QuizQuestion:
    id: str
    qtype: str  # "single" | "multi"
    prompt: str
    options: List[Dict[str, Any]]
    explanation: Optional[str]


class QuizParseError(Exception):
    pass


def slugify(value: str) -> str:
    """
    Делает slug из строки:
    - в нижний регистр
    - пробелы и `_` -> `-`
    - оставляем только [a-z0-9-]
    - схлопываем `--`, обрезаем по краям
    """
    value = value.strip().lower()
    value = re.sub(r"[ _]+", "-", value)
    value = re.sub(r"[^a-z0-9\-]", "", value)
    value = re.sub(r"-{2,}", "-", value)
    return value.strip("-")


def generate_course_icons_js() -> str:
    """
    Генерирует JavaScript код для COURSE_ICONS из COURSE_NAMES.
    Использует slugify для преобразования ключей курсов в course_id.
    """
    try:
        icons_list = []
        for course_key, course_info in COURSE_NAMES.items():
            if isinstance(course_info, dict) and "icon" in course_info:
                course_id = slugify(course_key)
                icon = course_info["icon"]
                # Если course_id содержит дефисы, нужно обернуть в кавычки
                if "-" in course_id:
                    key_str = f'"{course_id}"'
                else:
                    key_str = course_id
                icons_list.append((key_str, icon))
        
        # Сортируем по ключу (без учета кавычек)
        icons_list.sort(key=lambda x: x[0].strip('"'))
        
        # Формируем JavaScript объект
        items = []
        for key_str, icon in icons_list:
            # Используем json.dumps для правильного экранирования строк в JavaScript
            icon_escaped = json.dumps(icon)
            items.append(f'        {key_str}: {icon_escaped}')
        
        result = ",\n".join(items)
        # Если список пустой, возвращаем пустую строку (что даст {} в JS)
        return result
    except Exception as e:
        # В случае ошибки возвращаем пустую строку, чтобы не сломать JavaScript
        print(f"⚠️  Ошибка при генерации COURSE_ICONS: {e}", file=sys.stderr)
        return ""


def normalize_newlines(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def read_file_with_front_matter(path: Path) -> LectureSource:
    """
    Читает файл, нормализует окончания строк, вычисляет sha256 по полному
    содержимому (после нормализации) и, если есть YAML front-matter в начале,
    возвращает его как meta и текст без этого блока.
    """
    raw = path.read_text(encoding="utf-8")
    normalized = normalize_newlines(raw)
    sha = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    meta: Dict[str, Any] = {}
    body = normalized

    if normalized.startswith("---\n"):
        # front-matter заканчивается первой строкой '---' после начала
        end_idx = normalized.find("\n---", 4)
        if end_idx != -1:
            fm_text = normalized[4:end_idx]
            rest = normalized[end_idx + 4 :]
            try:
                loaded = yaml.safe_load(fm_text) or {}
                if isinstance(loaded, dict):
                    meta = loaded
            except yaml.YAMLError:
                # Ошибка в front-matter не должна ломать сборку целиком,
                # просто игнорируем meta.
                meta = {}
            # убираем возможный начальный перевод строки
            if rest.startswith("\n"):
                rest = rest[1:]
            body = rest

    return LectureSource(markdown=body, meta=meta, sha256=sha)


def extract_first_heading(markdown: str) -> Optional[str]:
    m = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def humanize_course_name(dir_name: str) -> str:
    # Преобразуем имя каталога в человекочитаемый вид: '_' / '-' -> пробел
    name = dir_name.replace("_", " ").replace("-", " ")
    # Убираем суффиксы вроде ".Interview"
    name = name.replace(".", " ")
    # Капитализация каждого слова
    return " ".join(part.capitalize() for part in name.split() if part)


def extract_anchors(markdown: str) -> List[Dict[str, str]]:
    """
    Генерирует anchors из заголовков уровня 1–3.
    """
    anchors: List[Dict[str, str]] = []
    for m in re.finditer(r"^(#{1,3})\s+(.+)$", markdown, re.MULTILINE):
        text = m.group(2).strip()
        anchor_id = slugify(text)
        if not anchor_id:
            continue
        anchors.append({"id": anchor_id, "text": text})
    return anchors


def replace_module_links_in_markdown(
    markdown: str, module_name_to_id: Dict[str, str], course_id: str
) -> str:
    """
    Заменяет ссылки на другие модули в markdown на формат TMA.
    
    Преобразует ссылки вида [Text](../NN_ModuleName/) в формат:
    [Text](content/courses/{course_id}/modules/{module_id}/lecture.json)
    
    Args:
        markdown: Исходный markdown текст
        module_name_to_id: Словарь маппинга module_name -> module_id
        course_id: ID курса
    
    Returns:
        Markdown с замененными ссылками
    """
    def replace_link(match):
        link_text = match.group(1)  # Текст ссылки
        module_name = match.group(2).rstrip('/')  # Имя модуля (например, "07_Sockets")
        
        # Ищем module_id для этого модуля
        if module_name in module_name_to_id:
            module_id = module_name_to_id[module_name]
            # Формируем URL в формате TMA
            tma_url = f"content/courses/{course_id}/modules/{module_id}/lecture.json"
            return f'[{link_text}]({tma_url})'
        else:
            # Если модуль не найден, оставляем ссылку как есть (или можно вывести предупреждение)
            return match.group(0)
    
    # Паттерн для поиска ссылок вида [Text](../NN_ModuleName/)
    # Поддерживает варианты: [Text](../07_Sockets/), [Text](../07_Sockets)
    pattern = r'\[([^\]]+)\]\(\.\./(\d{2}_[^/)]+)/?\)'
    return re.sub(pattern, replace_link, markdown)


def parse_quiz_markdown(markdown: str, base_path: Path) -> List[QuizQuestion]:
    """
    Обёртка над парсерами квизов:
    - если обнаружен новый формат чекбоксов (### + - [x]/- [ ]), используем его;
    - иначе пробуем легаси-формат (## Question N: ... + Answer Key);
    """
    # Быстрая эвристика: есть ли хотя бы один заголовок ### и строка с - [ ]
    has_checklist_heading = re.search(r"^\\s*###\\s+.+$", markdown, re.MULTILINE) is not None
    has_checklist_option = re.search(r"^\\s*-\\s*\\[[xX ]\\]", markdown, re.MULTILINE) is not None

    if has_checklist_heading and has_checklist_option:
        return _parse_quiz_checklist_format(markdown, base_path)

    # Падаем обратно на легаси-формат
    return _parse_quiz_legacy_format(markdown, base_path)


def _parse_quiz_checklist_format(markdown: str, base_path: Path) -> List[QuizQuestion]:
    """
    Новый нормативный формат (раздел 8 ТЗ):

    ### Вопрос?
    - [x] правильный
    - [ ] неправильный
    ...
    **Explanation:** ...

    или

    > Explanation: ...
    """
    lines = markdown.split("\n")
    questions: List[QuizQuestion] = []

    current_title: Optional[str] = None
    current_options: List[Tuple[str, bool]] = []
    explanation_lines: List[str] = []
    in_block_expl = False
    had_error = False

    def finalize_question(q_idx: int) -> None:
        nonlocal had_error
        if current_title is None:
            return
        if not current_options:
            had_error = True
            raise QuizParseError(
                f"Question '{current_title}' has no options in {base_path}"
            )
        correct_indices = [i for i, (_, is_correct) in enumerate(current_options) if is_correct]
        if not correct_indices:
            had_error = True
            raise QuizParseError(
                f"Question '{current_title}' has no correct options in {base_path}"
            )
        qtype = "single" if len(correct_indices) == 1 else "multi"

        options_json: List[Dict[str, Any]] = []
        for idx, (text, is_correct) in enumerate(current_options):
            option_id = chr(ord("a") + idx)
            options_json.append(
                {"id": option_id, "text": text.strip(), "correct": is_correct}
            )

        explanation: Optional[str] = None
        if explanation_lines:
            explanation = "\n".join(explanation_lines).strip()

        qid = f"q{q_idx}"
        questions.append(
            QuizQuestion(
                id=qid,
                qtype=qtype,
                prompt=current_title.strip(),
                options=options_json,
                explanation=explanation,
            )
        )

    q_counter = 0
    for line in lines:
        heading_match = re.match(r"^\s*###\s+(.+)$", line)
        if heading_match:
            # Завершаем предыдущий вопрос, если он есть
            if current_title is not None:
                q_counter += 1
                finalize_question(q_counter)
            current_title = heading_match.group(1).strip()
            current_options = []
            explanation_lines = []
            in_block_expl = False
            continue

        if current_title is None:
            # игнорируем всё до первого ### вопроса
            continue

        # Вариант ответа: - [x] text / - [ ] text
        option_match = re.match(r"^\s*-\s*\[([xX ])\]\s*(.+)$", line)
        if option_match:
            mark = option_match.group(1)
            text = option_match.group(2)
            current_options.append((text, mark.lower() == "x"))
            in_block_expl = False
            continue

        # Explanation в виде **Explanation:**
        expl_match = re.match(r"^\s*\*\*Explanation:\*\*\s*(.*)$", line)
        if expl_match:
            explanation_lines = [expl_match.group(1)]
            in_block_expl = False
            continue

        # Explanation в виде blockquote
        block_match = re.match(r"^\s*>\s*Explanation:\s*(.*)$", line)
        if block_match:
            explanation_lines = [block_match.group(1)]
            in_block_expl = True
            continue

        if in_block_expl:
            # Продолжаем собирать blockquote Explanation
            cont_match = re.match(r"^\s*>\s*(.*)$", line)
            if cont_match:
                explanation_lines.append(cont_match.group(1))
                continue
            else:
                in_block_expl = False

    if current_title is not None:
        q_counter += 1
        finalize_question(q_counter)

    if not questions and not had_error:
        raise QuizParseError(f"No questions found in {base_path}")

    return questions


def _parse_quiz_legacy_format(markdown: str, base_path: Path) -> List[QuizQuestion]:
    """
    Легаси-формат квизов, использовавшийся для HTML-генератора:

    ## Question 1:
    Текст...

    A) ...
    B) ...
    C) ...
    D) ...
    ---

    ## Answer Key
    | # | Answer | Explanation |
    | 1 | C | ... |
    """
    questions: List[QuizQuestion] = []

    # Разделяем по вопросам
    sections = re.split(r"#{2,3}\s+(?:Question|Вопрос)\s+(\d+):?", markdown)
    # sections: [преамбула, номер1, контент1, номер2, контент2, ...]
    raw_questions: List[Dict[str, Any]] = []

    for i in range(1, len(sections) - 1, 2):
        try:
            q_num = int(sections[i])
        except ValueError:
            continue
        section_content = sections[i + 1]

        # Останавливаемся, если внутри попалась секция Answer Key
        for stop_marker in [
            "## Answer Key",
            "## Ключ к Ответам",
            "## Ключ к ответам",
            "## Ответы",
        ]:
            if stop_marker in section_content:
                section_content = section_content.split(stop_marker)[0]
                break

        lines = section_content.strip().split("\n")
        if not lines:
            continue
        title_line = lines[0].strip()
        title = title_line if title_line else f"Вопрос {q_num}"

        full_text = "\n".join(lines[1:]).strip()

        # Варианты начинаются с A)
        options_match = re.search(r"\n\s*A\)", "\n" + full_text)
        if options_match:
            question_text = full_text[: options_match.start() - 1].strip()
            options_text = full_text[options_match.start() - 1 :].strip()
        else:
            question_text = ""
            options_text = full_text

        option_pattern = r"([A-D])\)\s*(.+?)(?=\n[A-D]\)|\n---|\n\n\n|\Z)"
        opts: List[Tuple[str, str]] = []
        for match in re.finditer(option_pattern, options_text, re.DOTALL):
            letter = match.group(1)
            text = match.group(2).strip()
            opts.append((letter, text))

        if len(opts) != 4:
            continue

        raw_questions.append(
            {
                "number": q_num,
                "title": title,
                "question_text": question_text,
                "options": opts,
            }
        )

    if not raw_questions:
        raise QuizParseError(f"No legacy questions found in {base_path}")

    # Парсим секцию Answer Key
    answer_key_match = re.search(
        r"##\s*(?:Answer Key|Ключ к Ответам|Ключ к ответам|Ответы)\s*\n(.+?)(?=\n## |\Z)",
        markdown,
        re.DOTALL | re.IGNORECASE,
    )
    answers: Dict[int, Tuple[str, str]] = {}
    if answer_key_match:
        answer_section = answer_key_match.group(1)
        # Табличный формат
        row_pattern = r"\|\s*(\d+)\s*\|\s*([A-D])\s*\|\s*(.+?)\s*\|"
        for m in re.finditer(row_pattern, answer_section):
            qn = int(m.group(1))
            letter = m.group(2)
            explanation = m.group(3).strip()
            answers[qn] = (letter, explanation)

        if not answers:
            # Формат списка: N. **X** - Explanation
            list_pattern = r"(\d+)\.\s*\*\*([A-D])\*\*\s*[-—]\s*(.+?)(?=\n\d+\.|\Z)"
            for m in re.finditer(list_pattern, answer_section, re.DOTALL):
                qn = int(m.group(1))
                letter = m.group(2)
                explanation = re.sub(r"\n+", " ", m.group(3).strip())
                answers[qn] = (letter, explanation)

    # Собираем итоговый список вопросов
    for idx, rq in enumerate(raw_questions, start=1):
        qn = rq["number"]
        title = rq["title"]
        qtext = rq["question_text"]
        opts = rq["options"]

        prompt_parts = [title]
        if qtext:
            prompt_parts.append("")
            prompt_parts.append(qtext)
        prompt = "\n".join(prompt_parts).strip()

        correct_letter = None
        explanation = None
        if qn in answers:
            correct_letter, explanation = answers[qn]

        option_json: List[Dict[str, Any]] = []
        correct_index = None
        for i, (letter, text) in enumerate(opts):
            oid = chr(ord("a") + i)
            is_correct = letter == correct_letter
            if is_correct:
                correct_index = i
            option_json.append({"id": oid, "text": text, "correct": is_correct})

        if correct_letter is not None and correct_index is None:
            # Ответ есть, но буква не совпала с вариантами
            raise QuizParseError(
                f"Answer key refers to option '{correct_letter}' which is missing in question {qn} ({base_path})"
            )

        qtype = "single"
        qid = f"q{idx}"
        questions.append(
            QuizQuestion(
                id=qid,
                qtype=qtype,
                prompt=prompt,
                options=option_json,
                explanation=explanation,
            )
        )

    if not questions:
        raise QuizParseError(f"No parsed legacy questions in {base_path}")

    return questions


def get_git_commit(repo_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def discover_courses(src_dir: Path, report: BuildReport) -> List[Path]:
    if not src_dir.exists():
        report.add_error(
            code="SRC_NOT_FOUND",
            path=src_dir,
            message=f"Source directory not found: {src_dir}",
        )
        return []

    courses: List[Path] = []
    for entry in sorted(src_dir.iterdir()):
        if entry.is_dir():
            courses.append(entry)
    return courses


def discover_modules(course_dir: Path, report: BuildReport) -> List[Path]:
    modules: List[Path] = []
    for entry in sorted(course_dir.iterdir()):
        if not entry.is_dir():
            continue
        if not re.match(r"^\d{2}_", entry.name):
            continue
        modules.append(entry)
    return modules


def build(
    src_dir: Path,
    out_dir: Path,
    strict: bool,
    clean: bool,
    course_filter: Optional[str],
    emit_anchors: bool,
    no_timestamp: bool,
) -> Tuple[BuildReport, int]:
    repo_root = Path(__file__).resolve().parents[1]

    timestamp_utc = (
        "1970-01-01T00:00:00Z"
        if no_timestamp
        else dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    )
    git_commit = get_git_commit(repo_root)

    report = BuildReport(build_timestamp_utc=timestamp_utc, git_commit=git_commit)

    # Корень JSON-контента совпадает с каталогом out_dir.
    # Внутри него мы создаём только:
    #   - index.json
    #   - build-report.json
    #   - courses/...
    content_root = out_dir
    if clean and content_root.exists():
        import shutil

        print(f"🧹 Очищаю JSON-контент в каталоге: {content_root}")
        for child in content_root.iterdir():
            # Удаляем только нашу структуру, не трогая index.html/app.js и т.п.
            if child.is_dir() and child.name == "courses":
                shutil.rmtree(child)
            elif child.is_file() and child.suffix == ".json":
                child.unlink()

    ensure_dir(content_root)
    courses_root = content_root / "courses"
    ensure_dir(courses_root)

    print(f"📂 Источник: {src_dir}")
    print(f"📦 Выход:    {content_root}")

    all_courses = discover_courses(src_dir, report)
    course_id_map: Dict[str, Path] = {}
    index_courses: List[Dict[str, Any]] = []

    # Для проверки существования файлов по url_*
    generated_files: set[Path] = set()

    for course_dir in all_courses:
        course_name = course_dir.name
        course_id = slugify(course_name)
        if not course_id:
            report.add_warning(
                code="COURSE_ID_EMPTY",
                path=course_dir,
                message="Could not generate non-empty course_id from directory name; skipping course",
            )
            continue

        if course_id in course_id_map:
            report.add_error(
                code="COURSE_ID_CONFLICT",
                path=course_dir,
                message=f"Duplicate course_id '{course_id}', first used by {course_id_map[course_id]}",
            )
            continue

        course_id_map[course_id] = course_dir

    # Фильтрация по --course (course_id)
    if course_filter:
        if course_filter not in course_id_map:
            report.add_error(
                code="COURSE_NOT_FOUND",
                path=src_dir,
                message=f"Course with id '{course_filter}' not found",
            )
        else:
            # Оставляем только один курс
            selected_dir = course_id_map[course_filter]
            course_id_map = {course_filter: selected_dir}

    # Строим каждый курс
    for course_id, course_dir in sorted(course_id_map.items(), key=lambda kv: kv[0]):
        print(f"\n📘 Курс: {course_dir.name} (course_id={course_id})")
        modules = discover_modules(course_dir, report)

        # Валидация номеров модулей
        module_nums: Dict[int, Path] = {}
        for mdir in modules:
            m = re.match(r"^(\d{2})_", mdir.name)
            if not m:
                report.add_error(
                    code="MODULE_NAME_INVALID",
                    path=mdir,
                    message="Module directory does not match ^\\d{2}_.+",
                )
                continue
            num = int(m.group(1))
            if num in module_nums:
                report.add_error(
                    code="MODULE_NO_CONFLICT",
                    path=mdir,
                    message=f"Duplicate module number {num} also used by {module_nums[num].name}",
                )
            else:
                module_nums[num] = mdir

        # Пересобираем модульный список только из валидных модулей
        valid_modules = [mdir for num, mdir in sorted(module_nums.items())]

        if not valid_modules:
            report.add_warning(
                code="NO_VALID_MODULES",
                path=course_dir,
                message="Course has no valid modules matching ^\\d{2}_.+",
            )
            continue

        # Метаданные курса
        # Попробуем взять заголовок из README.md, иначе — humanized имя каталога
        course_title = humanize_course_name(course_dir.name)
        readme_path = course_dir / "README.md"
        if readme_path.exists():
            src = read_file_with_front_matter(readme_path)
            heading = extract_first_heading(src.markdown)
            if heading:
                course_title = heading

        course_out_dir = courses_root / course_id
        ensure_dir(course_out_dir)
        modules_json_path = course_out_dir / "modules.json"
        course_json_path = course_out_dir / "course.json"

        modules_index: List[Dict[str, Any]] = []

        # Для уникальности module_id внутри курса
        module_id_counts: Dict[str, int] = {}
        
        # Маппинг module_name -> module_id для замены ссылок
        module_name_to_id: Dict[str, str] = {}

        # Первый проход: собираем маппинг module_name -> module_id
        for mdir in valid_modules:
            module_name = mdir.name
            m = re.match(r"^(\d{2})_(.+)$", module_name)
            if not m:
                continue
            module_no = int(m.group(1))
            module_name_rest = m.group(2)
            module_id_base = slugify(module_name_rest)
            if not module_id_base:
                module_id_base = f"m{module_no}"

            module_id = module_id_base
            if module_id in module_id_counts:
                module_id_counts[module_id] += 1
                suffix = module_id_counts[module_id]
                new_module_id = f"{module_id}-{suffix}"
                module_id = new_module_id
            else:
                module_id_counts[module_id] = 1
            
            # Сохраняем маппинг
            module_name_to_id[module_name] = module_id

        # Второй проход: обрабатываем модули и заменяем ссылки
        for mdir in valid_modules:
            module_name = mdir.name
            m = re.match(r"^(\d{2})_(.+)$", module_name)
            if not m:
                continue
            module_no = int(m.group(1))
            module_name_rest = m.group(2)
            
            # Используем module_id из маппинга, собранного в первом проходе
            module_id = module_name_to_id.get(module_name)
            if not module_id:
                # Если по какой-то причине модуль не найден в маппинге, вычисляем заново
                module_id_base = slugify(module_name_rest)
                if not module_id_base:
                    module_id_base = f"m{module_no}"
                module_id = module_id_base
                if module_id in module_id_counts:
                    module_id_counts[module_id] += 1
                    suffix = module_id_counts[module_id]
                    new_module_id = f"{module_id}-{suffix}"
                    report.add_warning(
                        code="MODULE_SLUG_CONFLICT",
                        path=mdir,
                        message=f"module_id conflict for '{module_id}', resolved as '{new_module_id}'",
                    )
                    module_id = new_module_id
                else:
                    module_id_counts[module_id] = 1

            lecture_path = mdir / "lecture.md"
            quiz_path = mdir / "quiz.md"

            if not lecture_path.exists():
                report.add_error(
                    code="LECTURE_MISSING",
                    path=mdir,
                    message="lecture.md not found in module",
                )
                continue

            print(f"  📄 Модуль {module_no:02d}: {module_name_rest} (module_id={module_id})")

            # Чтение и метаданные лекции
            lecture_src = read_file_with_front_matter(lecture_path)
            
            # Заменяем ссылки на другие модули в markdown
            processed_markdown = replace_module_links_in_markdown(
                lecture_src.markdown, module_name_to_id, course_id
            )
            
            lecture_title = (
                lecture_src.meta.get("title")
                if isinstance(lecture_src.meta.get("title"), str)
                else None
            )
            if not lecture_title:
                heading = extract_first_heading(processed_markdown)
                if heading:
                    lecture_title = heading
                else:
                    # fallback к имени модуля
                    lecture_title = module_name_rest.replace("_", " ").replace("-", " ")

            duration_min = lecture_src.meta.get("duration_min")
            tags = lecture_src.meta.get("tags")
            if not isinstance(tags, list):
                tags = None

            anchors = extract_anchors(processed_markdown) if emit_anchors else None

            # Генерация lecture.json
            module_out_dir = course_out_dir / "modules" / module_id
            ensure_dir(module_out_dir)
            lecture_json_path = module_out_dir / "lecture.json"

            lecture_json: Dict[str, Any] = {
                "schema_version": SCHEMA_VERSION,
                "course_id": course_id,
                "module_no": module_no,
                "module_id": module_id,
                "title": lecture_title,
                "markdown": processed_markdown,
                "source": {
                    "path": str(lecture_path.relative_to(repo_root)).replace(os.sep, "/"),
                    "sha256": lecture_src.sha256,
                },
            }
            if duration_min is not None:
                lecture_json["duration_min"] = duration_min
            if tags is not None:
                lecture_json["tags"] = tags
            if anchors:
                lecture_json["anchors"] = anchors

            with lecture_json_path.open("w", encoding="utf-8") as f:
                json.dump(lecture_json, f, ensure_ascii=False, indent=2)
            generated_files.add(lecture_json_path)
            report.stats.lectures_total += 1
            report.stats.modules_total += 1

            has_quiz = False
            quiz_json_url: Optional[str] = None

            if quiz_path.exists():
                quiz_src = read_file_with_front_matter(quiz_path)
                quiz_title = (
                    quiz_src.meta.get("title")
                    if isinstance(quiz_src.meta.get("title"), str)
                    else None
                )
                if not quiz_title:
                    quiz_title = f"Квиз: {lecture_title}"

                try:
                    questions = parse_quiz_markdown(quiz_src.markdown, quiz_path)
                except QuizParseError as e:
                    # strict → ошибка; lenient → warning и модуль без квиза
                    if strict:
                        report.add_error(
                            code="QUIZ_PARSE_ERROR",
                            path=quiz_path,
                            message=str(e),
                        )
                    else:
                        report.add_warning(
                            code="QUIZ_PARSE_SKIPPED",
                            path=quiz_path,
                            message=str(e),
                        )
                else:
                    # успешный парсинг
                    has_quiz = True
                    quiz_json_path = module_out_dir / "quiz.json"
                    quiz_json_url = (
                        f"courses/{course_id}/modules/{module_id}/quiz.json"
                    )

                    questions_json: List[Dict[str, Any]] = []
                    for q in questions:
                        questions_json.append(
                            {
                                "id": q.id,
                                "type": q.qtype,
                                "prompt": q.prompt,
                                "options": q.options,
                                **(
                                    {"explanation": q.explanation}
                                    if q.explanation is not None
                                    else {}
                                ),
                            }
                        )

                    quiz_json: Dict[str, Any] = {
                        "schema_version": SCHEMA_VERSION,
                        "course_id": course_id,
                        "module_no": module_no,
                        "module_id": module_id,
                        "title": quiz_title,
                        "questions": questions_json,
                        "source": {
                            "path": str(quiz_path.relative_to(repo_root)).replace(
                                os.sep, "/"
                            ),
                            "sha256": quiz_src.sha256,
                        },
                    }

                    with quiz_json_path.open("w", encoding="utf-8") as f:
                        json.dump(quiz_json, f, ensure_ascii=False, indent=2)
                    generated_files.add(quiz_json_path)
                    report.stats.quizzes_total += 1

            # Элемент в modules.json
            module_entry: Dict[str, Any] = {
                "module_no": module_no,
                "module_id": module_id,
                "title": lecture_title,
                "has_quiz": has_quiz,
                "url_lecture": f"courses/{course_id}/modules/{module_id}/lecture.json",
            }
            if duration_min is not None:
                module_entry["duration_min"] = duration_min
            if tags is not None:
                module_entry["tags"] = tags
            if has_quiz and quiz_json_url is not None:
                module_entry["url_quiz"] = quiz_json_url

            modules_index.append(module_entry)

        # Сортировка модулей по module_no
        modules_index.sort(key=lambda m: m["module_no"])

        # course.json
        course_json: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "course_id": course_id,
            "title": course_title,
            "source_path": str(course_dir.relative_to(repo_root)).replace(os.sep, "/"),
            "modules_count": len(modules_index),
            "url_modules": f"courses/{course_id}/modules.json",
        }

        with course_json_path.open("w", encoding="utf-8") as f:
            json.dump(course_json, f, ensure_ascii=False, indent=2)
        generated_files.add(course_json_path)

        # modules.json
        modules_json: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "course_id": course_id,
            "modules": modules_index,
        }

        with modules_json_path.open("w", encoding="utf-8") as f:
            json.dump(modules_json, f, ensure_ascii=False, indent=2)
        generated_files.add(modules_json_path)

        report.stats.courses_total += 1

        # Получаем информацию о разделах из COURSE_NAMES
        course_info = COURSE_NAMES.get(course_dir.name, {})
        sections = []
        if isinstance(course_info, dict):
            sections = list(course_info.get("sections", set()))

        # Элемент для index.json
        course_entry = {
            "course_id": course_id,
            "title": course_title,
            "modules_count": len(modules_index),
            "url_course": f"courses/{course_id}/course.json",
            "url_modules": f"courses/{course_id}/modules.json",
        }
        if sections:
            course_entry["sections"] = sorted(sections)
        index_courses.append(course_entry)

    # index.json
    index_courses.sort(key=lambda c: c["title"])
    index_json: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "build": {
            "timestamp_utc": timestamp_utc,
            "git_commit": git_commit,
            "generator": GENERATOR_NAME,
        },
        "courses": index_courses,
    }

    index_json_path = content_root / "index.json"
    with index_json_path.open("w", encoding="utf-8") as f:
        json.dump(index_json, f, ensure_ascii=False, indent=2)
    generated_files.add(index_json_path)

    # build-report.json
    build_report_path = content_root / "build-report.json"
    with build_report_path.open("w", encoding="utf-8") as f:
        json.dump(report.to_json(), f, ensure_ascii=False, indent=2)
    generated_files.add(build_report_path)

    # index.html оболочки mini app
    index_html_path = out_dir / "index.html"
    # Генерируем COURSE_ICONS из COURSE_NAMES
    try:
        course_icons_js = generate_course_icons_js()
        if "{COURSE_ICONS_PLACEHOLDER}" not in INDEX_HTML_TEMPLATE:
            report.add_error(
                code="TEMPLATE_PLACEHOLDER_MISSING",
                path=index_html_path,
                message="Placeholder {COURSE_ICONS_PLACEHOLDER} not found in INDEX_HTML_TEMPLATE",
            )
            course_icons_js = ""  # Fallback to empty
        index_html_content = INDEX_HTML_TEMPLATE.replace(
            "{COURSE_ICONS_PLACEHOLDER}", course_icons_js
        )
        # Проверяем, что замена произошла
        if "{COURSE_ICONS_PLACEHOLDER}" in index_html_content:
            report.add_error(
                code="TEMPLATE_PLACEHOLDER_NOT_REPLACED",
                path=index_html_path,
                message="Placeholder {COURSE_ICONS_PLACEHOLDER} was not replaced in generated HTML",
            )
            # Fallback: заменяем вручную
            index_html_content = index_html_content.replace(
                "{COURSE_ICONS_PLACEHOLDER}", ""
            )
    except Exception as e:
        report.add_error(
            code="COURSE_ICONS_GENERATION_ERROR",
            path=index_html_path,
            message=f"Error generating COURSE_ICONS: {e}",
        )
        # Fallback: используем пустой объект
        index_html_content = INDEX_HTML_TEMPLATE.replace(
            "{COURSE_ICONS_PLACEHOLDER}", ""
        )
    
    with index_html_path.open("w", encoding="utf-8") as f:
        f.write(index_html_content)

    # Простая проверка url_* → существующие файлы
    def check_url(path_value: str, container_path: Path) -> None:
        target = out_dir / path_value
        if target not in generated_files and not target.exists():
            report.add_error(
                code="URL_TARGET_MISSING",
                path=container_path,
                message=f"url '{path_value}' does not point to an existing file",
            )

    # Проверяем index.json
    for c in index_courses:
        check_url(c["url_course"], index_json_path)
        check_url(c["url_modules"], index_json_path)

    # Проверяем course/modules json по диску
    for course_id, course_dir in course_id_map.items():
        course_out_dir = courses_root / course_id
        course_json_path = course_out_dir / "course.json"
        modules_json_path = course_out_dir / "modules.json"
        if course_json_path.exists():
            with course_json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if "url_modules" in data:
                check_url(data["url_modules"], course_json_path)
        if modules_json_path.exists():
            with modules_json_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            for m in data.get("modules", []):
                if "url_lecture" in m:
                    check_url(m["url_lecture"], modules_json_path)
                if m.get("has_quiz") and "url_quiz" in m:
                    check_url(m["url_quiz"], modules_json_path)

    # Логирование результатов
    print("\n📊 Статистика сборки:")
    print(f"   Курсы:   {report.stats.courses_total}")
    print(f"   Модули:  {report.stats.modules_total}")
    print(f"   Лекции:  {report.stats.lectures_total}")
    print(f"   Квизы:   {report.stats.quizzes_total}")
    print(f"   Warning: {len(report.warnings)}")
    print(f"   Errors:  {len(report.errors)}")
    print(f"\n📁 Индекс: {index_json_path}")
    print(f"📝 Отчёт:  {build_report_path}")

    if report.errors:
        for err in report.errors:
            print(f"❌ [{err.code}] {err.path}: {err.message}")
        # В strict-режиме любая ошибка контента даёт код 2
        if strict:
            return report, 2
        # В lenient-режиме ошибки не валят сборку полностью, но сигнализируем кодом 2 только для серьёзных проблем
        # Здесь можно было бы дифференцировать, но пока оставим 0 для lenient.
        return report, 0

    return report, 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Сборка контента для Telegram Mini App (tma/...)"
    )
    parser.add_argument(
        "--src",
        default="Courses",
        help="Каталог с исходными курсами (по умолчанию: Courses)",
    )
    parser.add_argument(
        "--out",
        default="tma",
        help="Каталог для вывода контента (по умолчанию: tma)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Удалить старый JSON-контент (index.json, build-report.json, courses/...) в каталоге out перед сборкой",
    )
    strict_group = parser.add_mutually_exclusive_group()
    strict_group.add_argument(
        "--strict",
        dest="strict",
        action="store_true",
        help="Строгий режим (по умолчанию)",
    )
    strict_group.add_argument(
        "--lenient",
        dest="strict",
        action="store_false",
        help="Более мягкий режим: ошибки парсинга quiz.md считаются предупреждениями",
    )
    parser.set_defaults(strict=True)

    parser.add_argument(
        "--course",
        dest="course_filter",
        help="Собрать только один курс по его course_id (slug директории)",
    )
    parser.add_argument(
        "--emit-anchors",
        action="store_true",
        help="Генерировать anchors из заголовков лекций",
    )
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Не использовать текущий timestamp (детерминированные сборки)",
    )

    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    # Определяем корень репозитория относительно build_tma/build.py
    repo_root = Path(__file__).resolve().parents[1]

    src_path = Path(args.src)
    if not src_path.is_absolute():
        src_path = repo_root / src_path

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = repo_root / out_path

    try:
        _, exit_code = build(
            src_dir=src_path,
            out_dir=out_path,
            strict=args.strict,
            clean=args.clean,
            course_filter=args.course_filter,
            emit_anchors=args.emit_anchors,
            no_timestamp=args.no_timestamp,
        )
    except Exception as exc:
        print(f"❌ Необработанное исключение при сборке: {exc}", file=sys.stderr)
        return 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())


