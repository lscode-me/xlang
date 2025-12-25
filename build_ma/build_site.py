#!/usr/bin/env python3
"""
Build static Telegram Mini App for RU→TR Vocabulary Quiz.
Generates HTML files and assets in html/ma/
"""
import json
import shutil
import sys
import time
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

# Import validation to ensure questions are valid before building
import validate_questions


def load_questions_from_jsonl(filepath: Path) -> List[Dict[str, Any]]:
    """Load questions from a JSONL file"""
    questions = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                questions.append(obj)
            except json.JSONDecodeError:
                continue  # Skip invalid lines (should be caught by validation)
    return questions


def find_jsonl_files(base_dir: Path, content_type: str) -> Dict[str, List[Path]]:
    """
    Find all JSONL files organized by level.
    Args:
        base_dir: Repository root
        content_type: 'Words' or 'Phrases'
    Returns: {level: [Path, ...], ...}
    """
    structure = defaultdict(list)
    
    for level in ["A1", "A2", "B1"]:
        level_dir = base_dir / "Vocabulary" / f"RU-TR_{content_type}" / level
        if not level_dir.exists():
            continue
        
        for jsonl_file in level_dir.glob("**/*.jsonl"):
            structure[level].append(jsonl_file)
    
    return structure


def generate_quiz_page(level: str, questions_count: int, content_type: str) -> str:
    """Generate HTML for a quiz page"""
    import time
    cache_buster = int(time.time())
    type_label = "Слова" if content_type == "Words" else "Фразы"
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Quiz: {level} · {type_label}</title>
  <link rel="stylesheet" href="../../assets/app.css?v={cache_buster}">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <div class="app">
    <header>
      <div class="header-left">
        <h1 class="title">RU→TR {type_label} · {level}</h1>
      </div>
      <div class="header-right">
        <div class="score">Счёт: <span id="score">0</span></div>
      </div>
    </header>

    <main id="main">
      <!-- Start screen -->
      <div id="startScreen" class="screen">
        <div class="card">
          <h2>Готовы начать?</h2>
          <p>Вам будет предложено 5 вопросов на перевод с русского на турецкий.</p>
          <p class="info">Уровень: <strong>{level}</strong><br>Всего вопросов в базе: <strong>{questions_count}</strong></p>
          <button id="startBtn" class="btn btn-primary">Начать тест</button>
        </div>
      </div>

      <!-- Quiz screen -->
      <div id="quizScreen" class="screen hidden">
        <div class="progress-container">
          <div class="progress-bar">
            <div id="progressFill" class="progress-fill"></div>
          </div>
          <div class="progress-counter"><span id="currentQ">1</span>/<span id="totalQ">5</span></div>
        </div>
        
        <p id="questionText" class="question-text"></p>
        
        <div id="answers" class="answers">
          <!-- Answers will be inserted here -->
        </div>
        
        <div id="explanation" class="explanation hidden">
          <p id="explanationText"></p>
        </div>
        
        <button id="nextBtn" class="btn btn-primary hidden">Следующий вопрос</button>
      </div>

      <!-- Results screen -->
      <div id="resultsScreen" class="screen hidden">
        <div class="card results-card">
          <h2>Результаты</h2>
          <div class="results-score">
            <div class="score-circle">
              <span id="finalScore">0</span>
              <span class="score-total">/ 5</span>
            </div>
          </div>
          <p id="resultsMessage" class="results-message"></p>
          <div class="results-stats">
            <div class="stat">
              <div class="stat-label">Правильно</div>
              <div id="correctCount" class="stat-value">0</div>
            </div>
            <div class="stat">
              <div class="stat-label">Неправильно</div>
              <div id="wrongCount" class="stat-value">0</div>
            </div>
            <div class="stat">
              <div class="stat-label">Точность</div>
              <div id="accuracy" class="stat-value">0%</div>
            </div>
          </div>
          <div class="results-actions">
            <button id="playAgainBtn" class="btn btn-primary">Сыграть ещё</button>
            <a href="../../index.html" class="btn btn-secondary">Выбрать другой уровень</a>
          </div>
        </div>
      </div>
    </main>
  </div>

  <script src="../../assets/storage.js?v={cache_buster}"></script>
  <script src="../../assets/app.js?v={cache_buster}" data-questions="./questions.json" data-level="{level}"></script>
