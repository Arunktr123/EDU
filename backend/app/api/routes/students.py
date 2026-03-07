"""
SUPERNATURAL - Student Routes
Preference submission, profile, progress tracking
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models.student import Student
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.matching_service import MatchingService

router = APIRouter()


class StudentPreferencesUpdate(BaseModel):
    subjects_interested: Optional[List[str]] = None
    current_level: Optional[str] = None
    learning_style: Optional[str] = None
    preferred_time: Optional[str] = None
    available_days: Optional[List[str]] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    learning_goals: Optional[str] = None


@router.get("/profile")
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get logged-in student's profile and progress."""
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    mentor_info = None
    if student.assigned_mentor:
        mentor_info = {
            "id": student.assigned_mentor.id,
            "name": student.assigned_mentor.user.full_name,
            "email": student.assigned_mentor.user.email,
            "subjects": student.assigned_mentor.subjects,
        }

    return {
        "id": student.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "subjects_interested": student.subjects_interested,
        "current_level": student.current_level,
        "learning_style": student.learning_style,
        "preferred_time": student.preferred_time,
        "available_days": student.available_days,
        "learning_goals": student.learning_goals,
        "is_matched": student.is_matched,
        "assigned_mentor": mentor_info,
        "progress": {
            "total_classes_attended": student.total_classes_attended,
            "average_quiz_score": round(student.average_quiz_score, 1),
            "streak_days": student.streak_days,
        },
    }


@router.put("/preferences")
def update_preferences(
    payload: StudentPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit or update learning preferences.
    Automatically triggers mentor matching if not yet matched.
    """
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(student, key, value)
    db.commit()

    # Auto-trigger matching if not yet matched
    if not student.is_matched:
        service = MatchingService(db)
        match_result = service.assign_mentor(student.id)
        return {"message": "Preferences saved", "matching_result": match_result}

    return {"message": "Preferences updated successfully"}


@router.get("/quiz-history")
def get_quiz_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get student's full quiz history with scores."""
    from app.models.quiz import QuizResult
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    results = (
        db.query(QuizResult)
        .filter(QuizResult.student_id == student.id)
        .order_by(QuizResult.submitted_at.desc())
        .all()
    )

    return [
        {
            "quiz_id": r.quiz_id,
            "quiz_title": r.quiz.title,
            "subject": r.quiz.subject,
            "score": r.score,
            "percentage": round(r.percentage, 1),
            "ai_feedback": r.ai_feedback,
            "submitted_at": r.submitted_at,
        }
        for r in results
    ]

