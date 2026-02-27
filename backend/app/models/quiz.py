"""
SUPERNATURAL - Quiz Models
AI-generated quizzes, questions, and student results
"""

from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, Boolean, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id              = Column(Integer, primary_key=True, index=True)
    session_id      = Column(Integer, ForeignKey("class_sessions.id"))
    title           = Column(String, nullable=False)
    subject         = Column(String, nullable=False)
    topic_covered   = Column(Text, nullable=True)        # What was taught in session
    total_marks     = Column(Integer, default=10)
    time_limit_mins = Column(Integer, default=15)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────────────────
    session     = relationship("ClassSession", back_populates="quizzes")
    questions   = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete")
    results     = relationship("QuizResult",   back_populates="quiz",  cascade="all, delete")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id              = Column(Integer, primary_key=True, index=True)
    quiz_id         = Column(Integer, ForeignKey("quizzes.id"))
    question_text   = Column(Text, nullable=False)
    options         = Column(JSON, default=[])     # ["A) ...", "B) ...", "C) ...", "D) ..."]
    correct_answer  = Column(String, nullable=False)   # "A" / "B" / "C" / "D"
    explanation     = Column(Text, nullable=True)      # AI explanation of correct answer
    marks           = Column(Integer, default=1)

    quiz = relationship("Quiz", back_populates="questions")


class QuizResult(Base):
    __tablename__ = "quiz_results"

    id              = Column(Integer, primary_key=True, index=True)
    quiz_id         = Column(Integer, ForeignKey("quizzes.id"))
    student_id      = Column(Integer, ForeignKey("students.id"))
    answers         = Column(JSON, default={})         # {"q1": "A", "q2": "C", ...}
    score           = Column(Float, default=0.0)
    percentage      = Column(Float, default=0.0)
    ai_feedback     = Column(Text, nullable=True)      # Personalized AI feedback
    is_email_sent   = Column(Boolean, default=False)
    submitted_at    = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ──────────────────────────────────────────────────────
    quiz    = relationship("Quiz",    back_populates="results")
    student = relationship("Student", back_populates="quiz_results")
