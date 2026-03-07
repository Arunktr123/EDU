"""
SUPERNATURAL - Mentor Model
Stores mentor preferences for autonomous matching
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Time, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Mentor(Base):
    __tablename__ = "mentors"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"), unique=True)

    # ── Preferences for Matching ───────────────────────────────────────────
    subjects        = Column(JSON, default=[])          # ["Python", "ML", "Data Science"]
    expertise_level = Column(String, default="intermediate")  # beginner/intermediate/expert
    teaching_style  = Column(String, default="interactive")   # interactive/lecture/project-based
    max_students    = Column(Integer, default=5)
    preferred_time  = Column(String, default="morning")       # morning/afternoon/evening
    available_days  = Column(JSON, default=[])          # ["Monday", "Wednesday", "Friday"]
    language        = Column(String, default="English")
    timezone        = Column(String, default="UTC")
    bio             = Column(String, nullable=True)
    rating          = Column(Float, default=0.0)

    # ── Google Meet / Calendar ─────────────────────────────────────────────
    google_calendar_id = Column(String, nullable=True)
    meet_auto_create   = Column(Boolean, default=True)

    # ── Relationships ──────────────────────────────────────────────────────
    user        = relationship("User",         back_populates="mentor_profile")
    students    = relationship("Student",      back_populates="assigned_mentor")
    sessions    = relationship("ClassSession", back_populates="mentor")

