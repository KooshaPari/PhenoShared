import datetime
import google.auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class GoogleCalendarAPI:
    def __init__(self, credentials_file):
        self.credentials = google.auth.load_credentials_from_file(
            credentials_file, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        self.service = build("calendar", "v3", credentials=self.credentials)

    def get_event(self, event_id):
        try:
            event = (
                self.service.events()
                .get(calendarId="primary", eventId=event_id)
                .execute()
            )
            return event
        except HttpError as e:
            print(f"Error getting event: {e}")
            return None

    def get_events(self, event_ids):
        events = []
        for event_id in event_ids:
            event = self.get_event(event_id)
            if event:
                events.append(event)
        return events

    def get_events_by_date_range(self, start_date, end_date):
        events_result = (
            self.service.events()
            .list(
                calendarId="primary",
                timeMin=start_date.isoformat() + "Z",
                timeMax=end_date.isoformat() + "Z",
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return events_result.get("items", [])

    def create_event(self, event_data):
        return (
            self.service.events()
            .insert(calendarId="primary", body=event_data)
            .execute()
        )

    def update_event(self, event_id, event_data):
        try:
            return (
                self.service.events()
                .update(calendarId="primary", eventId=event_id, body=event_data)
                .execute()
            )
        except HttpError as e:
            print(f"Error updating event: {e}")
            return None

    def delete_event(self, event_id):
        try:
            self.service.events().delete(
                calendarId="primary", eventId=event_id
            ).execute()
            return True
        except HttpError as e:
            print(f"Error deleting event: {e}")
            return False

    def delete_events(self, event_ids):
        for event_id in event_ids:
            self.delete_event(event_id)
