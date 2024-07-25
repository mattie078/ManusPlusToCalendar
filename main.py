from datetime import datetime, timedelta
import os
from dotenv import *
import requests
import pytz

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

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

def getWorkweeks(token, week_amount):
    schedule = []
    current_year = datetime.now().isocalendar()[0]
    current_week = datetime.now().isocalendar()[1]

    headers = {
        'authorization': 'Bearer '+token,    
    }

    global hourRate
    hourRate = 0

    for i in range(0, week_amount):
        response = requests.get(
            'https://server.manus.plus/' + os.getenv('company_name') + '/api/node/' + nodeId + '/employee/' + employeeId + '/schedule/' + str(current_year) + '/' + str(current_week+i) +'/fromData',
            headers=headers,
        )
        weekData = response.json()

        if weekData.get('message'):
            print(f"Failed to get schedule for week {current_week+i}: {weekData['message']}")
            continue
        
        if not weekData.get('contracts'):
            print(f"No contracts found for week {current_week+i}")
            continue
        
        if not weekData.get('schedule'):
            print(f"No schedule found for week {current_week+i}")
            continue

        weekContract = weekData['contracts'][0]
        if hourRate == 0 and weekContract.get('hourRate'):
            hourRate = weekContract['hourRate']
            
        weekSchedule = weekData['schedule']
        for workDay in weekSchedule:
            if workDay.get('entries'):
                for entry in workDay['entries']:
                    schedule.append([entry['fromDate'], entry['startTime'], entry['endTime'], entry['totalTime']])
    return schedule

def convertSchedule(schedule):
    convertedSchedule = []

    # ManusPlus start date
    start_date = datetime(1900, 1, 1)

    # Convert Timezone so it can be used in the datetime object
    convertedTimezone = pytz.timezone(timezone)

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
                    print('Event already exists, skipping: %s' % (event.get('htmlLink')))
                    break
        else:
            description = '' if hourRate == 0 else '€ ' + str(float(hourRate) * float(schedule[2]))
                       
            event = {
                'summary': eventSummary,
                'start': {
                    'dateTime': schedule[0],
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': schedule[1],
                    'timeZone': timezone,
                },
                'colorId': 10,
                'description': description,
                'location': eventLocation,
            }

            # Insert the event
            event = service.events().insert(calendarId='primary', body=event).execute()
            print('Event created: %s' % (event.get('htmlLink')))

def setupGoogleCalendar():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def addColleagues(token, schedule):
    for workDay in schedule:  
        # Convert dateTime to YYYY-MM-DD
        date = workDay[0].split('T')[0]
        
        headers = {
            'authorization': 'Bearer '+token
        }

        params = {
            'departmentId': '-1',
            'scheduledOnly': 'true',
        }

        response = requests.get(
            'https://server.manus.plus/' + os.getenv('company_name') + '/api/node/' + nodeId + '/schedule/' +date,
            params=params,
            headers=headers,
        )
        
        response_data = response.json()
        
        collegesWithWorkTimes = []
        
        schedule_data = response_data['schedule']
        for collegeData in schedule_data:
            college = []
            if collegeData.get('entries'):
                for collegeEntry in collegeData['entries']:
                    if collegeEntry.get('noteId'):
                        college.append(collegeEntry['noteId'])
            else:
                continue
            
            
            
            

if __name__ == "__main__":
    try:
        # Load the environment variables
        load_dotenv()

        global timezone 
        timezone = os.getenv('event_timezone')
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

        # convertedScheduleWithColleagues = addColleagues(token, convertedSchedule)

        # Save the schedule to Google Calendar
        saveToGoogleCalendar(service, convertedSchedule)

    except Exception as e:
        print(e)






