import os.path
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from src.core.config import config
from src.core.logger import logger

SCOPES = ['https://www.googleapis.com/auth/calendar']

class CalendarClient:
    def __init__(self):
        self.creds = self._authenticate()

    def _authenticate(self):
        creds = None
        token_path = 'token.json'
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GOOGLE_APPLICATION_CREDENTIALS, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        return creds

    def create_event(self, job_title: str, company: str):
        try:
            service = build('calendar', 'v3', credentials=self.creds)
            
            # Set deadline for tomorrow
            start_time = (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
            end_time = (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z'
            
            event = {
                'summary': f'Apply to {job_title} at {company}',
                'description': 'Automated reminder from Sentinel-Apply',
                'start': {'dateTime': start_time, 'timeZone': 'UTC'},
                'end': {'dateTime': end_time, 'timeZone': 'UTC'},
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},
                        {'method': 'popup', 'minutes': 60},
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'popup', 'minutes': 10},
                    ],
                },
            }
            
            event = service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f"Calendar event created: {event.get('htmlLink')}")
        except Exception as e:
            logger.error(f"Failed to create calendar event: {e}")
