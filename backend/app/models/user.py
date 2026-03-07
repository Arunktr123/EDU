"""
SUPERNATURAL - User Model
Base user for both Mentors and Students
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class UserRole(str, enum.Enum):
    MENTOR = "mentor"
    STUDENT = "student"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    email         = Column(String, unique=True, index=True, nullable=False)
    full_name     = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role          = Column(SAEnum(UserRole), nullable=False)
    is_active     = Column(Boolean, default=True)
    google_token  = Column(String, nullable=True)   # OAuth token for Google Meet
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    mentor_profile  = relationship("Mentor",  back_populates="user", uselist=False)
    student_profile = relationship("Student", back_populates="user", uselist=False)

