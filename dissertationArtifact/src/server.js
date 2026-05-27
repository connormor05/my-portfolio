require('dotenv').config();
console.log("SERVER FILE LOADED");
console.log("SERVER STARTING…");

const express = require('express');
const bcrypt = require("bcrypt");
const jwt = require("jsonwebtoken");
const db = require("./database.js");

// Centralized Secret
const JWT_SECRET = process.env.JWT_SECRET || "secret";

const { runSafetyCheck } = require('./safety/llamaGuard');
const { loadCourses } = require("./data_utils");
const fs = require("fs");
const path = require("path");

const app = express();

// --- MIDDLEWARE (Must be before routes) ---
app.use(express.json()); 
app.use(express.urlencoded({ extended: true }));

// 🔍 DEBUG LOGGER: Tells you exactly what Python is sending
app.use((req, res, next) => {
  if (req.method === 'POST') {
    console.log(`\n[POST] ${req.url} - Body:`, req.body);
  }
  next();
});

const PORT = process.env.PORT || 3000;

// ⭐ AUTH MIDDLEWARE: Ensures req.userId is set for protected routes
function auth(req, res, next) {
  const authHeader = req.headers.authorization;
  if (!authHeader) return res.status(401).json({ error: "No token provided" });

  const token = authHeader.split(" ")[1];
  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.userId;
    next();
  } catch (err) {
    return res.status(401).json({ error: "Invalid token" });
  }
}

// ====================================================
// AUTHENTICATION ROUTES
// ====================================================

app.post("/signup", async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) {
    console.log("❌ Signup failed: Missing fields");
    return res.status(400).json({ error: "Email and password required" });
  }

  try {
    const existingUser = db.prepare("SELECT * FROM users WHERE email = ?").get(email);
    if (existingUser) return res.status(400).json({ error: "Email already in use" });

    const hashedPassword = await bcrypt.hash(password, 10);
    const info = db.prepare("INSERT INTO users (email, password_hash) VALUES (?, ?)").run(email, hashedPassword);    
    db.prepare(`
      INSERT INTO progress (user_id, xp, level, streak, achievements, completed_lessons) 
      VALUES (?, 0, 1, 0, '{}', '[]')
    `).run(info.lastInsertRowid);

    const token = jwt.sign({ userId: info.lastInsertRowid }, JWT_SECRET, { expiresIn: "24h" });
    console.log(`✅ New user registered: ${email}`);
    res.json({ token, email });
  } catch (err) {
    console.error("Signup error:", err);
    res.status(500).json({ error: "Server error during signup" });
  }
});

app.post("/login", async (req, res) => {
  const { email, password } = req.body;
  const user = db.prepare("SELECT * FROM users WHERE email = ?").get(email);
  
  if (!user) return res.status(400).json({ error: "Invalid credentials" });
  
  const validPassword = await bcrypt.compare(password, user.password_hash);  if (!validPassword) return res.status(400).json({ error: "Invalid credentials" });

  const token = jwt.sign({ userId: user.id }, JWT_SECRET, { expiresIn: "24h" });
  console.log(`✅ User logged in: ${email}`);
  
  res.json({ token, email });
});


// --- State and Lesson Logic Follows ---
let lessonStates = {};

// -------------------------
// ACHIEVEMENT NAMES
// -------------------------
const ACHIEVEMENT_NAMES = {
  "first_message": "Icebreaker 💬",
  "two_day_streak": "On a Roll (2 Days) 🔥",
  "three_day_streak": "Habit Builder (3 Days) 🔥",
  "five_day_streak": "Unstoppable (5 Days) 🚀",
  "seven_day_streak": "Weekly Warrior (7 Days) 🏆",
  "first_lesson_completed": "First Steps 🎓",
  "three_lessons_completed": "Getting the Hang of It 📚",
  "five_lessons_completed": "Halfway There! 🌟",
  "ten_lessons_completed": "Course Champion 🏆",
  "level_2": "Level 2 Reached! ⭐",
  "level_3": "Level 3 Reached! 🌟",
  "level_4": "Level 4 Reached! ✨",
  "level_5": "Level 5 Master! 👑"
};


// -------------------------
// USER PROGRESSION STATE
// -------------------------
let lastLessonId = null;

function resetLessonState(userId) {
  // Reset in-memory lesson state
  lessonStates[userId] = {
    phase: "intro",
    step: 0,
    totalSteps: 0,
    currentStepCorrect: true,
    lastInfoBlock: null,
    lastTask: null,
    lastAnswer: null,
    questionCount: 0,
    maxQuestions: 4,
    tasksCompleted: 0,
    taskStage: 0
  };

  // Ensure DB progression exists (prevents errors later)
  const prog = db.prepare(`SELECT * FROM progress WHERE user_id = ?`).get(userId);
  if (!prog) {
    db.prepare(`
      INSERT INTO progress (user_id, xp, level, streak, last_active_date, achievements, completed_lessons)
      VALUES (?, 0, 1, 0, ?, ?, ?)
    `).run(
      userId,
      new Date().toDateString(),
      JSON.stringify({}),
      JSON.stringify([])
    );
  }
}

