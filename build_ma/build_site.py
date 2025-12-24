#!/usr/bin/env python3
"""
Build static Telegram Mini App for RU→TR Vocabulary Quiz.
Generates HTML files and assets in html/ma/
"""
import json
import shutil
import sys
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


def find_jsonl_files(base_dir: Path) -> Dict[str, List[Path]]:
    """
    Find all JSONL files organized by level.
    Returns: {level: [Path, ...], ...}
    """
    structure = defaultdict(list)
    
    for level in ["A1", "A2", "B1"]:
        level_dir = base_dir / "Vocabulary" / "RU-TR" / level
        if not level_dir.exists():
            continue
        
        for jsonl_file in level_dir.glob("**/*.jsonl"):
            structure[level].append(jsonl_file)
    
    return structure


def generate_quiz_page(level: str, questions_count: int) -> str:
    """Generate HTML for a quiz page"""
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Quiz: {level}</title>
  <link rel="stylesheet" href="../../assets/app.css">
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <div class="app">
    <header>
      <div class="header-left">
        <h1 class="title">RU→TR Quiz</h1>
        <div class="subtitle">{level}</div>
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
        <div class="progress-bar">
          <div id="progressFill" class="progress-fill"></div>
        </div>
        <div class="question-counter">
          Вопрос <span id="currentQ">1</span> из <span id="totalQ">5</span>
        </div>
        
        <div class="card">
          <h3 class="question-prompt">Выбери правильный перевод:</h3>
          <p id="questionText" class="question-text"></p>
          
          <div id="answers" class="answers">
            <!-- Answers will be inserted here -->
          </div>
          
          <div id="explanation" class="explanation hidden">
            <h4>Объяснение:</h4>
            <p id="explanationText"></p>
          </div>
          
          <button id="nextBtn" class="btn btn-primary hidden">Следующий вопрос</button>
        </div>
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

  <script src="../../assets/storage.js"></script>
  <script src="../../assets/app.js" data-questions="./questions.json" data-level="{level}"></script>
