# ⚡ SUPERNATURAL — Fully Autonomous Education Platform

> A 100% autonomous AI-powered education platform. No human intervention required.  
> AI matches mentors to students • Auto-schedules Google Meet classes • Generates quizzes • Sends personalized feedback — all via **N8N automation**.

---

## Architecture Overview

```
Student/Mentor          FastAPI Backend              N8N Automation
─────────────          ───────────────              ──────────────
Fill Preferences   →   /api/students/preferences  ← Every hour: trigger-matching
                   →   /api/mentors/preferences
                        ↓
                   Matching Service (AI Score)
                        ↓
                   Assign Mentor + Email Both
                        ↑
                   N8N: 7AM daily         →   /api/webhooks/send-daily-meets
                   (send Meet links)           Google Calendar API → Meet Link
                                               Gmail SMTP → Email Students
                        ↑
                   N8N: Session ends      →   /api/webhooks/generate-quiz
                   (quiz generation)           OpenAI GPT-4o → 5 MCQ Questions
                                               Auto-email quiz to students
                        ↑
                   N8N: 8PM daily         →   /api/webhooks/send-quiz-reminders
                   (quiz reminders)            Email pending students
                        ↑
                   Student submits quiz   →   /api/quizzes/submit
                                               AI evaluates + generates feedback
                                               Email result to student instantly
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend**       | FastAPI (Python 3.11) |
| **Automation**    | N8N (no-code workflows) |
| **Database**      | SQLite (dev) / PostgreSQL (prod) |
| **AI**            | OpenAI GPT-4o |
| **Meetings**      | Google Calendar API + Google Meet |
| **Email**         | Gmail SMTP |
| **Cache/Queue**   | Redis |
| **Frontend**      | Jinja2 + HTML/CSS/JS |
| **Containerized** | Docker + Docker Compose |

---

## Project Structure

```
SUPERNATURAL/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint
│   │   ├── config.py                  # All settings via .env
│   │   ├── database.py                # SQLAlchemy setup
│   │   ├── models/
│   │   │   ├── user.py                # Base user model
│   │   │   ├── mentor.py              # Mentor + preferences
│   │   │   ├── student.py             # Student + preferences + progress
│   │   │   ├── session.py             # Class sessions + Meet links
│   │   │   └── quiz.py                # Quizzes, questions, results
│   │   ├── services/
│   │   │   ├── matching_service.py    # AI scoring + mentor-student matching
│   │   │   ├── google_meet_service.py # Create Google Meet events
│   │   │   ├── email_service.py       # All email types (meet, quiz, match)
│   │   │   ├── quiz_service.py        # AI quiz generation + evaluation
│   │   │   └── llm_service.py         # OpenAI quiz + feedback generation
│   │   └── api/routes/
│   │       ├── auth.py                # Register, login, JWT
│   │       ├── mentors.py             # Mentor profile + preferences
│   │       ├── students.py            # Student profile + preferences
│   │       ├── sessions.py            # Create sessions, send Meet links
│   │       ├── quizzes.py             # Generate, submit, view quizzes
│   │       └── webhooks.py            # N8N webhook endpoints
│   ├── Dockerfile
│   └── requirements.txt
├── n8n_workflows/
│   ├── mentor_student_matching.json   # Import into N8N
│   ├── daily_meeting_scheduler.json   # Import into N8N
│   └── quiz_automation.json           # Import into N8N
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html                 # Landing page
│   │   ├── student_onboarding.html    # Student registration + preferences
│   │   ├── mentor_onboarding.html     # Mentor registration + preferences
│   │   └── dashboard.html             # Unified dashboard
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── docker-compose.yml
└── .env.example
```

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
# 1. Clone and navigate
cd SUPERNATURAL

# 2. Set up environment
copy .env.example .env
# Edit .env with your credentials

# 3. Start everything
docker-compose up -d

# 4. Access the platform
# App:  http://localhost:8000
# N8N:  http://localhost:5678  (admin / supernatural123)
# Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
# 1. Create virtual environment
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up environment
copy ..\\.env.example ..\\.env
# Edit .env with your credentials

# 4. Run the server
cd ..
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Configuration Guide

### 1. Google Meet / Calendar Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project → Enable **Google Calendar API**
3. Create OAuth 2.0 credentials (Desktop app)
4. Download JSON → save as `credentials/google_credentials.json`
5. First run will open browser for OAuth — token saved automatically

### 2. Gmail SMTP (App Password)
1. Go to Google Account → Security → 2-Step Verification (enable)
2. Security → App Passwords → Create for "Mail"
3. Copy 16-character password → set as `SMTP_PASSWORD` in `.env`

### 3. OpenAI API Key
1. Go to [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
2. Create new key → set as `OPENAI_API_KEY` in `.env`

### 4. N8N Workflow Setup
1. Open N8N at `http://localhost:5678`
2. Import each workflow from `n8n_workflows/` folder
3. Create credential: **HTTP Header Auth**
   - Name: `SUPERNATURAL API Key`
   - Header Name: `x-n8n-api-key`
   - Header Value: your `N8N_API_KEY` from `.env`
