"""
SUPERNATURAL - Utility Helpers
"""

from datetime import datetime


def format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    return dt.strftime("%A, %B %d %Y at %I:%M %p UTC")


def get_grade_label(percentage: float) -> str:
    """Convert percentage to grade label."""
    if percentage >= 90: return "A+ — Outstanding! 🌟"
    if percentage >= 80: return "A  — Excellent! 🎉"
    if percentage >= 70: return "B  — Good Job! 👍"
    if percentage >= 60: return "C  — Average 📚"
    if percentage >= 50: return "D  — Below Average 💪"
    return "F  — Needs Improvement 🔄"
