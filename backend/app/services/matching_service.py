"""
SUPERNATURAL - Matching Service
Autonomous Mentor-Student matching based on mutual preferences
Uses a scoring algorithm to find the best match
"""

from sqlalchemy.orm import Session
from app.models.mentor import Mentor
from app.models.student import Student
from app.services.email_service import EmailService
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class MatchingService:
    """
    Autonomous matching engine.
    Scores every available mentor against a student's preferences
    and assigns the best-fit mentor.
    """

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()

    def calculate_match_score(self, mentor: Mentor, student: Student) -> float:
        """
        Score a mentor-student pair from 0 to 100.
        Higher = better match.
        """
        score = 0.0

        # ── Subject Match (40 pts) ────────────────────────────────────────
        mentor_subjects  = set(s.lower() for s in (mentor.subjects or []))
        student_subjects = set(s.lower() for s in (student.subjects_interested or []))
        if mentor_subjects and student_subjects:
            overlap = mentor_subjects & student_subjects
            score += (len(overlap) / max(len(student_subjects), 1)) * 40

        # ── Level Compatibility (20 pts) ─────────────────────────────────
        level_map = {"beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        mentor_level  = level_map.get(mentor.expertise_level, 2)
        student_level = level_map.get(student.current_level, 1)
        if mentor_level >= student_level:
            score += 20
        elif mentor_level == student_level - 1:
            score += 10  # Partial credit

        # ── Teaching/Learning Style Match (20 pts) ────────────────────────
        if mentor.teaching_style == student.learning_style:
            score += 20

        # ── Time Preference Match (10 pts) ────────────────────────────────
        if mentor.preferred_time == student.preferred_time:
            score += 10

        # ── Available Days Overlap (10 pts) ──────────────────────────────
        mentor_days  = set(d.lower() for d in (mentor.available_days or []))
        student_days = set(d.lower() for d in (student.available_days or []))
        if mentor_days and student_days:
            day_overlap = mentor_days & student_days
            score += (len(day_overlap) / max(len(student_days), 1)) * 10

        return round(score, 2)

    def find_best_mentor(self, student: Student) -> Optional[Mentor]:
        """Find the best available mentor for a student."""
        # Get all mentors who still have capacity
        available_mentors = (
            self.db.query(Mentor)
            .filter(Mentor.meet_auto_create == True)
            .all()
        )

        if not available_mentors:
            logger.warning("No available mentors found for matching.")
            return None

        # Filter mentors who haven't hit max_students yet
        def has_capacity(mentor: Mentor) -> bool:
            current_count = len(mentor.students) if mentor.students else 0
            return current_count < (mentor.max_students or 5)

        available_mentors = [m for m in available_mentors if has_capacity(m)]

        if not available_mentors:
            logger.warning("All mentors are at full capacity.")
            return None

        # Score all mentors
        scored = [
            (mentor, self.calculate_match_score(mentor, student))
            for mentor in available_mentors
        ]
        scored.sort(key=lambda x: x[1], reverse=True)

        best_mentor, best_score = scored[0]
        logger.info(
            f"Best mentor for student {student.id}: Mentor {best_mentor.id} "
            f"with score {best_score}"
        )
        return best_mentor

    def assign_mentor(self, student_id: int) -> dict:
        """
        Fully autonomous: find best mentor and assign to student.
        Triggers email notification to both mentor and student.
        """
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValueError(f"Student {student_id} not found")

        if student.is_matched:
            return {"status": "already_matched", "mentor_id": student.assigned_mentor_id}

        mentor = self.find_best_mentor(student)
        if not mentor:
            return {"status": "no_mentor_available"}

        # Assign mentor
        student.assigned_mentor_id = mentor.id
        student.is_matched = True
        self.db.commit()
        self.db.refresh(student)

        # Notify both parties via email
        self.email_service.send_matching_confirmation(student, mentor)

        logger.info(f"✅ Matched Student {student_id} with Mentor {mentor.id}")
        return {
            "status": "matched",
            "student_id": student_id,
            "mentor_id": mentor.id,
            "match_score": self.calculate_match_score(mentor, student),
        }

    def run_batch_matching(self) -> dict:
        """Autonomously match ALL unmatched students to available mentors."""
        unmatched = self.db.query(Student).filter(Student.is_matched == False).all()
        results = []
        for student in unmatched:
            result = self.assign_mentor(student.id)
            results.append(result)
        return {"total_processed": len(results), "results": results}

