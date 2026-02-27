"""
SUPERNATURAL - Quiz Routes
AI quiz generation, student submission, result retrieval
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict

from app.database import get_db
from app.models.quiz import Quiz, QuizQuestion, QuizResult
from app.models.session import ClassSession
from app.models.student import Student
from app.models.user import User
from app.api.routes.auth import get_current_user
from app.services.quiz_service import QuizService

router = APIRouter()


class GenerateQuizRequest(BaseModel):
    session_id: int
    topic: str  # Topics covered in today's class


class SubmitQuizRequest(BaseModel):
    quiz_id: int
    answers: Dict[str, str]  # {"1": "A", "2": "C", ...} — key = question_id


@router.post("/generate", status_code=201)
def generate_quiz(
    payload: GenerateQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Mentor triggers AI quiz generation after a class session.
    AI automatically creates relevant MCQs based on topic.
    """
    service = QuizService(db)
    quiz = service.generate_quiz_for_session(
        session_id=payload.session_id,
        topic=payload.topic,
    )
    return {
        "message": f"Quiz generated with {len(quiz.questions)} questions",
        "quiz_id": quiz.id,
        "title": quiz.title,
        "total_marks": quiz.total_marks,
        "time_limit_mins": quiz.time_limit_mins,
    }


@router.get("/{quiz_id}")
def get_quiz(
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch quiz questions for a student to answer."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.is_active == True).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found or inactive")

    return {
        "id": quiz.id,
        "title": quiz.title,
        "subject": quiz.subject,
        "time_limit_mins": quiz.time_limit_mins,
        "total_marks": quiz.total_marks,
        "questions": [
            {
                "id": q.id,
                "question": q.question_text,
                "options": q.options,
                "marks": q.marks,
                # NOTE: correct_answer NOT exposed to student
            }
            for q in quiz.questions
        ],
    }


@router.post("/submit")
def submit_quiz(
    payload: SubmitQuizRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Student submits quiz answers.
    Platform autonomously:
      1. Evaluates answers
      2. Generates AI feedback
      3. Emails result to student
    """
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=403, detail="Only students can submit quizzes")

    # Check duplicate submission
    existing = db.query(QuizResult).filter(
        QuizResult.quiz_id == payload.quiz_id,
        QuizResult.student_id == student.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already submitted this quiz")

    service = QuizService(db)
    result = service.evaluate_submission(
        quiz_id=payload.quiz_id,
        student_id=student.id,
        answers=payload.answers,
    )

    return {
        "message": "Quiz submitted! Results emailed to you automatically.",
        "score": result.score,
        "percentage": round(result.percentage, 1),
        "ai_feedback": result.ai_feedback,
        "email_sent": result.is_email_sent,
    }


@router.get("/results/me")
def my_quiz_results(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Student views all their quiz results."""
    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=403, detail="Students only")

    results = (
        db.query(QuizResult)
        .filter(QuizResult.student_id == student.id)
        .order_by(QuizResult.submitted_at.desc())
        .all()
    )
    return [
        {
            "quiz_title": r.quiz.title,
            "subject": r.quiz.subject,
            "score": r.score,
            "percentage": round(r.percentage, 1),
            "ai_feedback": r.ai_feedback,
            "submitted_at": r.submitted_at,
        }
        for r in results
    ]
