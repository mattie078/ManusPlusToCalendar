import json
import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from . import config
from .events import getRateForShift, buildEventDescription


def loadCredentialsSection():
    """Return the client section of credentials.json, or None if it cannot be read."""
    try:
        with open(config.CREDENTIALS_FILE, 'r') as credentialsFile:
            data = json.load(credentialsFile)
    except (ValueError, OSError):
        return None
    return data.get('installed') or data.get('web') or {}


def isGoogleConfigured():
    """credentials.json ships as a blank template, so its presence proves nothing."""
    if not os.path.exists(config.CREDENTIALS_FILE):
        return False

    section = loadCredentialsSection()
    # Unreadable: report configured so setupGoogleCalendar can explain the problem
    if section is None:
        return True

    return bool(str(section.get('client_id') or '').strip())


def getGoogleCreds():
    flow = InstalledAppFlow.from_client_secrets_file(
        config.CREDENTIALS_FILE, config.SCOPES
    )
    creds = flow.run_local_server(port=0)
    return creds


def setupGoogleCalendar():
    if not os.path.exists(config.CREDENTIALS_FILE):
        raise Exception(
            "No %s found. Download it from the Google Cloud Console and save it "
            "here. See README.md step 5." % config.CREDENTIALS_FILE
        )

    section = loadCredentialsSection()
    if section is None:
        raise Exception(
            "%s is empty or not valid JSON. Replace it with an unedited copy of "
            "the file downloaded from the Google Cloud Console." % config.CREDENTIALS_FILE
        )

    if not str(section.get('client_id') or '').strip():
        raise Exception(
            "%s is still the blank template. Replace it with the file downloaded "
            "from the Google Cloud Console, or leave it blank to skip Google "
            "Calendar. See README.md step 5." % config.CREDENTIALS_FILE
        )

    creds = None
    # Check if token.json exists and load credentials from it
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)

    # If no valid credentials, start the login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print('Token has been expired for too long, please reauthenticate.')
                creds = getGoogleCreds()
        else:
            creds = getGoogleCreds()

        # Save the credentials for the next run
        with open(config.TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def saveToGoogleCalendar(service, convertedSchedule):
    if not convertedSchedule:
        print('No shifts to sync to Google Calendar.')
        return

    existingEvents = service.events().list(calendarId='primary', timeMin=convertedSchedule[0][0], timeMax=convertedSchedule[-1][1]).execute()

    for schedule in convertedSchedule:
        currentHourRate = getRateForShift(schedule)

        # Check if the event is already in the calendar from the day before the first event to the day after the last event
        for event in existingEvents['items']:
            # Check if the event has the required fields to compare
            if event.get('status') and event.get('summary') and event.get('start') and event.get('end'):

                if event['status'] == 'cancelled':
                    continue
                if event['summary'] != config.eventSummary:
                    continue

                startDate = str(datetime.fromisoformat(schedule[0]).date())
                endDate = str(datetime.fromisoformat(schedule[1]).date())

                if event['start'].get('dateTime') and event['end'].get('dateTime'):
                    eventStartDate = str(datetime.fromisoformat(event['start']['dateTime']).date())
                    eventEndDate = str(datetime.fromisoformat(event['end']['dateTime']).date())
                elif event['start'].get('date') and event['end'].get('date'):
                    eventStartDate = event['start']['date']
                    eventEndDate = event['end']['date']
                else:
                    print('Event has no start or end date, skipping: %s' % (event.get('htmlLink')))
                    break

                if eventStartDate == startDate and eventEndDate == endDate:
                    eventStartTime = datetime.fromisoformat(event['start']['dateTime']).time() if event['start'].get('dateTime') else None
                    eventEndTime = datetime.fromisoformat(event['end']['dateTime']).time() if event['end'].get('dateTime') else None
                    scheduleStartTime = datetime.fromisoformat(schedule[0]).time()
                    scheduleEndTime = datetime.fromisoformat(schedule[1]).time()

                    conflicts = schedule[3] if len(schedule) > 3 else []
                    expectedDescription = buildEventDescription(currentHourRate, schedule[2], conflicts)
                    expectedColorId = '5' if conflicts else '10'

                    if eventStartTime == scheduleStartTime and eventEndTime == scheduleEndTime:
                        if event.get('description') == expectedDescription and event.get('colorId') == expectedColorId:
                            print('Event already exists, skipping: %s' % (event.get('htmlLink')))
                        else:
                            print('Event description or color changed, updating: %s' % (event.get('htmlLink')))
                            event['description'] = expectedDescription
                            event['colorId'] = expectedColorId
                            service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
                        break
                    else:
                        print('Event has different start or end time, updating: %s' % (event.get('htmlLink')))
                        event['start']['dateTime'] = schedule[0]
                        event['end']['dateTime'] = schedule[1]
                        event['description'] = expectedDescription
                        event['colorId'] = expectedColorId
                        service.events().update(calendarId='primary', eventId=event['id'], body=event).execute()
                        break
        else:
            conflicts = schedule[3] if len(schedule) > 3 else []
            description = buildEventDescription(currentHourRate, schedule[2], conflicts)

            event = {
                'summary': config.eventSummary,
                'start': {
                    'dateTime': schedule[0],
                    'timeZone': config.eventTimezone,
                },
                'end': {
                    'dateTime': schedule[1],
                    'timeZone': config.eventTimezone,
                },
                'colorId': '5' if conflicts else '10',
                'description': description,
                'location': config.eventLocation,
            }

            # Insert the event
            event = service.events().insert(calendarId='primary', body=event).execute()
            print('Event created: %s' % (event.get('htmlLink')))