</body>
</html>'''


def generate_catalog_page(words_structure: Dict[str, List[Path]], phrases_structure: Dict[str, List[Path]]) -> str:
    """Generate HTML for catalog/index page"""
    
    # Generate Words section
    words_html = []
    for level in ["A1", "A2", "B1"]:
        if level in words_structure:
            words_html.append(f'''
        <a href="RU-TR_Words/{level}/index.html" class="level-card" data-level="{level}">
          <div class="level-content">
            <div class="level-badge">{level}</div>
            <div class="level-stats" id="stats-words-{level}">
              <span class="stat-label">Ваш прогресс:</span>
              <span class="stat-value">—</span>
            </div>
          </div>
        </a>''')
    
    # Generate Phrases section
    phrases_html = []
    for level in ["A1", "A2", "B1"]:
        if level in phrases_structure:
            phrases_html.append(f'''
        <a href="RU-TR_Phrases/{level}/index.html" class="level-card" data-level="{level}">
          <div class="level-content">
            <div class="level-badge">{level}</div>
            <div class="level-stats" id="stats-phrases-{level}">
              <span class="stat-label">Ваш прогресс:</span>
              <span class="stat-value">—</span>
            </div>
          </div>
        </a>''')
    
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RU→TR Vocabulary Quiz</title>
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <style>
    :root {{
      --bg: #0b1220;
      --card: #121b2f;
      --text: #e9eefc;
      --muted: #9fb0d1;
      --accent: #6aa9ff;
      --border: rgba(255,255,255,0.08);
      --shadow: 0 10px 30px rgba(0,0,0,0.35);
      --radius: 18px;
    }}
    
    * {{ box-sizing: border-box; }}
    
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      background: radial-gradient(1200px 700px at 20% 0%, rgba(106,169,255,0.18), transparent 60%),
                  radial-gradient(900px 600px at 90% 20%, rgba(40,209,124,0.12), transparent 55%),
                  var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 20px;
    }}
    
    .container {{
      max-width: 700px;
      margin: 0 auto;
    }}
    
    h1 {{
      font-size: 2rem;
      margin: 0 0 10px 0;
      text-align: center;
    }}
    
    .subtitle {{
      text-align: center;
      color: var(--muted);
      margin-bottom: 40px;
    }}
    
    .levels-grid {{
      display: grid;
      gap: 12px;
    }}
    
    .level-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px 20px;
      text-decoration: none;
      color: var(--text);
      transition: all 0.2s;
      display: block;
    }}
    
    .level-card:hover {{
      transform: translateY(-2px);
      box-shadow: var(--shadow);
      border-color: var(--accent);
    }}
    
    .level-badge {{
      font-size: 1.8rem;
      font-weight: 700;
      color: var(--accent);
    }}
    
    .level-content {{
      display: flex;
      align-items: center;
      gap: 16px;
    }}
    
    .level-stats {{
      font-size: 0.9rem;
      white-space: nowrap;
    }}
    
    .stat-label {{
      color: var(--muted);
    }}
    
    .stat-value {{
      color: var(--accent);
      font-weight: 600;
      margin-left: 4px;
    }}
    
    .level-meta {{
      font-size: 0.9rem;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    
    .user-pill {{
      font-size: 0.75rem;
      padding: 4px 10px;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--muted);
      max-width: 40%;
      text-overflow: ellipsis;
      white-space: nowrap;
      overflow: hidden;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;">
      <div>
        <h1 style="margin: 0 0 4px 0; font-size: 1.5rem;">🇷🇺 → 🇹🇷</h1>
        <div style="font-size: 1.1rem;">Vocabulary Quiz</div>
      </div>
      <div style="text-align: right;">
        <div id="user-pill" style="font-size: 0.85rem; color: var(--muted); margin-bottom: 4px;"></div>
        <div style="font-size: 0.95rem;">
          🔥 <span style="color: var(--muted);">Дней:</span> <span id="unique-days" style="color: var(--accent); font-weight: 600;">0</span>
        </div>
      </div>
    </div>
    
    {'<h2 style="margin: 30px 0 15px 0; font-size: 1.3rem;">📝 Тесты по словам</h2>' if words_html else ''}
    <div class="levels-grid">
      {''.join(words_html) if words_html else '<p style="color: var(--muted); text-align: center;">Нет доступных тестов</p>'}
    </div>
    
    {'<h2 style="margin: 30px 0 15px 0; font-size: 1.3rem;">💬 Тесты по фразам</h2>' if phrases_html else ''}
    <div class="levels-grid">
      {''.join(phrases_html) if phrases_html else '<p style="color: var(--muted); text-align: center;">Нет доступных тестов</p>'}
    </div>
  </div>
  
  <script src="./assets/storage.js?v={int(time.time())}"></script>
  <script>
    // Telegram WebApp integration
    if (window.Telegram && window.Telegram.WebApp) {{
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.disableVerticalSwipes();
      tg.isClosingConfirmationEnabled = true;
      
      // Show user info
      const userPillEl = document.getElementById('user-pill');
      if (tg.initDataUnsafe && tg.initDataUnsafe.user && userPillEl) {{
        const u = tg.initDataUnsafe.user;
        const name = [u.first_name, u.last_name].filter(Boolean).join(' ') || u.username || 'Пользователь';
        userPillEl.textContent = '@' + (u.username || name);
      }} else if (userPillEl) {{
        userPillEl.textContent = 'Гость';
      }}
    }}
    
    // Load and display stats for each level and type
    (async function() {{
      const levels = ['A1', 'A2', 'B1'];
      const types = ['words', 'phrases'];
      
      // Load unique days counter
      try {{
        const globalKey = 'quiz:global:days-counter';
        
        // Check cache first
        const cached = storage._cache && storage._cache[globalKey];
        const uniqueDaysEl = document.getElementById('unique-days');
        
        if (cached && Date.now() - cached.timestamp < storage._cacheTTL) {{
          try {{
            const stats = JSON.parse(cached.value);
            console.log('[catalog] Unique days from cache:', stats.uniqueDays);
            if (uniqueDaysEl) {{
              uniqueDaysEl.textContent = stats.uniqueDays || 0;
            }}
          }} catch (e) {{
            console.error('[catalog] Error parsing cached unique days:', e);
          }}
        }}
        
        // Always load from storage to get latest value
        const globalData = await storage.get(globalKey);
        console.log('[catalog] Unique days from storage:', globalData);
        
        if (globalData) {{
          const stats = JSON.parse(globalData);
          console.log('[catalog] Parsed unique days:', stats);
          if (uniqueDaysEl) {{
            uniqueDaysEl.textContent = stats.uniqueDays || 0;
          }}
        }} else {{
          console.log('[catalog] No unique days data found');
          if (uniqueDaysEl) uniqueDaysEl.textContent = '0';
        }}
      }} catch (e) {{
        console.error('Failed to load unique days:', e);
      }}
      
      // Set default '-' or cached value for all levels immediately
      types.forEach(type => {{
        levels.forEach(level => {{
          const statsEl = document.getElementById(`stats-${{type}}-${{level}}`);
          if (statsEl) {{
            const valueEl = statsEl.querySelector('.stat-value');
            if (valueEl) {{
              // Check if we have cached value
              const storageKey = `quiz:ru-tr-${{type}}:${{level.toLowerCase()}}`;
              console.log(`[catalog] Checking cache for level ${{level}} (${{type}}), key: "${{storageKey}}"`);
              const cached = storage._cache && storage._cache[storageKey];
              
              if (cached && Date.now() - cached.timestamp < storage._cacheTTL) {{
                try {{
                  const stats = JSON.parse(cached.value);
                  let avgPercent = null;
                  if (stats.totalCorrect !== undefined && stats.totalQuestions > 0) {{
                    avgPercent = Math.round((stats.totalCorrect / stats.totalQuestions) * 100);
                  }} else if (stats.lastScore !== undefined) {{
                    avgPercent = Math.round((stats.lastScore / 5) * 100);
                  }}
                  
                  // Display cached value (will be cleared by async loader if corrupted)
                  if (avgPercent !== null) {{
                    valueEl.textContent = `${{avgPercent}}%`;
                  }} else {{
                    valueEl.textContent = '—';
                  }}
                }} catch (e) {{
                  valueEl.textContent = '—';
                }}
              }} else {{
                valueEl.textContent = '—';
              }}
            }}
          }}
        }});
      }});
      
      // Load all stats in parallel for faster response
      const promises = [];
      types.forEach(type => {{
        levels.forEach(level => {{
          promises.push((async () => {{
            const statsEl = document.getElementById(`stats-${{type}}-${{level}}`);
            if (!statsEl) return;
            
            try {{
              const storageKey = `quiz:ru-tr-${{type}}:${{level.toLowerCase()}}`;
              
              // Check if we already have fresh cached data - skip storage request
              const cached = storage._cache && storage._cache[storageKey];
              if (cached && Date.now() - cached.timestamp < storage._cacheTTL) {{
                console.log(`[catalog] Using cached data for ${{level}} (${{type}}), skipping storage request`);
                return; // Already displayed from cache, no need to reload
              }}
              
              console.log(`[catalog] Loading stats for level ${{level}} (${{type}}), key: "${{storageKey}}"`);
              const data = await storage.get(storageKey);
              
              console.log(`[catalog] Got data for ${{level}} (${{type}}):`, data);
              
              if (data) {{
                const stats = JSON.parse(data);
                let avgPercent = null;
                
                if (stats.totalCorrect !== undefined && stats.totalQuestions > 0) {{
                  avgPercent = Math.round((stats.totalCorrect / stats.totalQuestions) * 100);
                }} else if (stats.lastScore !== undefined) {{
                  avgPercent = Math.round((stats.lastScore / 5) * 100);
                }}
                
                console.log(`[catalog] Calculated percent for ${{level}} (${{type}}):`, avgPercent);
                
                // Check for corrupted data (>100%)
                if (avgPercent !== null && avgPercent > 100) {{
                  console.warn(`[catalog] Corrupted stats detected for ${{level}} (${{type}}): ${{avgPercent}}%. Clearing...`);
                  await storage.remove(storageKey);
                  const valueEl = statsEl.querySelector('.stat-value');
                  if (valueEl) valueEl.textContent = '—';
                }} else if (avgPercent !== null) {{
                  const valueEl = statsEl.querySelector('.stat-value');
                  if (valueEl) {{
                    valueEl.textContent = `${{avgPercent}}%`;
                    console.log(`[catalog] Updated display for ${{level}} (${{type}}) to ${{avgPercent}}%`);
                  }}
                }}
              }}
            }} catch (e) {{
              console.error(`Failed to load stats for ${{level}} (${{type}}):`, e);
            }}
          }})());
        }});
      }});
      
      await Promise.all(promises);
    }})();
  </script>
</body>
</html>'''


