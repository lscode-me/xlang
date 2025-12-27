// КОНСТАНТА: Количество вопросов в тесте
const QUIZ_LENGTH = {{ quiz_length }};

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
const contentId = scriptTag.getAttribute('data-content-id') || 'unknown';
const storageKey = storageKeys.quiz(contentId, level);

console.log(`[app.js] Quiz initialized: contentId="${contentId}", level="${level}", storageKey="${storageKey}"`);

// DOM elements
const startScreen = document.getElementById('startScreen');
const quizScreen = document.getElementById('quizScreen');
const resultsScreen = document.getElementById('resultsScreen');

const startBtn = document.getElementById('startBtn');
const cancelBtn = document.getElementById('cancelBtn');
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
    
    // Take EXACTLY QUIZ_LENGTH questions
    questions = shuffled.slice(0, QUIZ_LENGTH);
    
    // Shuffle answer options for each question
    questions = questions.map((q, index) => {
      const variants = [...q.options];
      const correctAnswer = q.options[q.correct - 1];
      
      // Shuffle variants
      const shuffledVariants = shuffleArray(variants);
      
      // Find new position of correct answer
      const newCorrectIndex = shuffledVariants.indexOf(correctAnswer) + 1;
      
      return {
        ...q,
        options: shuffledVariants,
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
  
  questionText.textContent = question.question;
  currentQDisplay.textContent = currentQuestionIndex + 1;
  
  // Update progress bar
  const progress = ((currentQuestionIndex + 1) / questions.length) * 100;
  progressFill.style.width = `${progress}%`;
  
  // Render answers
  answersContainer.innerHTML = '';
  const labels = ['A', 'B', 'C', 'D'];
  
  question.options.forEach((answer, index) => {
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
  explanationText.textContent = question.explanation;
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
  
  // Show results screen immediately
  showScreen(resultsScreen);
  
  // Show saving indicator, hide action buttons
  const savingIndicator = document.getElementById('savingIndicator');
  const resultsActions = document.getElementById('resultsActions');
  savingIndicator.classList.remove('hidden');
  resultsActions.classList.add('hidden');
  
  // Save stats in background and show buttons when done
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
    console.log(`[showResults] Saving stats to "${storageKey}":`, stats);
    const saveResult = await storage.set(storageKey, statsJson);
    console.log(`[showResults] Save result:`, saveResult);
    
    // Update cache immediately so it's available on catalog page
    if (storage._cache) {
      storage._cache[storageKey] = { value: statsJson, timestamp: Date.now() };
      console.log(`[showResults] Updated cache for "${storageKey}"`);
    }
    
    // Update global unique days counter
    try {
      console.log('[showResults] Starting unique days update...');
      const today = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
      console.log('[showResults] Today:', today);
      const globalKey = storageKeys.globalDaysCounter();
      const globalData = await storage.get(globalKey, { forceRefresh: true });
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
    
    // Show action buttons, hide saving indicator
    savingIndicator.classList.add('hidden');
    resultsActions.classList.remove('hidden');
  } catch (e) {
    console.error('Failed to save stats:', e);
    
    // Show buttons even on error (don't block user)
    savingIndicator.classList.add('hidden');
    resultsActions.classList.remove('hidden');
  }
  })();
}

// Event listeners
startBtn.addEventListener('click', startQuiz);
cancelBtn.addEventListener('click', () => {
  window.location.href = '../../index.html';
});
nextBtn.addEventListener('click', nextQuestion);
playAgainBtn.addEventListener('click', startQuiz);
