import os
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from events import getRateForShift, buildEventDescription


def getGoogleCreds():
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", config.SCOPES
    )
    creds = flow.run_local_server(port=0)
    return creds


def setupGoogleCalendar():
    if not os.path.exists("credentials.json"):
        raise Exception("No credentials.json file found, please create one and try again.")

    with open("credentials.json", "r") as cred_file:
        if len(cred_file.read()) == 0:
            raise Exception("The credentials.json file is empty, create your own and try again.")

    creds = None
    # Check if token.json exists and load credentials from it
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", config.SCOPES)

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
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def saveToGoogleCalendar(service, convertedSchedule):
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
