from datetime import datetime
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from flask import url_for

SCOPES = ['https://www.googleapis.com/auth/calendar']

def create_calendar_service(credentials_dict):
    """Create a Google Calendar service instance from credentials."""
    credentials = Credentials.from_authorized_user_info(credentials_dict, SCOPES)
    return build('calendar', 'v3', credentials=credentials)

def get_oauth_flow():
    """Create OAuth flow instance for Google Calendar."""
    client_config = {
        "web": {
            "client_id": os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
            "client_secret": os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=url_for('google_calendar_callback', _external=True)
    )

def create_calendar_event(service, appointment):
    """Create a calendar event for an appointment."""
    event = {
        'summary': f'Medical Appointment - {appointment.patient.name}',
        'location': 'Hospital',
        'description': f'Medical appointment with Dr. {appointment.doctor.name}',
        'start': {
            'dateTime': appointment.start_time.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': appointment.end_time.isoformat(),
            'timeZone': 'UTC',
        },
        'attendees': [
            {'email': appointment.patient.email},
            {'email': appointment.doctor.email}
        ],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 30},
            ],
        },
    }
    
    return service.events().insert(calendarId='primary', body=event).execute()

def update_calendar_event(service, event_id, appointment):
    """Update an existing calendar event."""
    event = {
        'summary': f'Medical Appointment - {appointment.patient.name}',
        'location': 'Hospital',
        'description': f'Medical appointment with Dr. {appointment.doctor.name}',
        'start': {
            'dateTime': appointment.start_time.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': appointment.end_time.isoformat(),
            'timeZone': 'UTC',
        },
        'attendees': [
            {'email': appointment.patient.email},
            {'email': appointment.doctor.email}
        ],
    }
    
    return service.events().update(
        calendarId='primary',
        eventId=event_id,
        body=event
    ).execute()

def delete_calendar_event(service, event_id):
    """Delete a calendar event."""
    service.events().delete(calendarId='primary', eventId=event_id).execute()

def get_calendar_events(service, time_min=None, time_max=None):
    """Get calendar events within a time range."""
    if not time_min:
        time_min = datetime.utcnow().isoformat() + 'Z'
    
    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max.isoformat() + 'Z' if time_max else None,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    
    return events_result.get('items', [])