4. Set environment variable in N8N: `SUPERNATURAL_API_URL=http://api:8000`
5. Activate all 3 workflows

---

## N8N Automation Schedules

| Workflow | Schedule | Action |
|---|---|---|
| Mentor-Student Matching | Every hour | Auto-match unmatched students to best mentor |
| Daily Meeting Scheduler | 7:00 AM daily | Send Google Meet links to all students |
| Quiz Generation | On-demand (session end) | Generate AI quiz + notify students |
| Quiz Reminders | 8:00 PM daily | Remind students who haven't completed quiz |

---

## API Documentation

Once running, visit `http://localhost:8000/docs` for full Swagger UI.

### Key Endpoints

#### Auth
```
POST /api/auth/register    — Register student or mentor
POST /api/auth/login       — Login, receive JWT token
GET  /api/auth/me          — Get current user
```

#### Students
```
GET  /api/students/profile       — View profile + match status
PUT  /api/students/preferences   — Set preferences (triggers auto-matching)
GET  /api/students/quiz-history  — View all past quiz results
```

#### Mentors
```
GET  /api/mentors/profile       — View profile + student list
PUT  /api/mentors/preferences   — Update teaching preferences
GET  /api/mentors/students      — List assigned students
```

#### Sessions
```
POST /api/sessions/        — Create session (auto-generates Meet + sends email)
GET  /api/sessions/        — List upcoming sessions
POST /api/sessions/{id}/resend-meet  — Re-send Meet link
```

#### Quizzes
```
POST /api/quizzes/generate   — Generate AI quiz for a session
GET  /api/quizzes/{id}       — Get quiz questions (students)
POST /api/quizzes/submit     — Submit answers (auto-evaluates + emails result)
GET  /api/quizzes/results/me — View all results
```

#### N8N Webhooks (secured with API key)
```
POST /api/webhooks/trigger-matching     — Batch match all unmatched students
POST /api/webhooks/send-daily-meets     — Send today's Meet links
POST /api/webhooks/generate-quiz        — Generate quiz after session
POST /api/webhooks/send-quiz-reminders  — Evening quiz reminder
```

---

## Autonomous Flow Walkthrough

```
Day 1 — Student Registers
  → Fills preferences (subjects, level, time, style)
  → System scores against all mentors
  → Best match assigned automatically
  → Both student & mentor receive match confirmation email

Day 2+ — Continuous Learning Loop
  07:00 AM → N8N sends Google Meet link to student's email
  10:00 AM → Class happens on Google Meet
  10:05 AM → Mentor signals session ended (POST to N8N webhook)
  10:10 AM → N8N waits 5 min, then calls generate-quiz
  10:10 AM → GPT-4o generates 5 MCQ questions on today's topic
  10:10 AM → Student receives "Your quiz is ready" email
  ~Afternoon→ Student submits quiz answers
             → AI grades instantly + generates personalized feedback
             → Student receives score + feedback email automatically
  08:00 PM → N8N reminds any student who hasn't submitted yet

  REPEAT DAILY — FOREVER — ZERO HUMAN INVOLVEMENT
```

---

## License

MIT License — Built with ❤️ for autonomous learning
 
 