function requiredTasks(difficulty) {
  if (difficulty === "easy") return 4;
  if (difficulty === "medium") return 7;
  if (difficulty === "hard") return 12;
  return 4; // default fallback
}

// -------------------------
// JSON EXTRACTOR
// -------------------------
function extractJSON(text) {
  if (!text) return null;

  // Remove markdown fences like ```json ... ```
  text = text
    .replace(/```json/gi, "")
    .replace(/```/g, "")
    .trim();

  // Grab the first {...} block
  const match = text.match(/\{[\s\S]*\}/);
  return match ? match[0] : null;
}

// -------------------------
// JSON SANITIZER
// -------------------------
function safeJSONParse(text) {
  if (!text || typeof text !== "string") {
    console.error("❌ safeJSONParse received invalid input:", text);
    return null;
  }

  // ⭐ Clean the text first
  const cleaned = extractJSON(text);
  if (!cleaned) {
    console.error("❌ safeJSONParse could not extract JSON from:", text);
    return null;
  }

  try {
    return JSON.parse(cleaned);
  } catch (err) {
    console.error("❌ safeJSONParse failed:", err.message);
    return null;
  }
}

function updateStreak(progression) {
  const today = new Date().toDateString();

  if (!progression.lastActiveDate || progression.lastActiveDate !== today) {
    progression.streak = (progression.streak || 0) + 1;
    progression.lastActiveDate = today;
  }
}

function unlockAchievement(progression, name) {
  // Ensure achievements is an object (dictionary)
  if (
    !progression.achievements ||
    typeof progression.achievements !== "object" ||
    Array.isArray(progression.achievements)
  ) {
    progression.achievements = {};
  }

  // Only add if not already present
  if (!progression.achievements[name]) {
    progression.achievements[name] = true;
    return true; // NEW achievement unlocked
  }

  return false; // Already had it
}

function markLessonComplete(userId, lessonId, progression) {
  if (!progression.completedLessons.includes(lessonId)) {
    progression.completedLessons.push(lessonId);
  }
}

function buildProgressionPayload(progression) {
  const xpNeeded = progression.level * 50;

  return {
    xp: progression.xp,
    level: progression.level,
    streak: progression.streak,
    achievements: progression.achievements,
    xpNeeded: xpNeeded,
    xpToNext: xpNeeded - progression.xp
  };
}


// Root route
app.get('/', (req, res) => {
  res.json({ message: 'Uni AI Assistant backend is running' });
});

// Ask route with safety layer (used by ChatWindow)
app.post('/ask', async (req, res) => {
  const { question } = req.body;

  if (!question) {
    return res.status(400).json({ error: 'No question provided' });
  }

  const safety = await runSafetyCheck(question);

  if (!safety.allowed) {
    return res.status(403).json({
      error: 'Question blocked by safety system',
      reason: safety.reason
    });
  }

  res.json({
    answer: `You asked: "${question}". The Assistant will respond here soon.`
  });
});

app.get("/courses", auth, (req, res) => {
  const userId = req.userId;

  // Load static lessons
  const courses = loadCourses();
  const course = courses["Programming Fundamentals"];

  // Load user progression from DB (or create if missing)
  let row = db.prepare(`
    SELECT xp, level, streak, achievements, completed_lessons
    FROM progress
    WHERE user_id = ?
  `).get(userId);

  if (!row) {
    db.prepare(`
      INSERT INTO progress (user_id, xp, level, streak, achievements, completed_lessons)
      VALUES (?, 0, 1, 0, '{}', '[]')
    `).run(userId);

    row = db.prepare(`
      SELECT xp, level, streak, achievements, completed_lessons
      FROM progress
      WHERE user_id = ?
    `).get(userId);
  }

  let achievementsParsed = JSON.parse(row.achievements || "{}");
  if (Array.isArray(achievementsParsed)) {
    const converted = {};
    for (const key of achievementsParsed) {
      converted[key] = true;
    }
    achievementsParsed = converted;
  }

  const progression = {
    xp: row.xp,
    level: row.level,
    streak: row.streak,
    achievements: achievementsParsed,
    completedLessons: JSON.parse(row.completed_lessons || "[]")
  };

  // Merge static lessons with per-user progress
  const lessonsWithState = course.lessons.map(lesson => {
    const completed = progression.completedLessons.includes(lesson.id);
    const unlocked = lesson.id === 1 || progression.completedLessons.includes(lesson.id - 1);

    return {
      ...lesson,
      completed,
      unlocked
    };
  });

  res.json({
    "Programming Fundamentals": {
      lessons: lessonsWithState
    }
  });
});

async function runOllama(prompt) {
  try {
    const response = await fetch("http://localhost:11434/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: "llama3.1",
        prompt: prompt,
        stream: false
      })
    });

    const data = await response.json();

    // ⭐ GUARANTEE a string is returned
    if (!data || typeof data.response !== "string") {
      console.error("❌ Ollama returned invalid response:", data);
      return "";
    }

    return data.response;

  } catch (err) {
    console.error("❌ Ollama error:", err);
    return "";
  }
}