def generate_css() -> str:
    """Generate CSS file"""
    return '''/* RU→TR Vocabulary Quiz Styles */

:root {
  --bg: #0b1220;
  --card: #121b2f;
  --text: #e9eefc;
  --muted: #9fb0d1;
  --accent: #6aa9ff;
  --ok: #28d17c;
  --bad: #ff4d5a;
  --border: rgba(255,255,255,0.08);
  --shadow: 0 10px 30px rgba(0,0,0,0.35);
  --radius: 18px;
}

* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
  background: radial-gradient(1200px 700px at 20% 0%, rgba(106,169,255,0.18), transparent 60%),
              radial-gradient(900px 600px at 90% 20%, rgba(40,209,124,0.12), transparent 55%),
              var(--bg);
  color: var(--text);
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 18px;
}

.app {
  width: min(860px, 100%);
  background: rgba(18,27,47,0.82);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
  backdrop-filter: blur(10px);
}

header {
  padding: 16px 18px;
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  background: rgba(0,0,0,0.2);
}

.header-left {
  flex: 1;
}

.title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 700;
}

.subtitle {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  color: var(--muted);
}

.score {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--accent);
}

main {
  padding: 20px;
}

.screen {
  display: block;
}

.screen.hidden {
  display: none;
}

.card {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.card h2 {
  margin: 0 0 15px 0;
  font-size: 1.8rem;
}

.card h3 {
  margin: 0 0 10px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--muted);
}

.card p {
  margin: 0 0 15px 0;
  line-height: 1.6;
}

.info {
  padding: 15px;
  background: rgba(106,169,255,0.1);
  border-left: 3px solid var(--accent);
  border-radius: 4px;
}

.btn {
  display: inline-block;
  padding: 12px 24px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  text-align: center;
}

.btn-primary {
  background: var(--accent);
  color: white;
}

.btn-primary:hover {
  background: #5a98ee;
  transform: translateY(-1px);
}

.btn-secondary {
  background: rgba(255,255,255,0.1);
  color: var(--text);
}

.btn-secondary:hover {
  background: rgba(255,255,255,0.15);
}

.btn.hidden {
  display: none;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--ok));
  width: 0;
  transition: width 0.3s ease;
}

.progress-counter {
  font-size: 0.85rem;
  color: var(--muted);
  font-weight: 600;
  white-space: nowrap;
  min-width: 35px;
  text-align: right;
}

.question-prompt {
  text-align: center;
  color: var(--muted);
}

.question-text {
  font-size: 1.3rem;
  font-weight: 600;
  text-align: center;
  margin: 15px 0 20px 0;
}

.answers {
  display: grid;
  gap: 10px;
  margin-bottom: 20px;
  max-width: 95%;
  margin-left: auto;
  margin-right: auto;
}

.answer-btn {
  width: 100%;
  padding: 12px 16px;
  border: 2px solid var(--border);
  border-radius: 12px;
  background: rgba(255,255,255,0.03);
  color: var(--text);
  font-size: 1rem;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 12px;
}

.answer-btn:hover:not(.correct):not(.wrong):not(:disabled) {
  border-color: var(--accent);
  background: rgba(106,169,255,0.1);
}

.answer-btn.correct {
  border-color: var(--ok);
  background: rgba(40,209,124,0.15);
}

.answer-btn.wrong {
  border-color: var(--bad);
  background: rgba(255,77,90,0.15);
}

.answer-btn:disabled {
  cursor: not-allowed;
}

.answer-label {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: rgba(255,255,255,0.1);
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 0.9rem;
  flex-shrink: 0;
}

.answer-btn.correct .answer-label {
  background: var(--ok);
  color: white;
}

.answer-btn.wrong .answer-label {
  background: var(--bad);
  color: white;
}

.answer-text {
  flex: 1;
}

.explanation {
  padding: 15px 20px;
  background: rgba(106,169,255,0.08);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  margin-bottom: 20px;
  max-width: 95%;
  margin-left: auto;
  margin-right: auto;
}

.explanation p {
  margin: 0;
  line-height: 1.5;
}

.results-card {
  text-align: center;
}

.results-score {
  margin: 30px 0;
}

.score-circle {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(106,169,255,0.2), rgba(40,209,124,0.2));
  border: 3px solid var(--accent);
  font-size: 3rem;
  font-weight: 700;
}

.score-total {
  font-size: 1.2rem;
  color: var(--muted);
  margin-top: -10px;
}

.results-message {
  font-size: 1.2rem;
  color: var(--muted);
  margin: 20px 0 30px 0;
}

.results-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin: 30px 0;
  padding: 20px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.stat {
  text-align: center;
}

.stat-label {
  font-size: 0.85rem;
  color: var(--muted);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--accent);
}

.results-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  flex-wrap: wrap;
}

.results-actions .btn {
  min-width: 180px;
}
'''


