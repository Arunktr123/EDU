"""
SUPERNATURAL - N8N Webhook Routes
N8N calls these endpoints to trigger autonomous platform actions:
  1. POST /api/webhooks/trigger-matching      — Batch match unmatched students
  2. POST /api/webhooks/send-daily-meets      — Send today's Meet links
  3. POST /api/webhooks/generate-quiz         — Generate post-class quiz
  4. POST /api/webhooks/send-quiz-reminders   — Remind students to complete pending quizzes
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database import get_db
from app.config import settings
from app.models.session import ClassSession
from app.models.quiz import Quiz, QuizResult
from app.models.student import Student
from app.services.matching_service import MatchingService
from app.services.email_service import EmailService
from app.services.quiz_service import QuizService

router = APIRouter()


# ── N8N Auth Guard ────────────────────────────────────────────────────────────
def verify_n8n_key(x_n8n_api_key: str = Header(...)):
    """Simple API key auth for N8N to call platform webhooks securely."""
    if x_n8n_api_key != settings.N8N_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid N8N API key")


# ── 1. Batch Mentor-Student Matching ─────────────────────────────────────────
@router.post("/trigger-matching")
def webhook_trigger_matching(
    db: Session = Depends(get_db),
    _: None = Depends(verify_n8n_key),
):
    """
    N8N TRIGGER: Run autonomous mentor-student matching for all unmatched students.
    N8N Schedule: Every hour or on new student registration.
    """
    service = MatchingService(db)
    result = service.run_batch_matching()
    return {
        "webhook": "trigger-matching",
        "timestamp": datetime.utcnow().isoformat(),
        **result,
    }


# ── 2. Send Daily Meet Links ──────────────────────────────────────────────────
@router.post("/send-daily-meets")
def webhook_send_daily_meets(
    db: Session = Depends(get_db),
    _: None = Depends(verify_n8n_key),
):
    """
    N8N TRIGGER: Find all sessions scheduled for today and send Meet links.
    N8N Schedule: Every morning at 7:00 AM (cron: 0 7 * * *).
    """
    from datetime import timedelta
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start + timedelta(days=1)

    sessions = (
        db.query(ClassSession)
        .filter(
            ClassSession.scheduled_at >= today_start,
            ClassSession.scheduled_at < today_end,
            ClassSession.is_email_sent == False,
        )
        .all()
    )

    email_service = EmailService()
    sent_count = 0

    for session in sessions:
        if session.attendees and session.meet_link:
            try:
                email_service.send_meet_link(
                    student_emails=session.attendees,
                    session_title=session.title,
                    meet_link=session.meet_link,
                    scheduled_at=session.scheduled_at,
                    duration_minutes=session.duration_minutes,
                    mentor_name=session.mentor.user.full_name if session.mentor else "Mentor",
                )
                session.is_email_sent = True
                sent_count += 1
            except Exception as e:
                pass  # log and continue for other sessions

    db.commit()
    return {
        "webhook": "send-daily-meets",
        "sessions_found": len(sessions),
        "emails_sent": sent_count,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── 3. Post-Class Quiz Generation ────────────────────────────────────────────
class QuizGeneratePayload(BaseModel):
    session_id: int
    topic: str


@router.post("/generate-quiz")
def webhook_generate_quiz(
    payload: QuizGeneratePayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_n8n_key),
):
    """
    N8N TRIGGER: After class ends, auto-generate and activate a quiz.
    N8N Schedule: N8N waits for session end time + 5 min, then calls this.
    """
    service = QuizService(db)
    quiz = service.generate_quiz_for_session(
        session_id=payload.session_id,
        topic=payload.topic,
    )

    # Notify students quiz is ready
    session = db.query(ClassSession).filter(ClassSession.id == payload.session_id).first()
    if session and session.attendees:
        email_service = EmailService()
        for email in session.attendees:
            try:
                email_service._send(
                    to_emails=[email],
                    subject=f"📝 Quiz Ready: {quiz.title} | SUPERNATURAL",
                    html_body=f"""
                    <html><body style="font-family:Arial,sans-serif;padding:20px;">
                    <div style="max-width:600px;margin:auto;background:white;
                                border-radius:12px;padding:30px;">
                        <h1 style="color:#6c63ff;">📝 Your Quiz is Ready!</h1>
                        <p>A quiz has been prepared based on today's class:</p>
                        <h2 style="color:#6c63ff;">{quiz.title}</h2>
                        <p>📚 Subject: {quiz.subject}</p>
                        <p>⏱ Time Limit: {quiz.time_limit_mins} minutes</p>
                        <p>📊 Total Marks: {quiz.total_marks}</p>
                        <div style="text-align:center;margin:20px 0;">
                            <a href="http://localhost:8000/quiz/{quiz.id}"
                               style="background:#6c63ff;color:white;padding:15px 30px;
                                      border-radius:8px;text-decoration:none;font-weight:bold;">
                                Start Quiz Now
                            </a>
                        </div>
                    </div></body></html>
                    """,
                )
            except Exception:
                pass

    return {
        "webhook": "generate-quiz",
        "quiz_id": quiz.id,
        "questions": len(quiz.questions),
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── 4. Quiz Reminders ─────────────────────────────────────────────────────────
@router.post("/send-quiz-reminders")
def webhook_quiz_reminders(
    db: Session = Depends(get_db),
    _: None = Depends(verify_n8n_key),
):
    """
    N8N TRIGGER: Remind students who haven't completed pending quizzes.
    N8N Schedule: Every evening at 8:00 PM (cron: 0 20 * * *).
    """
    active_quizzes = db.query(Quiz).filter(Quiz.is_active == True).all()
    email_service = EmailService()
    reminders_sent = 0

    for quiz in active_quizzes:
        session = quiz.session
        if not session or not session.attendees:
            continue

        # Find students who haven't submitted
        submitted_ids = {r.student.user.email for r in quiz.results if r.student and r.student.user}
        pending_emails = [e for e in session.attendees if e not in submitted_ids]

        for email in pending_emails:
            try:
                email_service._send(
                    to_emails=[email],
                    subject=f"⏰ Reminder: Complete your quiz | {quiz.title}",
                    html_body=f"""
                    <html><body style="font-family:Arial,sans-serif;padding:20px;">
                    <div style="max-width:600px;margin:auto;background:white;
                                border-radius:12px;padding:30px;">
                        <h1 style="color:#ff6b6b;">⏰ Don't Forget Your Quiz!</h1>
                        <p>You have a pending quiz from today's class:</p>
                        <h2 style="color:#6c63ff;">{quiz.title}</h2>
                        <div style="text-align:center;margin:20px 0;">
                            <a href="http://localhost:8000/quiz/{quiz.id}"
                               style="background:#6c63ff;color:white;padding:15px 30px;
                                      border-radius:8px;text-decoration:none;font-weight:bold;">
                                Take Quiz Now
                            </a>
                        </div>
                    </div></body></html>
                    """,
                )
                reminders_sent += 1
            except Exception:
                pass

    return {
        "webhook": "quiz-reminders",
        "reminders_sent": reminders_sent,
        "timestamp": datetime.utcnow().isoformat(),
    }

