"""
SUPERNATURAL - Google Meet Service
Autonomously creates Google Meet links via Google Calendar API
No human intervention required
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings

logger = logging.getLogger(__name__)

# Calendar API scopes
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


class GoogleMeetService:
    """
    Autonomous Google Meet link generator.
    Creates Calendar events with Meet conferencing attached.
    """

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate via OAuth2 and build Calendar service."""
        creds = None
        token_file = settings.GOOGLE_TOKEN_FILE
        creds_file = settings.GOOGLE_CALENDAR_CREDENTIALS_FILE

        # Load saved token
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, SCOPES)

        # Refresh or re-authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(creds_file):
                    logger.warning(
                        "Google credentials file not found. "
                        "Meet links will be mocked in development."
                    )
                    return
                flow = InstalledAppFlow.from_client_secrets_file(creds_file, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token for future runs
            os.makedirs(os.path.dirname(token_file), exist_ok=True)
            with open(token_file, "w") as f:
                f.write(creds.to_json())

        try:
            self.service = build("calendar", "v3", credentials=creds)
            logger.info("✅ Google Calendar service authenticated.")
        except Exception as e:
            logger.error(f"Google Calendar auth failed: {e}")

    def create_meet_event(
        self,
        title: str,
        description: str,
        start_time: datetime,
        duration_minutes: int,
        attendee_emails: list[str],
        calendar_id: str = "primary",
    ) -> dict:
        """
        Create a Google Meet event and return the meet link.
        Falls back to mock link if credentials unavailable.
        """
        if not self.service:
            # Development fallback
            mock_link = f"https://meet.google.com/mock-{title[:8].replace(' ', '-').lower()}"
            logger.warning(f"Using mock Meet link: {mock_link}")
            return {"meet_link": mock_link, "event_id": "mock-event-id"}

        end_time = start_time + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": f"🎓 SUPERNATURAL | {title}",
            "description": description,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC",
            },
            "attendees": [{"email": email} for email in attendee_emails],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"supernatural-{int(start_time.timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email",   "minutes": 60},
                    {"method": "popup",   "minutes": 10},
                ],
            },
        }

        try:
            event = (
                self.service.events()
                .insert(
                    calendarId=calendar_id,
                    body=event_body,
                    conferenceDataVersion=1,
                    sendUpdates="all",    # Auto-sends invites to all attendees
                )
                .execute()
            )

            meet_link = (
                event.get("conferenceData", {})
                .get("entryPoints", [{}])[0]
                .get("uri", "")
            )
            event_id = event.get("id", "")

            logger.info(f"✅ Created Meet event: {meet_link}")
            return {"meet_link": meet_link, "event_id": event_id}

        except Exception as e:
            logger.error(f"Failed to create Meet event: {e}")
            raise

    def delete_event(self, event_id: str, calendar_id: str = "primary"):
        """Cancel/delete a scheduled event."""
        if not self.service:
            return
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            logger.info(f"Deleted event: {event_id}")
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}")
