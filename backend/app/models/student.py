"""
SUPERNATURAL - Student Model
Stores student preferences for autonomous matching & progress tracking
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from app.database import Base


class Student(Base):
    __tablename__ = "students"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), unique=True)
    assigned_mentor_id = Column(Integer, ForeignKey("mentors.id"), nullable=True)

    # ── Preferences for Matching ───────────────────────────────────────────
    subjects_interested = Column(JSON, default=[])     # ["Python", "ML"]
    current_level       = Column(String, default="beginner")  # beginner/intermediate/advanced
    learning_style      = Column(String, default="interactive")
    preferred_time      = Column(String, default="morning")
    available_days      = Column(JSON, default=[])
    language            = Column(String, default="English")
    timezone            = Column(String, default="UTC")
    learning_goals      = Column(Text, nullable=True)  # Free text: "I want to become ML engineer"

    # ── Progress Tracking ─────────────────────────────────────────────────
    total_classes_attended = Column(Integer, default=0)
    average_quiz_score     = Column(Float, default=0.0)
    streak_days            = Column(Integer, default=0)
    is_matched             = Column(Boolean, default=False)

    # ── Relationships ──────────────────────────────────────────────────────
    user             = relationship("User",    back_populates="student_profile")
    assigned_mentor  = relationship("Mentor",  back_populates="students")
    quiz_results     = relationship("QuizResult", back_populates="student")