def generate_js() -> str:
    """Generate main app.js file"""
    return '''// RU→TR Vocabulary Quiz App

// КОНСТАНТА: Количество вопросов в тесте
const QUIZ_LENGTH = 5;

// Telegram WebApp initialization
let tg = null;
if (window.Telegram && window.Telegram.WebApp) {
  tg = window.Telegram.WebApp;
  tg.ready();
  tg.disableVerticalSwipes();
  tg.isClosingConfirmationEnabled = true;
}

// Quiz state
let questions = [];
let currentQuestionIndex = 0;
let score = 0;
let answered = false;

// Storage key for this quiz
const scriptTag = document.querySelector('script[data-questions]');
const questionsPath = scriptTag.getAttribute('data-questions');
const level = scriptTag.getAttribute('data-level') || 'unknown';
// Determine content type from URL path
const contentType = window.location.pathname.includes('RU-TR_Words') ? 'words' : 'phrases';
const storageKey = `quiz:ru-tr-${contentType}:${level.toLowerCase()}`;

// DOM elements
const startScreen = document.getElementById('startScreen');
const quizScreen = document.getElementById('quizScreen');
const resultsScreen = document.getElementById('resultsScreen');

const startBtn = document.getElementById('startBtn');
const nextBtn = document.getElementById('nextBtn');
const playAgainBtn = document.getElementById('playAgainBtn');

const scoreDisplay = document.getElementById('score');
const currentQDisplay = document.getElementById('currentQ');
const totalQDisplay = document.getElementById('totalQ');
const progressFill = document.getElementById('progressFill');

const questionText = document.getElementById('questionText');
const answersContainer = document.getElementById('answers');
const explanation = document.getElementById('explanation');
const explanationText = document.getElementById('explanationText');

const finalScoreDisplay = document.getElementById('finalScore');
const correctCountDisplay = document.getElementById('correctCount');
const wrongCountDisplay = document.getElementById('wrongCount');
const accuracyDisplay = document.getElementById('accuracy');
const resultsMessage = document.getElementById('resultsMessage');

// Load questions
async function loadQuestions() {
  try {
    const response = await fetch(questionsPath);
    const allQuestions = await response.json();
    
    // Shuffle all questions first
    const shuffled = shuffleArray(allQuestions);
    
    // Take EXACTLY QUIZ_LENGTH questions (5)
    questions = shuffled.slice(0, QUIZ_LENGTH);
    
    // Shuffle answer options for each question
    questions = questions.map((q, index) => {
      const variants = [...q.tr];
      const correctAnswer = q.tr[q.correct - 1];
      
      // Shuffle variants
      const shuffledVariants = shuffleArray(variants);
      
      // Find new position of correct answer
      const newCorrectIndex = shuffledVariants.indexOf(correctAnswer) + 1;
      
      return {
        ...q,
        tr: shuffledVariants,
        correct: newCorrectIndex
      };
    });
    
    totalQDisplay.textContent = QUIZ_LENGTH;
    return true;
  } catch (error) {
    console.error('Failed to load questions:', error);
    alert('Не удалось загрузить вопросы. Пожалуйста, попробуйте позже.');
    return false;
  }
}

// Shuffle array (Fisher-Yates algorithm)
function shuffleArray(array) {
  const arr = [...array];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

// Show a screen
function showScreen(screen) {
  [startScreen, quizScreen, resultsScreen].forEach(s => s.classList.add('hidden'));
  screen.classList.remove('hidden');
}

// Start quiz
async function startQuiz() {
  const loaded = await loadQuestions();
  if (!loaded) return;
  
  currentQuestionIndex = 0;
  score = 0;
  scoreDisplay.textContent = score;
  
  showScreen(quizScreen);
  showQuestion();
}

// Show current question
function showQuestion() {
  answered = false;
  nextBtn.classList.add('hidden');
  explanation.classList.add('hidden');
  explanationText.textContent = '';
  
  const question = questions[currentQuestionIndex];
  
  questionText.textContent = question.ru;
  currentQDisplay.textContent = currentQuestionIndex + 1;
  
  // Update progress bar
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100;
  progressFill.style.width = `${progress}%`;
  
  // Render answers
  answersContainer.innerHTML = '';
  const labels = ['A', 'B', 'C', 'D'];
  
  question.tr.forEach((answer, index) => {
    const button = document.createElement('button');
    button.className = 'answer-btn';
    button.innerHTML = `
      <span class="answer-label">${labels[index]}</span>
      <span class="answer-text">${answer}</span>
    `;
    button.onclick = () => selectAnswer(index + 1, button);
    answersContainer.appendChild(button);
  });
}

// Handle answer selection
function selectAnswer(selected, button) {
  if (answered) return;
  
  answered = true;
  const question = questions[currentQuestionIndex];
  const correct = question.correct;
  const isCorrect = selected === correct;
  
  // Disable all buttons
  const buttons = answersContainer.querySelectorAll('.answer-btn');
  buttons.forEach((btn, idx) => {
    btn.disabled = true;
    if (idx + 1 === correct) {
      btn.classList.add('correct');
    }
  });
  
  // Mark selected button
  if (!isCorrect) {
    button.classList.add('wrong');
  }
  
  // Update score
  if (isCorrect) {
    score++;
    scoreDisplay.textContent = score;
  }
  
  // Show explanation
  explanationText.textContent = question.explain_ru;
  explanation.classList.remove('hidden');
  
  // Show next button or finish
  if (currentQuestionIndex < questions.length - 1) {
    nextBtn.textContent = 'Следующий вопрос';
    nextBtn.classList.remove('hidden');
  } else {
    nextBtn.textContent = 'Показать результаты';
    nextBtn.classList.remove('hidden');
  }
}

// Next question
function nextQuestion() {
  currentQuestionIndex++;
  
  if (currentQuestionIndex < questions.length) {
    showQuestion();
  } else {
    showResults();
  }
}

// Show results
function showResults() {
  const correctCount = score;
  const wrongCount = questions.length - score;
  const accuracy = Math.round((score / questions.length) * 100);
  
  finalScoreDisplay.textContent = score;
  correctCountDisplay.textContent = correctCount;
  wrongCountDisplay.textContent = wrongCount;
  accuracyDisplay.textContent = `${accuracy}%`;
  
  // Determine message
  let message = '';
  if (accuracy >= 90) {
    message = 'Превосходно! 🌟';
  } else if (accuracy >= 70) {
    message = 'Отличная работа! 👏';
  } else if (accuracy >= 50) {
    message = 'Хорошо, но есть куда расти! 💪';
  } else {
    message = 'Продолжайте практиковаться! 📚';
  }
  resultsMessage.textContent = message;
  
  // Show screen immediately (non-blocking)
  showScreen(resultsScreen);
  
  // Save stats in background
  setTimeout(() => {
    (async () => {
      try {
        console.log(`[showResults] Saving stats with storageKey: "${storageKey}"`);
        const stats = {
          bestScore: score,
          lastScore: score,
          totalCorrect: score,
          totalQuestions: 5,
          attempts: 1,
          lastAttemptAt: new Date().toISOString()
        };
        
        // Load previous stats
        try {
          const prevStats = await storage.get(storageKey);
          if (prevStats) {
            const prev = JSON.parse(prevStats);
            
            // Check if previous stats are corrupted (>100%)
            let prevPercent = null;
            if (prev.totalCorrect !== undefined && prev.totalQuestions > 0) {
              prevPercent = (prev.totalCorrect / prev.totalQuestions) * 100;
            } else if (prev.lastScore !== undefined) {
              prevPercent = (prev.lastScore / 5) * 100;
            }
            
            // If corrupted, reset stats and start fresh
            if (prevPercent !== null && prevPercent > 100) {
              console.warn(`[showResults] Corrupted stats detected (${Math.round(prevPercent)}%). Resetting...`);
              // Keep only current attempt, discard broken history
            } else {
              // Stats look good, merge with previous
              stats.bestScore = Math.max(score, prev.bestScore || 0);
              
              // Migrate old stats format to new
              if (prev.totalCorrect !== undefined && prev.totalQuestions !== undefined) {
                // New format - just add
                stats.totalCorrect = prev.totalCorrect + score;
                stats.totalQuestions = prev.totalQuestions + 5;
              } else if (prev.lastScore !== undefined) {
                // Old format - initialize with last score as one attempt
                stats.totalCorrect = prev.lastScore + score;
                stats.totalQuestions = 5 + 5; // Previous attempt + current attempt
              }
              
              stats.attempts = (prev.attempts || 0) + 1;
            }
          }
        } catch (e) {
          console.error('Failed to load previous stats:', e);
        }
        
        // Save new stats
        const statsJson = JSON.stringify(stats);
        await storage.set(storageKey, statsJson);
        
        // Update cache immediately so it's available on catalog page
        if (storage._cache) {
          storage._cache[storageKey] = { value: statsJson, timestamp: Date.now() };
        }
        
        // Update global unique days counter
        try {
          console.log('[showResults] Starting unique days update...');
          const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
          console.log('[showResults] Today:', today);
          const globalKey = 'quiz:global:days-counter';
          const globalData = await storage.get(globalKey);
          console.log('[showResults] Got global data:', globalData);
          
          let globalStats = {
            uniqueDays: 1,
            lastPassed: today
          };
          
          if (globalData) {
            const prev = JSON.parse(globalData);
            console.log('[showResults] Parsed previous data:', prev);
            
            // If last passed is not today, increment counter
            if (prev.lastPassed !== today) {
              globalStats.uniqueDays = (prev.uniqueDays || 0) + 1;
              globalStats.lastPassed = today;
              console.log(`[showResults] New day! Unique days: ${globalStats.uniqueDays}`);
            } else {
              // Same day, keep existing count
              globalStats.uniqueDays = prev.uniqueDays || 1;
              globalStats.lastPassed = prev.lastPassed;
              console.log(`[showResults] Already passed today. Unique days: ${globalStats.uniqueDays}`);
            }
          } else {
            console.log(`[showResults] First day! Unique days: 1`);
          }
          
          console.log('[showResults] Saving global stats:', globalStats);
          await storage.set(globalKey, JSON.stringify(globalStats));
          console.log('[showResults] Global stats saved successfully!');
          
          // Update cache
          if (storage._cache) {
            storage._cache[globalKey] = { value: JSON.stringify(globalStats), timestamp: Date.now() };
          }
        } catch (e) {
          console.error('Failed to update unique days counter:', e);
        }
        
        // Calculate new percentage
        const newPercent = Math.round((stats.totalCorrect / stats.totalQuestions) * 100);
        console.log(`Stats saved! New average: ${newPercent}%`);
      } catch (e) {
        console.error('Failed to save stats:', e);
      }
    })();
  }, 100);
}

// Event listeners
startBtn.addEventListener('click', startQuiz);
nextBtn.addEventListener('click', nextQuestion);
playAgainBtn.addEventListener('click', startQuiz);
'''


