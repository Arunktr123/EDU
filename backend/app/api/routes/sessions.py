"""
SUPERNATURAL - Session Routes
Create and manage class sessions; auto-generate Meet links and send emails
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from app.database import get_db
from app.models.session import ClassSession
from app.models.mentor import Mentor
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.google_meet_service import GoogleMeetService
from app.services.email_service import EmailService

router = APIRouter()


class SessionCreateRequest(BaseModel):
    title: str
    subject: str
    description: Optional[str] = None
    scheduled_at: datetime         # ISO format: "2026-03-01T10:00:00"
    duration_minutes: int = 60
    is_recurring: bool = True


@router.post("/", status_code=201)
def create_session(
    payload: SessionCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mentor creates a class session.
    Platform autonomously:
      1. Creates Google Meet link
      2. Sends Meet link to all enrolled students via email
    """
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.id).first()
    if not mentor:
        raise HTTPException(status_code=403, detail="Only mentors can create sessions")

    # ── Create DB Record ──────────────────────────────────────────────────
    session = ClassSession(
        mentor_id=mentor.id,
        title=payload.title,
        subject=payload.subject,
        description=payload.description,
        scheduled_at=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        is_recurring=payload.is_recurring,
    )
    db.add(session)
    db.flush()

    # ── Collect Student Emails ────────────────────────────────────────────
    student_emails = [s.user.email for s in (mentor.students or []) if s.user]
    session.attendees = student_emails

    # ── Autonomous: Create Google Meet ────────────────────────────────────
    meet_service = GoogleMeetService()
    meet_result = meet_service.create_meet_event(
        title=payload.title,
        description=payload.description or f"SUPERNATURAL | {payload.subject}",
        start_time=payload.scheduled_at,
        duration_minutes=payload.duration_minutes,
        attendee_emails=[current_user.email] + student_emails,
        calendar_id=mentor.google_calendar_id or "primary",
    )

    session.meet_link = meet_result["meet_link"]
    session.calendar_event_id = meet_result["event_id"]

    # ── Autonomous: Send Emails ───────────────────────────────────────────
    if student_emails:
        email_service = EmailService()
        email_service.send_meet_link(
            student_emails=student_emails,
            session_title=payload.title,
            meet_link=meet_result["meet_link"],
            scheduled_at=payload.scheduled_at,
            duration_minutes=payload.duration_minutes,
            mentor_name=current_user.full_name,
        )
        session.is_email_sent = True

    db.commit()
    db.refresh(session)

    return {
        "message": "Session created and Meet link sent to all students automatically!",
        "session_id": session.id,
        "meet_link": session.meet_link,
        "students_notified": len(student_emails),
    }


@router.get("/")
def list_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List upcoming sessions for the logged-in user (mentor or student)."""
    from app.models.student import Student
    now = datetime.utcnow()

    if current_user.mentor_profile:
        sessions = (
            db.query(ClassSession)
            .filter(
                ClassSession.mentor_id == current_user.mentor_profile.id,
                ClassSession.scheduled_at >= now,
            )
            .order_by(ClassSession.scheduled_at)
            .all()
        )
    elif current_user.student_profile and current_user.student_profile.assigned_mentor_id:
        sessions = (
            db.query(ClassSession)
            .filter(
                ClassSession.mentor_id == current_user.student_profile.assigned_mentor_id,
                ClassSession.scheduled_at >= now,
            )
            .order_by(ClassSession.scheduled_at)
            .all()
        )
    else:
        return []

    return [
        {
            "id": s.id,
            "title": s.title,
            "subject": s.subject,
            "scheduled_at": s.scheduled_at,
            "duration_minutes": s.duration_minutes,
            "meet_link": s.meet_link,
            "is_quiz_generated": s.is_quiz_generated,
        }
        for s in sessions
    ]


@router.post("/{session_id}/resend-meet")
def resend_meet_link(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually re-send Meet link email to all students (emergency use)."""
    session = db.query(ClassSession).filter(ClassSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.attendees:
        mentor = db.query(Mentor).filter(Mentor.id == session.mentor_id).first()
        EmailService().send_meet_link(
            student_emails=session.attendees,
            session_title=session.title,
            meet_link=session.meet_link,
            scheduled_at=session.scheduled_at,
            duration_minutes=session.duration_minutes,
            mentor_name=mentor.user.full_name if mentor else "Mentor",
        )
    return {"message": "Meet link re-sent successfully", "recipients": session.attendees}
