"""
SUPERNATURAL - LLM Service
OpenAI-powered quiz generation and personalized feedback
"""

import json
import logging
from openai import OpenAI
from app.config import settings

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)


class LLMService:
    """Handles all AI/LLM operations autonomously."""

    def generate_quiz(
        self,
        subject: str,
        topic: str,
        difficulty: str = "intermediate",
        num_questions: int = 5,
    ) -> list[dict]:
        """
        Generate MCQ quiz questions for a given topic using GPT.
        Returns structured list of questions.
        """
        prompt = f"""
        You are an expert educator. Generate exactly {num_questions} multiple-choice 
        questions for a class on the following topic.

        Subject: {subject}
        Topic Covered Today: {topic}
        Difficulty: {difficulty}

        Return a JSON array only (no extra text) in this exact format:
        [
            {{
                "question": "Question text here?",
                "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                "correct_answer": "A",
                "explanation": "Brief explanation of why A is correct.",
                "marks": 1
            }}
        ]
        """

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are an expert quiz generator. Always return valid JSON only."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            # Handle both list and {"questions": [...]} formats
            if isinstance(data, list):
                questions = data
            else:
                questions = data.get("questions", data.get("quiz", []))

            logger.info(f"✅ Generated {len(questions)} quiz questions for '{topic}'")
            return questions

        except Exception as e:
            logger.error(f"Quiz generation failed: {e}")
            return self._fallback_questions(subject, topic, num_questions)

    def generate_feedback(
        self,
        student_name: str,
        subject: str,
        quiz_title: str,
        score: float,
        percentage: float,
        wrong_questions: list[str],
    ) -> str:
        """
        Generate personalized AI feedback for a student's quiz performance.
        """
        context = (
            f"Student: {student_name}\n"
            f"Subject: {subject}\n"
            f"Quiz: {quiz_title}\n"
            f"Score: {score:.1f}% ({percentage:.1f}%)\n"
        )
        if wrong_questions:
            context += f"Topics to improve: {', '.join(wrong_questions[:3])}"

        prompt = f"""
        You are a supportive AI tutor. Based on the student's quiz performance below,
        give warm, encouraging, and constructive feedback in 3-4 sentences.
        Highlight what they did well, what to improve, and one specific action tip.

        {context}
        """

        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are a supportive AI tutor."},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.8,
                max_tokens=200,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            if percentage >= 70:
                return f"Great work, {student_name}! You scored {percentage:.1f}%. Keep up the momentum!"
            else:
                return (
                    f"Good effort, {student_name}! You scored {percentage:.1f}%. "
                    "Review the topics covered in today's class and try again. You've got this!"
                )

    def _fallback_questions(self, subject: str, topic: str, num: int) -> list[dict]:
        """Fallback static questions if OpenAI is unavailable."""
        return [
            {
                "question": f"Which of the following best describes {topic}?",
                "options": [
                    "A) A fundamental concept in the field",
                    "B) An unrelated topic",
                    "C) A deprecated method",
                    "D) None of the above",
                ],
                "correct_answer": "A",
                "explanation": f"{topic} is a core concept in {subject}.",
                "marks": 1,
            }
        ] * min(num, 3)
