from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import requests
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]
EXTRA_SUNDAY_PERCENTAGE = 0.5
AVAILABILITY_CONFLICT_FIELDS = ['unavailability', 'illness', 'vacation', 'holiday']

def getGoogleCreds():
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES
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
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
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

def getBearerToken():
    data = {
        'client_id': 'employee',
        'grant_type': 'password',
        'username': os.getenv('manus_username'),
        'password': os.getenv('manus_password'),
    }
    
    response = requests.post('https://server.manus.plus/' + os.getenv('company_name') + '/app/token', data=data)
   
    if response.status_code == 200:
        # Assuming the response contains a JSON object with the token
        token_data = response.json()
        return token_data['access_token']
    else:
        # Handle errors
        raise Exception(f"Failed to get token: {response.status_code}, {response.text}")

def getUserInformation(token):
    headers = {
        'authorization': 'Bearer '+token,
    }
    response = requests.get('https://server.manus.plus/' + os.getenv('company_name') + '/api/user/me', headers=headers)
    information_data = response.json()
    
    global nodeId, employeeId
    
    nodeId = information_data['nodeId']
    employeeId = information_data['employeeId']

def getAvailabilityConflicts(workDay, entry):
    """Return list of (field, period) tuples where the entry overlaps an absence period."""
    conflicts = []
    for field in AVAILABILITY_CONFLICT_FIELDS:
        for period in workDay.get(field, []):
            # Overlap when entry starts before period ends AND entry ends after period starts
            if entry['startTime'] < period['endTime'] and entry['endTime'] > period['startTime']:
                conflicts.append((field, period))
    return conflicts

def getWorkweeks(token, week_amount):
    schedule = []

    headers = {
        'authorization': 'Bearer ' + token,
    }

    global hourRate
    hourRate = 0

    for i in range(week_amount):
        adjusted_date = datetime.now() + timedelta(weeks=i)
        year, week, _ = adjusted_date.isocalendar()

        response = requests.get(
            f'https://server.manus.plus/{os.getenv("company_name")}/api/node/{nodeId}/employee/{employeeId}/schedule/{year}/{week}/fromData',
            headers=headers,
        )
        weekData = response.json()

        if weekData.get('message'):
            print(f"Failed to get schedule for week {week}: {weekData['message']}")
            continue
        if not weekData.get('contracts'):
            print(f"No contracts found for week {week}")
            continue
        if not weekData.get('schedule'):
            print(f"No schedule found for week {week}")
            continue

        weekContract = weekData['contracts'][0]
        if hourRate == 0 and weekContract.get('hourRate'):
            hourRate = weekContract['hourRate']
        weekSchedule = weekData['schedule']
        for workDay in weekSchedule:
            if workDay.get('entries'):
                for entry in workDay['entries']:
                    conflicts = getAvailabilityConflicts(workDay, entry)
                    schedule.append([entry['fromDate'], entry['startTime'], entry['endTime'], entry['totalTime'], conflicts])
    return schedule

def convertSchedule(schedule):
    convertedSchedule = []

    # ManusPlus start date
    start_date = datetime(1900, 1, 1)

    # Convert Timezone so it can be used in the datetime object
    convertedTimezone = pytz.timezone(eventTimezone)

    for entry in schedule:
        converted_date = start_date + timedelta(days=entry[0])        
        
        workTimes = []
        for i in range(1, 4):
            hours = entry[i] // 60
            minutes = entry[i] % 60
            
            # Convert total time to hours and minutes
            if i == 3:
                workTimes.append(hours + (minutes / 60))
                continue
            
            # Convert the date and time to a string
            dateStr = converted_date.strftime("%d-%m-%Y")
            timeStr = f"{hours:02d}:{minutes:02d}"
            datetimeStr = f"{dateStr} {timeStr}"

            # Parse the combined datetime string into a datetime object
            datetimeObj = datetime.strptime(datetimeStr, '%d-%m-%Y %H:%M')

            # Localize the datetime object to the specified timezone
            localizedDatetimeObj = convertedTimezone.localize(datetimeObj)

            # Convert the localized datetime object to ISO 8601 format
            isoFormatStr = localizedDatetimeObj.isoformat()

            workTimes.append(isoFormatStr)
        
        # Pass conflicts through unchanged (index 4 of raw entry)
        workTimes.append(entry[4] if len(entry) > 4 else [])
        convertedSchedule.append(workTimes)

    return convertedSchedule

def saveToGoogleCalendar(service, convertedSchedule):
    existingEvents = service.events().list(calendarId='primary', timeMin=convertedSchedule[0][0], timeMax=convertedSchedule[-1][1]).execute()
    
    for schedule in convertedSchedule:
        # Check if the event is already in the calendar from the day before the first event to the day after the last event
        for event in existingEvents['items']:
            # Check if the event has the required fields to compare
            if event.get('status') and event.get('summary') and event.get('start') and event.get('end'):

                if event['status'] == 'cancelled':
                    continue
                if event['summary'] != eventSummary:
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
                    expectedDescription = buildEventDescription(hourRate, schedule[2], conflicts)
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
            # Check if the event is on a Sunday and apply extra percentage if needed
            currentHourRate = hourRate
            if datetime.fromisoformat(schedule[0]).weekday() == 6: # Sunday
                currentHourRate = hourRate * (1 + EXTRA_SUNDAY_PERCENTAGE)
            description = buildEventDescription(currentHourRate, schedule[2], conflicts)

            event = {
                'summary': eventSummary,
                'start': {
                    'dateTime': schedule[0],
                    'timeZone': eventTimezone,
                },
                'end': {
                    'dateTime': schedule[1],
                    'timeZone': eventTimezone,
                },
                'colorId': '5' if conflicts else '10',
                'description': description,
                'location': eventLocation,
            }

            # Insert the event
            event = service.events().insert(calendarId='primary', body=event).execute()
            print('Event created: %s' % (event.get('htmlLink')))

def calculateWageForEvent(hourRate, duration):
    return '' if hourRate == 0 else '€ {:.2f}'.format(float(hourRate) * float(duration))

def buildEventDescription(hourRate, duration, conflicts):
    parts = []
    wage = calculateWageForEvent(hourRate, duration)
    if wage:
        parts.append(wage)
    if conflicts:
        conflict_parts = []
        for field, period in conflicts:
            p_start = f"{int(period['startTime']) // 60:02d}:{int(period['startTime']) % 60:02d}"
            p_end = f"{int(period['endTime']) // 60:02d}:{int(period['endTime']) % 60:02d}"
            conflict_parts.append(f"{field} {p_start}-{p_end}")
        parts.append("Not available: " + ", ".join(conflict_parts))
    return "\n".join(parts)

if __name__ == "__main__":
    try:
        # Load the environment variables
        load_dotenv()

        global eventTimezone 
        eventTimezone = os.getenv('event_timezone')
        global eventSummary 
        eventSummary = os.getenv('event_summary')
        global eventLocation
        eventLocation = os.getenv('event_location')

        # Setup the Google Calendar service
        service = setupGoogleCalendar()

        # Get the bearer token
        token = getBearerToken()

        # Get the user information about the company id and the user id
        getUserInformation(token)

        # Get the schedule of the user for x weeks
        rawSchedule = getWorkweeks(token, 5)

        # Convert schedule to normal datetime format
        convertedSchedule = convertSchedule(rawSchedule)

        # Save the schedule to Google Calendar
        saveToGoogleCalendar(service, convertedSchedule)

    except Exception as e:
        print(e)