</body>
</html>'''


def generate_catalog_page(structure: Dict[str, List[Path]]) -> str:
    """Generate HTML for catalog/index page"""
    levels_html = []
    
    for level in ["A1", "A2", "B1"]:
        if level not in structure:
            continue
        
        levels_html.append(f'''
        <a href="RU-TR/{level}/index.html" class="level-card">
          <div class="level-badge">{level}</div>
          <div class="level-description">
            {'Начальный уровень' if level == 'A1' else 'Элементарный уровень' if level == 'A2' else 'Средний уровень'}
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
      gap: 20px;
    }}
    
    .level-card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 30px;
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
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 10px;
      color: var(--accent);
    }}
    
    .level-meta {{
      font-size: 0.9rem;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    
    .level-description {{
      font-size: 1.1rem;
      font-weight: 500;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>🇷🇺 → 🇹🇷 Vocabulary Quiz</h1>
    <p class="subtitle">Выберите свой уровень</p>
    
    <div class="levels-grid">
      {''.join(levels_html)}
    </div>
  </div>
  
  <script>
    // Telegram WebApp integration
    if (window.Telegram && window.Telegram.WebApp) {{
      const tg = window.Telegram.WebApp;
      tg.ready();
      tg.expand();
    }}
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
  padding: 30px;
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

.progress-bar {
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 15px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent), var(--ok));
  width: 0;
  transition: width 0.3s ease;
}

.question-counter {
  text-align: center;
  font-size: 0.9rem;
  color: var(--muted);
  margin-bottom: 20px;
}

.question-prompt {
  text-align: center;
  color: var(--muted);
}

.question-text {
  font-size: 1.5rem;
  font-weight: 600;
  text-align: center;
  margin: 20px 0 30px 0;
}

.answers {
  display: grid;
  gap: 12px;
  margin-bottom: 20px;
}

.answer-btn {
  width: 100%;
  padding: 16px 20px;
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
  padding: 20px;
  background: rgba(106,169,255,0.08);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  margin-bottom: 20px;
}

.explanation h4 {
  margin: 0 0 8px 0;
  font-size: 0.95rem;
  color: var(--accent);
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

// Telegram WebApp initialization
let tg = null;
if (window.Telegram && window.Telegram.WebApp) {
  tg = window.Telegram.WebApp;
  tg.ready();
  tg.expand();
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
const storageKey = `quiz:ru-tr:${level.toLowerCase()}`;

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
    
    // Shuffle and take 5 questions
    questions = shuffleArray(allQuestions).slice(0, 5);
    
    console.log(`Loaded ${questions.length} questions from ${allQuestions.length} total`);
    
    // Optionally shuffle answer options for each question
    questions = questions.map(q => {
      const variants = [...q.tr];
      const correctAnswer = q.tr[q.correct - 1];
      
      // Shuffle variants
      const shuffled = shuffleArray(variants);
      
      // Find new position of correct answer
      const newCorrectIndex = shuffled.indexOf(correctAnswer) + 1;
      
      return {
        ...q,
        tr: shuffled,
        correct: newCorrectIndex
      };
    });
    
    totalQDisplay.textContent = questions.length;
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
  console.log(`Moving to question ${currentQuestionIndex + 1} of ${questions.length}`);
  
  if (currentQuestionIndex < questions.length) {
    showQuestion();
  } else {
    console.log('Quiz finished! Showing results...');
    showResults();
  }
}

// Show results
async function showResults() {
  console.log('Showing results screen...');
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
  
  // Save progress to storage
  const stats = {
    bestScore: score,
    lastScore: score,
    attempts: 1,
    lastAttemptAt: new Date().toISOString()
  };
  
  // Load previous stats
  try {
    const prevStats = await storage.get(storageKey);
    if (prevStats) {
      const prev = JSON.parse(prevStats);
      stats.bestScore = Math.max(score, prev.bestScore || 0);
      stats.attempts = (prev.attempts || 0) + 1;
    }
  } catch (e) {
    console.error('Failed to load previous stats:', e);
  }
  
  // Save new stats
  try {
    await storage.set(storageKey, JSON.stringify(stats));
  } catch (e) {
    console.error('Failed to save stats:', e);
  }
  
  showScreen(resultsScreen);
}

// Event listeners
startBtn.addEventListener('click', startQuiz);
nextBtn.addEventListener('click', nextQuestion);
playAgainBtn.addEventListener('click', startQuiz);

// Initialize
console.log('Quiz app loaded');
'''


def generate_storage_js() -> str:
    """Generate storage.js for CloudStorage/localStorage"""
    return '''// Storage wrapper with Telegram CloudStorage fallback to localStorage

const storage = {
  // Check if CloudStorage is available
  isCloudStorageAvailable() {
    return window.Telegram && 
           window.Telegram.WebApp && 
           window.Telegram.WebApp.CloudStorage;
  },
  
  // Get value by key
  async get(key) {
    if (this.isCloudStorageAvailable()) {
      return new Promise((resolve, reject) => {
        window.Telegram.WebApp.CloudStorage.getItem(key, (error, value) => {
          if (error) {
            console.warn('CloudStorage get error, falling back to localStorage:', error);
            resolve(localStorage.getItem(key));
          } else {
            resolve(value);
          }
        });
      });
    } else {
      return Promise.resolve(localStorage.getItem(key));
    }
  },
  
  // Set value by key
  async set(key, value) {
    if (this.isCloudStorageAvailable()) {
      return new Promise((resolve, reject) => {
        window.Telegram.WebApp.CloudStorage.setItem(key, value, (error, success) => {
          if (error) {
            console.warn('CloudStorage set error, falling back to localStorage:', error);
            localStorage.setItem(key, value);
            resolve();
          } else {
            resolve();
          }
        });
      });
    } else {
      localStorage.setItem(key, value);
      return Promise.resolve();
    }
  },
  
  // Remove value by key
  async remove(key) {
    if (this.isCloudStorageAvailable()) {
      return new Promise((resolve, reject) => {
        window.Telegram.WebApp.CloudStorage.removeItem(key, (error, success) => {
          if (error) {
            console.warn('CloudStorage remove error, falling back to localStorage:', error);
            localStorage.removeItem(key);
            resolve();
          } else {
            resolve();
          }
        });
      });
    } else {
      localStorage.removeItem(key);
      return Promise.resolve();
    }
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
    
    # Run validation first
    all_ids = set()
    jsonl_files = validate_questions.find_jsonl_files(repo_root)
    
    if not jsonl_files:
        print("⚠️  No JSONL files found. Nothing to build.")
        return 1
    
    has_errors = False
    for filepath in jsonl_files:
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
    
    # Find and organize JSONL files
    structure = find_jsonl_files(repo_root)
    
    print("🏗️  Building quiz pages...")
    
    # Generate quiz pages for each level
    for level, files in structure.items():
        # Create directory for this level
        quiz_dir = output_dir / "RU-TR" / level
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
        quiz_html = generate_quiz_page(level, len(all_questions))
        (quiz_dir / "index.html").write_text(quiz_html, encoding="utf-8")
        
        print(f"  ✓ {level} ({len(all_questions)} questions from {len(files)} file(s))")
    
    # Generate catalog/index page
    print("📋 Generating catalog page...")
    catalog_html = generate_catalog_page(structure)
    (output_dir / "index.html").write_text(catalog_html, encoding="utf-8")
    
    print(f"\n✅ Build complete! Output: {output_dir}")
    print(f"   Total levels: {len(structure)}")
    total_files = sum(len(files) for files in structure.values())
    print(f"   Total source files: {total_files}")
    
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
