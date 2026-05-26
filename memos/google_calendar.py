import json
import os
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.utils import timezone


GOOGLE_AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"


class GoogleCalendarSyncError(Exception):
    pass


def is_google_oauth_configured():
    return bool(settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET)


def build_authorization_url(request):
    flow = _build_flow(request)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    return authorization_url, state


def fetch_credentials_json(request):
    state = request.session.get("google_oauth_state")
    if not state:
        raise ValueError("Google OAuth state is missing.")

    flow = _build_flow(request, state=state)
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    return flow.credentials.to_json()


def create_google_calendar_event(memo, credential):
    if not memo.reminder_at:
        raise GoogleCalendarSyncError("Reminder datetime is required.")

    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.exceptions import RefreshError
    from googleapiclient.errors import HttpError

    credentials = Credentials.from_authorized_user_info(
        json.loads(credential.credentials_json),
        scopes=settings.GOOGLE_CALENDAR_SCOPES,
    )
    service = build("calendar", "v3", credentials=credentials)

    starts_at = timezone.localtime(memo.reminder_at)
    ends_at = starts_at + timedelta(minutes=30)
    event_body = {
        "summary": memo.content,
        "start": {
            "dateTime": starts_at.isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
        "end": {
            "dateTime": ends_at.isoformat(),
            "timeZone": settings.TIME_ZONE,
        },
    }

    try:
        return (
            service.events()
            .insert(calendarId=credential.calendar_id, body=event_body)
            .execute()
        )
    except (HttpError, RefreshError) as exc:
        raise GoogleCalendarSyncError("Failed to create Google Calendar event.") from exc


def _build_flow(request, state=None):
    if not is_google_oauth_configured():
        raise ImproperlyConfigured("Google OAuth client ID and secret are not configured.")

    if settings.DEBUG:
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    from google_auth_oauthlib.flow import Flow

    redirect_uri = request.build_absolute_uri(reverse("google_calendar_callback"))
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
            "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
            "auth_uri": GOOGLE_AUTH_URI,
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": [redirect_uri],
        }
    }
    return Flow.from_client_config(
        client_config,
        scopes=settings.GOOGLE_CALENDAR_SCOPES,
        redirect_uri=redirect_uri,
        state=state,
    )