function cleanAIResponse(text) {
  if (!text || typeof text !== "string") {
    return "I'm not sure how to respond to that.";
  }

  return text
    .trim()
    .replace(/\n{3,}/g, "\n\n")
    .replace(/^#+\s*/gm, "")
    .replace(/\*\*/g, "");
}

function fallbackMCQ(lessonObj) {
  return {
    type: "multiple_choice",
    question: `What is the main purpose of ${lessonObj.title}?`,
    options: [
      "To manage and store data correctly in a program.", // <-- FIX: This used to be the massive paragraph!
      "Something unrelated to programming.",
      "A random incorrect definition."
    ],
    answer: 0
  };
}

function isValidTask(task) {
  if (!task || typeof task !== "object") return false;
  if (!task.type) return false;
  if (task.type !== "true_false" && !task.question) return false;

  if (task.type === "fill_blank") {
    if (!task.answer) return false;
    if (typeof task.answer !== "string") return false;
    if (!task.question.includes("____")) return false;
  }

  if (task.type === "multiple_choice") {
    if (!Array.isArray(task.options) || task.options.length < 2) return false;
    if (typeof task.answer !== "number") return false;
    if (task.answer < 0 || task.answer >= task.options.length) return false;
  }

  if (task.type === "code_output") {
    if (!task.code) return false;
    if (!Array.isArray(task.options) || task.options.length < 2) return false;
    if (typeof task.answer !== "number") return false;
  }

  return true;
}


// -------------------------
// AI GENERATION HELPERS
// -------------------------

async function generateInfoBlock(course, lessonObj, level, lessonState) {
  const prompt = `
You are Study Forge, an adaptive AI tutor. Write a friendly 2–4 sentence intro for the lesson: "${lessonObj.title}".

STRICT RULES:
1. DO NOT repeat the "labeled box" analogy if it was used before. Instead, use a different explanation like "name tags," "storage slots," or a direct technical overview.
2. Focus on the core concept: "${lessonObj.coreInfoBlock}".
3. Output ONLY JSON: { "type": "info", "content": "..." }
4. No markdown, no backticks.
`;

  const reply = await runOllama(prompt);
  const parsed = safeJSONParse(reply);

  if (!parsed || !parsed.content) {
    return {
      type: "info",
      content: `Welcome to ${lessonObj.title}! Today we're diving into ${lessonObj.description}. Let's get started!`
    };
  }
  return parsed;
}

async function generateTask(course, lessonObj, level, lessonState, lastInfoBlock) {
  let allowedTypes = ["multiple_choice", "fill_blank", "predict_output", "debug_code"];
  
  // Pick ONE type randomly to ensure variety
  const forcedType = allowedTypes[Math.floor(Math.random() * allowedTypes.length)];
  let grounding = lessonState.coreInfoBlock || lessonObj.coreInfoBlock;

  const prompt = `
You are an expert programming tutor creating a high-quality quiz question.

LESSON CONCEPT: "${grounding}"
TASK TYPE REQUIRED: ${forcedType}

STRICT RULES:
1. The question MUST test the core programming logic. Do NOT write vague questions.
2. If fill_blank: The answer MUST be a specific programming keyword (e.g., "while", "for", "array", "boolean"). It CANNOT be a generic English word like "sequence". No options array.
3. If multiple_choice: Options must be distinct, highly relevant, and under 10 words. No "joke" distractors.
4. FORMAT: Output ONLY raw, valid JSON. Do NOT wrap the JSON in markdown code blocks (\`\`\`).
5. NO RAW LINE BREAKS: You MUST escape all newlines in your code strings using the literal characters \\n. NEVER use actual line breaks inside a JSON string.

SCHEMA FORMATS (Use only the one for ${forcedType}):
- multiple_choice: {"type": "multiple_choice", "question": "...", "options": ["A", "B", "C"], "answer": 0}
- fill_blank: {"type": "fill_blank", "question": "A ____ loop runs as long as a condition is true.", "answer": "while"}
- predict_output: {"type": "predict_output", "question": "What is printed?", "code": "print(2+2)", "options": ["3", "4", "error"], "answer": 1}
- debug_code: {"type": "debug_code", "question": "Find the bug", "code": "while x < 5 print(x)", "options": ["Missing colon", "Infinite loop"], "answer": 0}
`;

  const reply = await runOllama(prompt);
  let parsed = safeJSONParse(reply);

  // Fallbacks for bad AI behavior
  if (!parsed || typeof parsed !== "object") return fallbackMCQ(lessonObj);
  if (forcedType === "fill_blank" && typeof parsed.answer === "number") return fallbackMCQ(lessonObj);
  
  if (!parsed.type) parsed.type = forcedType;

  // Validation
  if (parsed.type === "multiple_choice" && Array.isArray(parsed.options)) {
    return { type: "multiple_choice", question: parsed.question, options: parsed.options, answer: Number(parsed.answer) || 0 };
  }
  if (parsed.type === "fill_blank" && typeof parsed.answer === "string") {
    let a = parsed.answer.trim().toLowerCase().replace(/[.,!?;:()"]/g, "");
    if (!a.includes(" ")) return { type: "fill_blank", question: parsed.question, answer: a };
  }
  if (["predict_output", "debug_code"].includes(parsed.type) && parsed.code) {
      // 🌟 BUG 3 FIX: Flatten multi-line text in options so buttons don't explode!
      const flatOptions = (parsed.options || ["error"]).map(opt => 
        String(opt).replace(/\\n/g, ", ").replace(/\n/g, ", ")
      );
      
      return { 
        type: parsed.type, 
        question: parsed.question, 
        code: parsed.code, 
        options: flatOptions, 
        answer: Number(parsed.answer) || 0 
      };
    }

  return fallbackMCQ(lessonObj);
}

async function generateFeedback(userAnswer, course, lessonObj, level, lessonState) {
  const task = lessonState.lastTask;
  const taskType = task.type;
  let isCorrect = false;

  if (taskType === "multiple_choice" || taskType === "code_output" || taskType === "predict_output" || taskType === "debug_code") {
    isCorrect = Number(userAnswer) === Number(task.answer);
  } else if (taskType === "fill_blank") {
    isCorrect = String(userAnswer).trim().toLowerCase() === String(task.answer).trim().toLowerCase();
  } else if (taskType === "true_false") {
    isCorrect = (String(userAnswer).trim().toLowerCase() === "true") === task.answer;
  }

  if (isCorrect) {
    const rewards = ["Spot on!", "Nailed it!", "Excellent work.", "Perfect!", "Right on the money!"];
    return { correct: true, message: rewards[Math.floor(Math.random() * rewards.length)] };
  }

  // --- 🌟 FIRST CLASS DISSERTATION UPGRADE 🌟 ---
  const prompt = `
### SYSTEM ROLE
You are Study Forge, a supportive programming tutor. The student just got a question WRONG.
Provide an "intelligent nudge" (constructive scaffolding) to help them understand their mistake.

### CONTEXT
Question: "${task.question}"
Correct Answer: ${task.answer}
Student's Wrong Answer: ${userAnswer}

### INSTRUCTIONS
1. Acknowledge the attempt politely.
2. Explain WHY their answer is incorrect or give a strong hint guiding them to the right logic.
3. Keep it under 2 sentences. DO NOT just give them the final answer.
4. MUST output raw JSON format ONLY. NO markdown blocks (\`\`\`). Escape internal quotes with \\".

### REQUIRED JSON FORMAT:
{"message": "Your intelligent hint goes here"}
`;

  const reply = await runOllama(prompt);
  const parsed = safeJSONParse(reply);
  
  return { 
    correct: false, 
    message: parsed?.message || "Not quite! Think carefully about the syntax rules for this concept and try again." 
  };
}

async function generateSummary(course, lessonObj, level, lessonState) {
  const prompt = `You are Study Forge. Summary of ${lessonObj.title} in 2 sentences. Motivational. JSON: {"type": "summary", "content": "...", "encouragement": "..."}`;
  const reply = await runOllama(prompt);
  const parsed = safeJSONParse(reply);
  return parsed || { type: "summary", content: "Great lesson!", encouragement: "Keep going!" };
}

async function generateFollowUpAnswer(userMessage, lastInfoBlock) {
  // 1. Define the High-Level Pedagogical Prompt
  const prompt = `
### SYSTEM ROLE
You are "Study Forge," a world-class programming tutor. Your goal is to preserve student autonomy. 
You provide "scaffolding" (hints/logic), NOT solutions.

### CONTEXT
The student is currently learning about: "${lastInfoBlock?.content || "General Programming"}"

### INSTRUCTIONS FOR RESPONSE
1. If the user asks for a direct answer, to skip a task, or for "copy-paste" code:
   - Politely REFUSE. 
   - Explain that giving the answer prevents them from building the "mental muscle" for coding.
2. If the user is confused:
   - Break the concept into one smaller, manageable analogy.
   - Ask a "check for understanding" question at the end.
3. TONE: Professional, encouraging, but firm.
4. LIMIT: Maximum 3 sentences. No markdown headers.

### STUDENT MESSAGE
"${userMessage}"

### STUDY FORGE RESPONSE:`;

  try {
    const response = await runOllama(prompt);
    
    // 2. Clean the response to ensure no "AI chatter" (like "Sure, I can help")
    const cleanedResponse = response.replace(/^(Study Forge:|Response:)/i, "").trim();
    
    return { content: cleanedResponse };
  } catch (err) {
    console.error("❌ Error in Study Forge Follow-up:", err);
    return { content: "I'm having a little trouble connecting to my brain. Could you try asking that again?" };
  }
}

app.get("/me", auth, (req, res) => {
  try {
    // 1. Fetch the user AND their progress in one single query
    const user = db.prepare(`
      SELECT 
        users.id, 
        users.email, 
        progress.xp, 
        progress.level, 
        progress.streak, 
        progress.achievements,
        progress.completed_lessons
      FROM users 
      JOIN progress ON users.id = progress.user_id 
      WHERE users.id = ?
    `).get(req.userId);

    if (!user) {
      console.log(`❌ /me failed: User ${req.userId} not found`);
      return res.status(404).json({ error: "User not found" });
    }

    // 2. Parse JSON strings back into objects so Python can read them
    user.achievements = JSON.parse(user.achievements || '{}');
    user.completed_lessons = JSON.parse(user.completed_lessons || '[]');

    console.log(`✅ /me success for: ${user.email} (Level: ${user.level})`);
    
    // 3. Send the full object back to the Python app
    res.json(user);

  } catch (err) {
    console.error("Critical error in /me route:", err);
    res.status(500).json({ error: "Server error fetching user profile" });
  }
});

function auth(req, res, next) {
  const header = req.headers.authorization;

  console.log("FULL AUTH HEADER:", header);

  if (!header) 
    return res.status(401).json({ error: "No token provided" });

  const token = header.split(" ")[1];

  console.log("EXTRACTED TOKEN:", token);

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.userId = decoded.userId;
    next();
  } catch (err) {
    console.log("JWT VERIFY ERROR:", err.message);
    return res.status(401).json({ error: "Invalid token" });
  }
}

function saveUserProgress(userId, progression) {
  db.prepare(`
    INSERT INTO progress (user_id, xp, level, streak, last_active_date, achievements, completed_lessons)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(user_id) DO UPDATE SET
      xp = excluded.xp,
      level = excluded.level,
      streak = excluded.streak,
      last_active_date = excluded.last_active_date,
      achievements = excluded.achievements,
      completed_lessons = excluded.completed_lessons
  `).run(
    userId,
    progression.xp || 0,
    progression.level || 1,
    progression.streak || 0,
    progression.lastActiveDate || new Date().toDateString(),
    JSON.stringify(progression.achievements || {}),
    JSON.stringify(progression.completedLessons || [])
  );
}

function applyXP(progression, amount) {
  progression.xp += amount;

  // XP needed grows with level (Level 1 = 50, Level 2 = 100, Level 3 = 150…)
  let xpNeeded = progression.level * 50;

  while (progression.xp >= xpNeeded) {
    progression.xp -= xpNeeded;
    progression.level++;
    xpNeeded = progression.level * 50;

    // LEVEL ACHIEVEMENTS
    if (progression.level === 2) unlockAchievement(progression, "level_2");
    if (progression.level === 3) unlockAchievement(progression, "level_3");
    if (progression.level === 4) unlockAchievement(progression, "level_4");
    if (progression.level === 5) unlockAchievement(progression, "level_5");
    if (progression.level === 6) unlockAchievement(progression, "level_6");
    if (progression.level === 7) unlockAchievement(progression, "level_7");
    if (progression.level === 8) unlockAchievement(progression, "level_8");
    if (progression.level === 9) unlockAchievement(progression, "level_9");
    if (progression.level === 10) unlockAchievement(progression, "level_10");
  }
}

app.post("/lesson/start", auth, (req, res) => {
  const userId = req.userId;

  lessonStates[userId] = {
    phase: "intro",
    step: 0,
    totalSteps: 0,
    currentStepCorrect: true,
    lastInfoBlock: null,
    lastTask: null,
    lastAnswer: null,
    questionCount: 0,
    maxQuestions: 4,
    tasksCompleted: 0,
    taskStage: 0,
    correctStreak: 0,
    incorrectStreak: 0
  };

  console.log("🔥 LESSON RESET FOR USER:", userId);
  res.json({ info: "Welcome! Press continue to start the lesson." });
});

// Chat route for LessonWindow (Lesson Cycle Engine + AI)
app.post('/chat', auth, async (req, res) => {
  const { message, course, lesson, level, task_answer, force_reset } = req.body;
  const userId = req.userId;

  // Optional hard reset
  if (force_reset === true) {
    resetLessonState(userId);
  }

  let state = lessonStates[userId];
  if (!state) return res.status(400).json({ error: "Lesson not started. Call /lesson/start before /chat." });

  const userMessage = (message || "").trim();
  if (userMessage.toLowerCase() === "hello") {
    resetLessonState(userId);
    state = lessonStates[userId];
  }

  // Load progression safely
  let prog = db.prepare(`SELECT * FROM progress WHERE user_id = ?`).get(userId);

  if (!prog) {
    db.prepare(`
      INSERT INTO progress (user_id, xp, level, streak, last_active_date, achievements, completed_lessons)
      VALUES (?, 0, 1, 0, ?, '{}', '[]')
    `).run(userId, new Date().toDateString());

    prog = db.prepare(`SELECT * FROM progress WHERE user_id = ?`).get(userId);
  }

  let achievementsParsed = JSON.parse(prog.achievements || "{}");
  if (Array.isArray(achievementsParsed)) {
    const converted = {};
    for (const key of achievementsParsed) {
      converted[key] = true;
    }
    achievementsParsed = converted;
  }

  let progression = {
    xp: prog.xp,
    level: prog.level,
    streak: prog.streak,
    lastActiveDate: prog.last_active_date,
    achievements: achievementsParsed,
    completedLessons: JSON.parse(prog.completed_lessons || "[]")
  };

  // Collect all achievements unlocked during this request
    const newlyUnlocked = [];

    // Helper to unlock and push nice names
    function tryUnlock(codeName) {
      if (unlockAchievement(progression, codeName)) {
        newlyUnlocked.push(ACHIEVEMENT_NAMES[codeName] || codeName);
      }
    }

    // First Message Achievement
    if (userMessage && !progression.achievements?.first_message) {
      tryUnlock("first_message");
    }

    // Streak Achievement + Achievement update
    updateStreak(progression);
    if (progression.streak === 2) tryUnlock("two_day_streak");
    if (progression.streak === 3) tryUnlock("three_day_streak");
    if (progression.streak === 5) tryUnlock("five_day_streak");
    if (progression.streak === 7) tryUnlock("seven_day_streak");

  saveUserProgress(userId, progression);

  const courses = loadCourses();
  const courseData = courses[course];
  if (!courseData) return res.json({ info: "Course not found.", newlyUnlocked });

  const lessonIdNum = Number(lesson);
  const lessonObj = courseData.lessons.find(l => l.id === lessonIdNum);
  if (!lessonObj) return res.json({ info: "Lesson not found.", newlyUnlocked });

  console.log("🔥 NEW CHAT ROUTE ACTIVE");

  const isTestLesson = (lessonIdNum === 10);

  // 1) INTRO PHASE
  if (state.phase === "intro"){
    const introPrompt = `
You are Study Forge, a friendly AI tutor.
Write ONLY a welcome message for the lesson.
STRICT RULES:
- No teaching content
- No tasks
- No questions
- 2–3 motivational sentences

Lesson title: ${lessonObj.title}
Difficulty: ${lessonObj.difficulty}
`;

    const intro = await runOllama(introPrompt);
    state.phase = isTestLesson ? "test_intro" : "info_detail";

    return res.json({ info: cleanAIResponse(intro), newlyUnlocked });
  }

  // Test Intro (LESSON 10 ONLY)
  if (isTestLesson && state.phase === "test_intro") {

    const testIntro = `
This final lesson is a test of everything you've learned so far.
You'll answer questions covering the core concepts.
Good luck!
    `.trim();

    const testKnowledge = courseData.lessons
      .filter(l => l.id !== 10)
      .map(l => `• ${l.title}: ${l.description}`)
      .join("\n");

    state.coreInfoBlock = `
This is the final test for the course "${course}".
It covers:

${testKnowledge}
`.trim();

    state.lastInfoBlock = { content: state.coreInfoBlock };
    state.phase = "task";

    return res.json({ info: testIntro, newlyUnlocked });
  }
    if (!isTestLesson && state.phase === "task" && message === "continue" && typeof task_answer === "undefined") {
      if (state.lastTask) {
        console.log("🛡️ Shield activated: Ignored accidental 'continue' during a task.");
        return res.json({ task: state.lastTask, newlyUnlocked });
      }
    }

    // 2) Info Detail Phase
    if (!isTestLesson && state.phase === "info_detail") {
      let difficultyRules = "";
      if (lessonObj.difficulty === "easy") difficultyRules = "- Simple language, no code.";
      else if (lessonObj.difficulty === "medium") difficultyRules = "- Use light technical terms and 1-2 lines of code.";
      else if (lessonObj.difficulty === "hard") difficultyRules = "- Deep reasoning and complex code examples.";

      const detailPrompt = `
        You are Study Forge, a technical programming tutor.
        ${!state.currentStepCorrect ? "The student got the last task WRONG. Clarify their mistake first." : ""}
        
        Explain the concept: "${lessonObj.title}".
        Core Concept: "${lessonObj.coreInfoBlock}"
        
        STRICT RULES:
        - 3 to 4 sentences MAXIMUM.
        - DO NOT use the "labeled box" analogy. Try a different one or use direct technical terms.
        - Be clear and motivating.
        ${difficultyRules}
      `;

      const detail = await runOllama(detailPrompt); 
      const cleaned = cleanAIResponse(detail);

      if (!state.coreInfoBlock) {
          state.coreInfoBlock = lessonObj.coreInfoBlock;
      }

      state.lastInfoBlock = { content: cleaned };
      state.phase = "ask";

      return res.json({
        info: cleaned,
        newlyUnlocked
      });
    }

  // 3) Ask Phase
  if (state.phase === "ask") {
    const msg = (userMessage || "").trim().toLowerCase();

    // First time entering ASK phase
    if (!msg || msg === "continue") {
      return res.json({
        info: "Would you like to ask anything about this topic before we continue?",
        newlyUnlocked
      });
    }

    // Treat skip as "no"
    if (msg === "no" || msg === "skip") {
      state.phase = "task";
      return res.json({
        info: "Alright! Let's jump straight into a quick task.",
        newlyUnlocked
      });
    }

    if (msg === "yes") {
      state.phase = "questions";
      return res.json({
        info: "Great! What would you like to ask?",
        newlyUnlocked
      });
    }

    // Any other input treated as question
    state.phase = "questions";
    return res.json({
      info: "Great! What would you like to ask?",
      newlyUnlocked
    });
  }

  // 4) Free Text Question
  if (
    !isTestLesson &&
    state.phase === "questions" &&
    userMessage &&
    !["continue", "next"].includes(userMessage.toLowerCase())
  ) {
    const followup = await generateFollowUpAnswer(userMessage, state.lastInfoBlock);
    state.questionCount++;

    if (
      state.questionCount >= state.maxQuestions ||
      userMessage.toLowerCase().includes("continue") ||
      userMessage.toLowerCase().includes("next")
    ) {
      state.phase = "task";
    } else {
      state.phase = "info_detail";
    }
    return res.json({ info: followup.content, newlyUnlocked });
  }

  // 5) Normal Task Mode (LESSONS 1–9)
  if (!isTestLesson && state.phase === "task") {
    if (typeof task_answer !== "undefined") {
      state.lastAnswer = task_answer;

      const feedback = await generateFeedback(
        task_answer,
        course,
        lessonObj,
        level,
        state
      );

      state.lastTask = null;

      // Increment ONCE per task
      state.tasksCompleted += 1;

      const wasCorrect = feedback.correct;
      const previousStage = state.taskStage;

      if (wasCorrect) {
        state.correctStreak = (state.correctStreak || 0) + 1;
        state.incorrectStreak = 0;

        if (state.correctStreak >= 2) {
          const maxStage =
            lessonObj.difficulty === "easy" ? 3 :
            lessonObj.difficulty === "medium" ? 5 :
            7;

          state.taskStage = Math.min(state.taskStage + 1, maxStage);
          state.correctStreak = 0;
        }
      } else {
        state.incorrectStreak = (state.incorrectStreak || 0) + 1;
        state.correctStreak = 0;

        if (state.incorrectStreak >= 2) {
          state.taskStage = Math.max(state.taskStage - 1, 0);
          state.incorrectStreak = 0;
        }
      }

      if (feedback.correct) {
        let xpGain =
          lessonObj.difficulty === "easy"
            ? 8
            : lessonObj.difficulty === "medium"
            ? 12
            : 16;

        const stageBonus = [0, 2, 4][state.taskStage] || 0;
        xpGain += stageBonus;

        applyXP(progression, xpGain);
        saveUserProgress(userId, progression);

        state.currentStepCorrect = true;
      } else {
        state.currentStepCorrect = false;
      }
      const finishedByCount =
        state.tasksCompleted >= (
          lessonObj.difficulty === "easy" ? 4 :
          lessonObj.difficulty === "medium" ? 6 :
          8
        ) && feedback.correct;

      const finishedByStages =
        state.taskStage >= (
          lessonObj.difficulty === "easy" ? 3 :
          lessonObj.difficulty === "medium" ? 5 :
          7
        ) && feedback.correct;

      state.phase =
        finishedByCount || finishedByStages ? "summary" : "info_detail";

      if (state.phase === "summary") {
        const summary = await generateSummary(
          course,
          lessonObj,
          level,
          state
        );

        // Mark lesson complete
        markLessonComplete(userId, lessonIdNum, progression);

        // Lesson Count Achievement
        const lessonCount = progression.completedLessons.length;
        
        function tryUnlockLesson(codeName) {
            if (unlockAchievement(progression, codeName)) {
              newlyUnlocked.push(ACHIEVEMENT_NAMES[codeName] || codeName);
            }
        }

        if (lessonCount >= 1) tryUnlockLesson("first_lesson_completed");
        if (lessonCount >= 3) tryUnlockLesson("three_lessons_completed");
        if (lessonCount >= 5) tryUnlockLesson("five_lessons_completed");
        if (lessonCount >= 10) tryUnlockLesson("ten_lessons_completed");
        
        saveUserProgress(userId, progression);

        let bonusXP =
          lessonObj.difficulty === "medium"
            ? 30
            : lessonObj.difficulty === "hard"
            ? 40
            : 20;

        applyXP(progression, bonusXP);
        saveUserProgress(userId, progression);

        const progressionPayload = buildProgressionPayload(progression);

        // 1. Reset state 
        resetLessonState(userId);
        
        // 2. Queue up the next lesson
        lessonStates[userId].lesson = lessonIdNum + 1;

        return res.json({
          summary: {
            xp: bonusXP,
            new_xp_total: progressionPayload.xp,
            level: progressionPayload.level,
            xpNeeded: progressionPayload.xpNeeded,
            xpToNext: progressionPayload.xpToNext,
            achievements: progressionPayload.achievements,
            streak: progressionPayload.streak,
            text: summary.content,
            encouragement: summary.encouragement,
            next_lesson: lessonIdNum + 1 
          },
          newlyUnlocked
        });
      }

      return res.json({
        feedback: {
          correct: feedback.correct,
          message: feedback.message,
          taskStage: state.taskStage
        },
        newlyUnlocked
      });
    }

    // Generate new task
    if (state.tasksCompleted === 0) {
      state.lastTask = null;
      state.currentStepCorrect = true;
    }

    let task;

    if (!state.currentStepCorrect && state.lastTask) {
      task =
        Math.random() < 0.5
          ? state.lastTask
          : await generateTask(
              course,
              lessonObj,
              level,
              state,
              state.lastInfoBlock
            );
    } else {
      task = await generateTask(
        course,
        lessonObj,
        level,
        state,
        state.lastInfoBlock
      );
    }

    state.lastTask = task;

    return res.json({ task, newlyUnlocked });
  }

  // 6) Final Test Mode (LESSON 10)
  if (isTestLesson && state.phase === "task") {

    const pastLessons = courseData.lessons.filter(l => l.id !== 10);
    const randomLessonToTest = pastLessons[Math.floor(Math.random() * pastLessons.length)];

    const testLesson = {
      title: randomLessonToTest.title, 
      coreInfoBlock: randomLessonToTest.description || randomLessonToTest.title,
      difficulty: "hard",
      type: "test"
    };

    if (typeof task_answer !== "undefined") {
          state.lastAnswer = task_answer;

          const feedback = await generateFeedback(
            task_answer,
            course,
            testLesson,
            level,
            state
          );

          state.tasksCompleted++;
          state.lastTask = null; 

          if (state.tasksCompleted >= 10) {
              state.phase = "summary";
              
              // Mark as complete
              markLessonComplete(userId, 10, progression);
              
              // Apply a massive 100 XP bonus for passing the final test
              applyXP(progression, 100); 
              saveUserProgress(userId, progression);
              
              const progressionPayload = buildProgressionPayload(progression);
              resetLessonState(userId); 

              return res.json({
                summary: {
                  xp: 100,
                  new_xp_total: progressionPayload.xp,
                  level: progressionPayload.level,
                  xpNeeded: progressionPayload.xpNeeded,
                  xpToNext: progressionPayload.xpToNext,
                  achievements: progressionPayload.achievements,
                  streak: progressionPayload.streak,
                  text: "You have completed the Final Test! You've proven your mastery of the programming fundamentals.",
                  encouragement: "Congratulations on finishing the course! 🎉",
                  next_lesson: null 
                },
                newlyUnlocked
              });
          }

      // Dynamic Difficulty Scaling for the Final Test
      if (state.tasksCompleted === 1) state.taskStage = 1;      // Recall
      if (state.tasksCompleted === 2) state.taskStage = 3;      // Application
      if (state.tasksCompleted >= 3) state.taskStage = 7;       // Mastery (Hardest)

          return res.json({
            feedback: {
              correct: feedback.correct,
              message: feedback.message,
              taskStage: state.taskStage
            },
            newlyUnlocked
          });
        }

    const task = await generateTask(
      course,
      testLesson,
      level,
      state,
      state.lastInfoBlock
    );

    state.lastTask = task;
    return res.json({ task, newlyUnlocked });
  }

  // 7) Failsafe
  return res.json({ info: "Unexpected state. Resetting lesson.", newlyUnlocked });
});

app.get("/progression", auth, (req, res) => {

  let prog = db.prepare(`SELECT * FROM progress WHERE user_id = ?`).get(req.userId);

  // Safety fallback if user has no progress yet
  if (!prog) {
    prog = {
      xp: 0,
      level: 1,
      streak: 0,
      achievements: '{}',
      completed_lessons: '[]'
    };
  }

  let achievements = JSON.parse(prog.achievements || "{}");

  // If DB stored "[]", convert to {}
  if (Array.isArray(achievements)) {
    achievements = {};
  }

  const progression = {
    xp: prog.xp,
    level: prog.level,
    streak: prog.streak,
    achievements: achievements,
    completedLessons: JSON.parse(prog.completed_lessons || "[]"),
    xpNeeded: prog.level * 50,
    xpToNext: (prog.level * 50) - prog.xp
  };

  res.json(progression);
});

app.post("/progression/update", auth, (req, res) => {
  const { xp, level, streak, achievements, completedLessons } = req.body;

  if (!req.userId) {
    return res.status(401).json({ error: "Unauthorized" });
  }

  try {
    const stmt = db.prepare(`
      INSERT INTO progress (user_id, xp, level, streak, achievements, completed_lessons)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(user_id) DO UPDATE SET
        xp = excluded.xp,
        level = excluded.level,
        streak = excluded.streak,
        achievements = excluded.achievements,
        completed_lessons = excluded.completed_lessons
    `);

    stmt.run(
      req.userId,
      xp || 0,
      level || 1,
      streak || 0,
      JSON.stringify(achievements || {}),
      JSON.stringify(completedLessons || [])
    );

    res.json({ success: true });
  } catch (err) {
    console.error("Error saving progress:", err);
    res.status(500).json({ error: "Failed to save progress" });
  }
});

// Save Progress
app.post("/save_progress", auth, (req, res) => {
  const { xp, level, streak, achievements, completedLessons } = req.body;

  try {
    db.prepare(`
      INSERT INTO progress (user_id, xp, level, streak, achievements, completed_lessons)
      VALUES (?, ?, ?, ?, ?, ?)
      ON CONFLICT(user_id) DO UPDATE SET
        xp = excluded.xp,
        level = excluded.level,
        streak = excluded.streak,
        achievements = excluded.achievements,
        completed_lessons = excluded.completed_lessons
    `).run(
      req.userId,
      xp,
      level,
      streak,
      JSON.stringify(achievements || {}),
      JSON.stringify(completedLessons || [])
    );

    res.json({ success: true });
  } catch (err) {
    console.error("Failed to save progress:", err);
    res.status(500).json({ success: false, error: err.message });
  }
});

app.listen(PORT, () => {
  console.log("🔥 Backend running on port " + PORT);
});