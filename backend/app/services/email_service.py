"""
SUPERNATURAL - Email Service
Autonomous email delivery for:
  1. Mentor-Student Matching Confirmation
  2. Daily Google Meet Links
  3. Quiz Results + AI Feedback
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Sends all platform emails autonomously via SMTP."""

    def _send(self, to_emails: list[str], subject: str, html_body: str):
        """Core SMTP send method with error handling."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            msg["To"]      = ", ".join(to_emails)
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, to_emails, msg.as_string())

            logger.info(f"✅ Email sent to {to_emails}: {subject}")

        except Exception as e:
            logger.error(f"❌ Email send failed to {to_emails}: {e}")
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # 1. MATCHING CONFIRMATION
    # ─────────────────────────────────────────────────────────────────────────
    def send_matching_confirmation(self, student, mentor):
        """Notify student and mentor about their match."""
        student_email = student.user.email
        mentor_email  = mentor.user.email

        # Email to Student
        student_html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f6ff;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border-radius:12px;padding:30px;">
            <h1 style="color:#6c63ff;">🎓 Welcome to SUPERNATURAL!</h1>
            <p>Hi <strong>{student.user.full_name}</strong>,</p>
            <p>Great news! You've been matched with your mentor:</p>
            <div style="background:#f0edff;padding:15px;border-radius:8px;margin:20px 0;">
                <h2 style="color:#6c63ff;margin:0;">{mentor.user.full_name}</h2>
                <p style="color:#666;">📚 Subjects: {', '.join(mentor.subjects or [])}</p>
                <p style="color:#666;">🎯 Teaching Style: {mentor.teaching_style}</p>
                <p style="color:#666;">⭐ Rating: {mentor.rating}/5.0</p>
                <p style="color:#666;">📧 {mentor_email}</p>
            </div>
            <p>Your learning journey starts now! You'll receive class schedules and 
            Google Meet links automatically.</p>
            <p style="color:#999;font-size:12px;">– SUPERNATURAL Platform (Autonomous)</p>
        </div></body></html>
        """

        # Email to Mentor
        mentor_html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f6ff;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border-radius:12px;padding:30px;">
            <h1 style="color:#6c63ff;">🎓 New Student Assigned!</h1>
            <p>Hi <strong>{mentor.user.full_name}</strong>,</p>
            <p>A new student has been matched with you:</p>
            <div style="background:#f0edff;padding:15px;border-radius:8px;margin:20px 0;">
                <h2 style="color:#6c63ff;margin:0;">{student.user.full_name}</h2>
                <p style="color:#666;">📚 Interested In: {', '.join(student.subjects_interested or [])}</p>
                <p style="color:#666;">🎯 Level: {student.current_level}</p>
                <p style="color:#666;">🎯 Learning Style: {student.learning_style}</p>
                <p style="color:#666;">📧 {student_email}</p>
            </div>
            <p>Google Meet links will be sent automatically based on your schedule.</p>
            <p style="color:#999;font-size:12px;">– SUPERNATURAL Platform (Autonomous)</p>
        </div></body></html>
        """

        self._send([student_email], "🎓 You've been matched with a mentor! | SUPERNATURAL", student_html)
        self._send([mentor_email], "🎓 New student assigned to you | SUPERNATURAL", mentor_html)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. DAILY MEET LINK
    # ─────────────────────────────────────────────────────────────────────────
    def send_meet_link(
        self,
        student_emails: list[str],
        session_title: str,
        meet_link: str,
        scheduled_at: datetime,
        duration_minutes: int,
        mentor_name: str,
    ):
        """Send daily Google Meet session link to all enrolled students."""
        formatted_time = scheduled_at.strftime("%A, %B %d %Y at %I:%M %p UTC")

        html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f6ff;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border-radius:12px;padding:30px;">
            <h1 style="color:#6c63ff;">📅 Today's Class is Ready!</h1>
            <p>Your daily class has been scheduled:</p>

            <div style="background:#f0edff;padding:20px;border-radius:8px;margin:20px 0;">
                <h2 style="color:#6c63ff;margin:0;">📚 {session_title}</h2>
                <p style="color:#666;">👨‍🏫 Mentor: <strong>{mentor_name}</strong></p>
                <p style="color:#666;">📅 Time: <strong>{formatted_time}</strong></p>
                <p style="color:#666;">⏱ Duration: <strong>{duration_minutes} minutes</strong></p>
            </div>

            <div style="text-align:center;margin:30px 0;">
                <a href="{meet_link}"
                   style="background:#6c63ff;color:white;padding:15px 30px;
                          border-radius:8px;text-decoration:none;font-size:16px;
                          font-weight:bold;">
                    🎥 Join Google Meet
                </a>
            </div>

            <p style="color:#666;font-size:13px;">
                ⚠️ A quiz will be automatically sent after the class based on topics covered.
            </p>
            <p style="color:#999;font-size:12px;">– SUPERNATURAL Platform (Autonomous)</p>
        </div></body></html>
        """
        self._send(
            student_emails,
            f"📅 Class Today: {session_title} | SUPERNATURAL",
            html,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. QUIZ RESULT + AI FEEDBACK
    # ─────────────────────────────────────────────────────────────────────────
    def send_quiz_result(
        self,
        student_email: str,
        student_name: str,
        quiz_title: str,
        score: float,
        total: int,
        percentage: float,
        ai_feedback: str,
    ):
        """Send quiz score and personalized AI feedback to student."""
        grade_color = "#28a745" if percentage >= 70 else "#dc3545" if percentage < 50 else "#ffc107"
        grade_label = "Excellent! 🌟" if percentage >= 80 else "Good Job! 👍" if percentage >= 60 else "Keep Practicing 💪"

        html = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f6ff;padding:20px;">
        <div style="max-width:600px;margin:auto;background:white;border-radius:12px;padding:30px;">
            <h1 style="color:#6c63ff;">📊 Your Quiz Results</h1>
            <p>Hi <strong>{student_name}</strong>, here are your results for:</p>
            <h2 style="color:#6c63ff;">{quiz_title}</h2>

            <div style="text-align:center;padding:30px;background:#f0edff;border-radius:12px;margin:20px 0;">
                <div style="font-size:60px;font-weight:bold;color:{grade_color};">
                    {percentage:.1f}%
                </div>
                <div style="font-size:24px;color:#333;">{score}/{total} marks</div>
                <div style="font-size:18px;color:{grade_color};margin-top:10px;">{grade_label}</div>
            </div>

            <div style="background:#fff8e1;padding:20px;border-radius:8px;margin:20px 0;
                        border-left:4px solid #ffc107;">
                <h3 style="color:#f57c00;margin:0 0 10px;">🤖 AI Feedback for You</h3>
                <p style="color:#555;line-height:1.7;">{ai_feedback}</p>
            </div>

            <p style="color:#999;font-size:12px;">– SUPERNATURAL Platform (Autonomous AI)</p>
        </div></body></html>
        """
        self._send(
            [student_email],
            f"📊 Quiz Results: {quiz_title} | SUPERNATURAL",
            html,
        )