def generate_storage_js() -> str:
    """Generate storage.js for CloudStorage/localStorage"""
    return '''// Storage wrapper with Telegram CloudStorage + localStorage fallback

const storage = {
  // In-memory cache to avoid repeated CloudStorage calls
  _cache: {},
  _cacheTTL: 30000, // 30 seconds
  
  // Check if CloudStorage is available
  canUseCloudStorage() {
    return window.Telegram && 
           window.Telegram.WebApp && 
           window.Telegram.WebApp.CloudStorage &&
           typeof window.Telegram.WebApp.CloudStorage.getItem === 'function';
  },
  
  // Get value by key
  async get(key) {
    return new Promise((resolve) => {
      // Check cache first
      const cached = this._cache[key];
      if (cached && Date.now() - cached.timestamp < this._cacheTTL) {
        console.log(`[Storage] GET ${key} from cache:`, cached.value);
        resolve(cached.value);
        return;
      }
      
      // Always try localStorage first for immediate response
      const localValue = localStorage.getItem(key);
      
      if (!this.canUseCloudStorage()) {
        console.log(`[Storage] GET ${key} from localStorage:`, localValue);
        if (localValue) {
          this._cache[key] = { value: localValue, timestamp: Date.now() };
        }
        resolve(localValue);
        return;
      }
      
      // Try CloudStorage with 800ms timeout for faster response
      let resolved = false;
      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          console.log(`[Storage] GET ${key} timeout, using localStorage:`, localValue);
          if (localValue) {
            this._cache[key] = { value: localValue, timestamp: Date.now() };
          }
          resolve(localValue);
        }
      }, 800);
      
      try {
        window.Telegram.WebApp.CloudStorage.getItem(key, (error, value) => {
          clearTimeout(timeout);
          if (resolved) return;
          resolved = true;
          
          if (error) {
            console.warn(`[Storage] CloudStorage GET ${key} error:`, error);
            if (localValue) {
              this._cache[key] = { value: localValue, timestamp: Date.now() };
            }
            resolve(localValue);
          } else {
            console.log(`[Storage] GET ${key} from CloudStorage:`, value);
            const finalValue = value || localValue;
            // Cache the result
            if (finalValue) {
              this._cache[key] = { value: finalValue, timestamp: Date.now() };
            }
            // Sync to localStorage
            if (value && value !== localValue) {
              localStorage.setItem(key, value);
            }
            resolve(finalValue);
          }
        });
      } catch (e) {
        clearTimeout(timeout);
        if (!resolved) {
          resolved = true;
          console.error(`[Storage] CloudStorage GET ${key} exception:`, e);
          resolve(localValue);
        }
      }
    });
  },
  
  // Set value by key
  async set(key, value) {
    return new Promise((resolve) => {
      // Update cache immediately
      this._cache[key] = { value, timestamp: Date.now() };
      
      // Always save to localStorage immediately
      localStorage.setItem(key, value);
      console.log(`[Storage] SET ${key} to localStorage:`, value);
      
      if (!this.canUseCloudStorage()) {
        resolve();
        return;
      }
      
      // Try CloudStorage in background
      try {
        window.Telegram.WebApp.CloudStorage.setItem(key, value, (error) => {
          if (error) {
            console.warn(`[Storage] CloudStorage SET ${key} error:`, error);
          } else {
            console.log(`[Storage] SET ${key} to CloudStorage: OK`);
          }
          resolve();
        });
      } catch (e) {
        console.error(`[Storage] CloudStorage SET ${key} exception:`, e);
        resolve();
      }
    });
  },
  
  // Remove value by key
  async remove(key) {
    return new Promise((resolve) => {
      localStorage.removeItem(key);
      console.log(`[Storage] REMOVE ${key} from localStorage`);
      
      if (!this.canUseCloudStorage()) {
        resolve();
        return;
      }
      
      try {
        window.Telegram.WebApp.CloudStorage.removeItem(key, (error) => {
          if (error) {
            console.warn(`[Storage] CloudStorage REMOVE ${key} error:`, error);
          } else {
            console.log(`[Storage] REMOVE ${key} from CloudStorage: OK`);
          }
          resolve();
        });
      } catch (e) {
        console.error(`[Storage] CloudStorage REMOVE ${key} exception:`, e);
        resolve();
      }
    });
  }
};

// Export for use in other scripts
window.storage = storage;
'''


