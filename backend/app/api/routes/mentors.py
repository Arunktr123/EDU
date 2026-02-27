"""
SUPERNATURAL - Mentor Routes
Preference setup, profile management, student assignments
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models.mentor import Mentor
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.matching_service import MatchingService

router = APIRouter()


class MentorPreferencesUpdate(BaseModel):
    subjects: Optional[List[str]] = None
    expertise_level: Optional[str] = None
    teaching_style: Optional[str] = None
    max_students: Optional[int] = None
    preferred_time: Optional[str] = None
    available_days: Optional[List[str]] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    bio: Optional[str] = None


@router.get("/profile")
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get logged-in mentor's profile."""
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor profile not found")
    return {
        "id": mentor.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "subjects": mentor.subjects,
        "expertise_level": mentor.expertise_level,
        "teaching_style": mentor.teaching_style,
        "max_students": mentor.max_students,
        "preferred_time": mentor.preferred_time,
        "available_days": mentor.available_days,
        "language": mentor.language,
        "timezone": mentor.timezone,
        "bio": mentor.bio,
        "rating": mentor.rating,
        "student_count": len(mentor.students) if mentor.students else 0,
    }


@router.put("/preferences")
def update_preferences(
    payload: MentorPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update mentor teaching preferences. Triggers re-matching for unmatched students."""
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor profile not found")

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(mentor, key, value)

    db.commit()
    db.refresh(mentor)
    return {"message": "Preferences updated successfully", "mentor_id": mentor.id}


@router.get("/students")
def get_my_students(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all students assigned to this mentor."""
    mentor = db.query(Mentor).filter(Mentor.user_id == current_user.id).first()
    if not mentor:
        raise HTTPException(status_code=404, detail="Mentor profile not found")

    return [
        {
            "id": s.id,
            "name": s.user.full_name,
            "email": s.user.email,
            "level": s.current_level,
            "subjects": s.subjects_interested,
            "average_quiz_score": s.average_quiz_score,
            "streak_days": s.streak_days,
        }
        for s in (mentor.students or [])
    ]


@router.post("/trigger-matching")
def trigger_batch_matching(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger autonomous batch matching — matches all unmatched students."""
    service = MatchingService(db)
    result = service.run_batch_matching()
    return result
