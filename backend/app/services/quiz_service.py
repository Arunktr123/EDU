"""
SUPERNATURAL - Quiz Service
Orchestrates AI quiz generation, evaluation, and result delivery
Fully autonomous: no human intervention required
"""

import logging
from sqlalchemy.orm import Session
from app.models.quiz import Quiz, QuizQuestion, QuizResult
from app.models.session import ClassSession
from app.models.student import Student
from app.services.llm_service import LLMService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


class QuizService:
    """Autonomous quiz lifecycle manager."""

    def __init__(self, db: Session):
        self.db           = db
        self.llm_service  = LLMService()
        self.email_service = EmailService()

    # ── STEP 1: Generate Quiz for a Session ──────────────────────────────────
    def generate_quiz_for_session(self, session_id: int, topic: str) -> Quiz:
        """
        After a class session ends, autonomously generate a quiz using AI.
        """
        session: ClassSession = (
            self.db.query(ClassSession).filter(ClassSession.id == session_id).first()
        )
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Determine difficulty from mentor's student level
        difficulty = "intermediate"
        if session.mentor and session.mentor.students:
            levels = [s.current_level for s in session.mentor.students]
            if "beginner" in levels:
                difficulty = "beginner"
            elif "advanced" in levels:
                difficulty = "advanced"

        # AI-generate questions
        raw_questions = self.llm_service.generate_quiz(
            subject=session.subject,
            topic=topic,
            difficulty=difficulty,
            num_questions=5,
        )

        # Persist Quiz
        quiz = Quiz(
            session_id=session_id,
            title=f"Quiz: {topic}",
            subject=session.subject,
            topic_covered=topic,
            total_marks=len(raw_questions),
            time_limit_mins=15,
        )
        self.db.add(quiz)
        self.db.flush()  # get quiz.id

        # Persist Questions
        for q in raw_questions:
            question = QuizQuestion(
                quiz_id=quiz.id,
                question_text=q.get("question", ""),
                options=q.get("options", []),
                correct_answer=q.get("correct_answer", "A"),
                explanation=q.get("explanation", ""),
                marks=q.get("marks", 1),
            )
            self.db.add(question)

        # Mark session as quiz generated
        session.is_quiz_generated = True
        self.db.commit()
        self.db.refresh(quiz)

        logger.info(f"✅ Quiz {quiz.id} generated for session {session_id}")
        return quiz

    # ── STEP 2: Evaluate a Student's Submission ──────────────────────────────
    def evaluate_submission(
        self, quiz_id: int, student_id: int, answers: dict[str, str]
    ) -> QuizResult:
        """
        Evaluate submitted answers, compute score, generate AI feedback.
        Autonomously sends result email to student.
        """
        quiz: Quiz = self.db.query(Quiz).filter(Quiz.id == quiz_id).first()
        if not quiz:
            raise ValueError(f"Quiz {quiz_id} not found")

        student: Student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError(f"Student {student_id} not found")

        # Score calculation
        total_marks = 0
        earned_marks = 0.0
        wrong_topics: list[str] = []

        for question in quiz.questions:
            q_key = str(question.id)
            total_marks += question.marks
            student_answer = answers.get(q_key, "").strip().upper()
            correct = question.correct_answer.strip().upper()
            if student_answer == correct:
                earned_marks += question.marks
            else:
                wrong_topics.append(question.question_text[:60])

        percentage = (earned_marks / max(total_marks, 1)) * 100

        # AI Feedback
        ai_feedback = self.llm_service.generate_feedback(
            student_name=student.user.full_name,
            subject=quiz.subject,
            quiz_title=quiz.title,
            score=earned_marks,
            percentage=percentage,
            wrong_questions=wrong_topics,
        )

        # Save result
        result = QuizResult(
            quiz_id=quiz_id,
            student_id=student_id,
            answers=answers,
            score=earned_marks,
            percentage=percentage,
            ai_feedback=ai_feedback,
        )
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)

        # Update student average
        all_results = self.db.query(QuizResult).filter(
            QuizResult.student_id == student_id
        ).all()
        student.average_quiz_score = sum(r.percentage for r in all_results) / len(all_results)
        self.db.commit()

        # Autonomous email delivery
        self.email_service.send_quiz_result(
            student_email=student.user.email,
            student_name=student.user.full_name,
            quiz_title=quiz.title,
            score=earned_marks,
            total=total_marks,
            percentage=percentage,
            ai_feedback=ai_feedback,
        )
        result.is_email_sent = True
        self.db.commit()

        logger.info(
            f"✅ Quiz result for student {student_id}: {percentage:.1f}% — email sent"
        )
        return result