def build_site():
    """Main build function"""
    # Find repository root
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    
    print("🔍 Running validation...")
    
    # Run validation first with separate ID tracking for Words and Phrases
    words_ids = set()
    phrases_ids = set()
    jsonl_files = validate_questions.find_jsonl_files(repo_root)
    
    if not jsonl_files:
        print("⚠️  No JSONL files found. Nothing to build.")
        return 1
    
    has_errors = False
    for filepath in jsonl_files:
        # Determine which ID set to use based on file path
        is_words = "RU-TR_Words" in str(filepath)
        all_ids = words_ids if is_words else phrases_ids
        
        _, errors_list = validate_questions.validate_jsonl_file(filepath, all_ids)
        if errors_list:
            has_errors = True
            print(f"❌ Validation failed for {filepath.relative_to(repo_root)}")
    
    if has_errors:
        print("\n❌ Validation failed. Fix errors before building.")
        return 1
    
    print("✅ Validation passed\n")
    
    # Prepare output directory
    output_dir = repo_root / "html" / "ma"
    print(f"📁 Cleaning output directory: {output_dir}")
    
    # Clean output directory (but keep .gitkeep if exists)
    if output_dir.exists():
        for item in output_dir.iterdir():
            if item.name == '.gitkeep':
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create assets directory
    assets_dir = output_dir / "assets"
    assets_dir.mkdir(exist_ok=True)
    
    print("📝 Generating assets...")
    
    # Generate CSS and JS
    (assets_dir / "app.css").write_text(generate_css(), encoding="utf-8")
    (assets_dir / "app.js").write_text(generate_js(), encoding="utf-8")
    (assets_dir / "storage.js").write_text(generate_storage_js(), encoding="utf-8")
    
    # Find and organize JSONL files for both types
    words_structure = find_jsonl_files(repo_root, "Words")
    phrases_structure = find_jsonl_files(repo_root, "Phrases")
    
    print("🏗️  Building quiz pages...")
    
    # Generate quiz pages for Words
    for level, files in words_structure.items():
        # Create directory for this level
        quiz_dir = output_dir / "RU-TR_Words" / level
        quiz_dir.mkdir(parents=True, exist_ok=True)
        
        # Load and combine all questions from all files in this level
        all_questions = []
        for jsonl_file in files:
            questions = load_questions_from_jsonl(jsonl_file)
            all_questions.extend(questions)
        
        # Save combined questions.json
        questions_json_path = quiz_dir / "questions.json"
        with open(questions_json_path, "w", encoding="utf-8") as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=2)
        
        # Generate quiz HTML
        quiz_html = generate_quiz_page(level, len(all_questions), "Words")
        (quiz_dir / "index.html").write_text(quiz_html, encoding="utf-8")
        
        print(f"  ✓ Words/{level} ({len(all_questions)} questions from {len(files)} file(s))")
    
    # Generate quiz pages for Phrases
    for level, files in phrases_structure.items():
        # Create directory for this level
        quiz_dir = output_dir / "RU-TR_Phrases" / level
        quiz_dir.mkdir(parents=True, exist_ok=True)
        
        # Load and combine all questions from all files in this level
        all_questions = []
        for jsonl_file in files:
            questions = load_questions_from_jsonl(jsonl_file)
            all_questions.extend(questions)
        
        # Save combined questions.json
        questions_json_path = quiz_dir / "questions.json"
        with open(questions_json_path, "w", encoding="utf-8") as f:
            json.dump(all_questions, f, ensure_ascii=False, indent=2)
        
        # Generate quiz HTML
        quiz_html = generate_quiz_page(level, len(all_questions), "Phrases")
        (quiz_dir / "index.html").write_text(quiz_html, encoding="utf-8")
        
        print(f"  ✓ Phrases/{level} ({len(all_questions)} questions from {len(files)} file(s))")
    
    # Generate catalog/index page
    print("📋 Generating catalog page...")
    catalog_html = generate_catalog_page(words_structure, phrases_structure)
    (output_dir / "index.html").write_text(catalog_html, encoding="utf-8")
    
    print(f"\n✅ Build complete! Output: {output_dir}")
    print(f"   Words levels: {len(words_structure)}")
    print(f"   Phrases levels: {len(phrases_structure)}")
    total_words_files = sum(len(files) for files in words_structure.values())
    total_phrases_files = sum(len(files) for files in phrases_structure.values())
    print(f"   Total source files: {total_words_files + total_phrases_files}")
    
    return 0


def main():
    """Main entry point"""
    try:
        return build_site()
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
