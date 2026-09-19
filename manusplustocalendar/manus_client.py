from datetime import datetime, timedelta

import requests
import pytz

from . import config

API_HOST = 'https://server.manus.plus'
REQUEST_TIMEOUT_SECONDS = 30


def apiUrl(path):
    return '%s/%s%s' % (API_HOST, config.companyName, path)


def getBearerToken():
    data = {
        'client_id': 'employee',
        'grant_type': 'password',
        'username': config.manusUsername,
        'password': config.manusPassword,
    }

    try:
        response = requests.post(apiUrl('/app/token'), data=data, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as error:
        raise Exception(
            "Could not reach MyManus at %s: %s\n"
            "Check your connection and that company_name in .env is correct." % (API_HOST, error)
        )

    if response.status_code == 200:
        return response.json()['access_token']

    if response.status_code in (400, 401):
        raise Exception(
            "MyManus rejected the login (%s).\n"
            "Check manus_username and manus_password in .env. If you have left the "
            "company, the account may be deactivated.\n"
            "Server said: %s" % (response.status_code, response.text)
        )

    raise Exception(f"Failed to get token: {response.status_code}, {response.text}")


def getUserInformation(token):
    headers = {
        'authorization': 'Bearer '+token,
    }
    response = requests.get(apiUrl('/api/user/me'), headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
    information_data = response.json()

    # The API returns JSON for errors too, so check before indexing
    if 'nodeId' not in information_data or 'employeeId' not in information_data:
        raise Exception(
            "MyManus did not return the expected account details, which usually "
            "means the account has no active contract.\n"
            "Server said: %s" % information_data
        )

    config.nodeId = information_data['nodeId']
    config.employeeId = information_data['employeeId']


def getAvailabilityConflicts(workDay, entry):
    """Return list of (field, period) tuples where the entry overlaps an absence period."""
    conflicts = []
    for field in config.AVAILABILITY_CONFLICT_FIELDS:
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

    config.hourRate = 0

    for i in range(week_amount):
        adjusted_date = datetime.now() + timedelta(weeks=i)
        year, week, _ = adjusted_date.isocalendar()

        response = requests.get(
            apiUrl(f'/api/node/{config.nodeId}/employee/{config.employeeId}/schedule/{year}/{week}/fromData'),
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
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
        if config.hourRate == 0 and weekContract.get('hourRate'):
            config.hourRate = weekContract['hourRate']
        weekSchedule = weekData['schedule']
        for workDay in weekSchedule:
            # Days not yet published by the employer come back as null
            if not workDay:
                continue
            if workDay.get('entries'):
                for entry in workDay['entries']:
                    conflicts = getAvailabilityConflicts(workDay, entry)
                    schedule.append([entry['fromDate'], entry['startTime'], entry['endTime'], entry['totalTime'], conflicts])
    return schedule


def convertSchedule(schedule):
    """Convert raw MyManus rows into the shift rows both calendar modules index:

        row[0] start ISO string, row[1] end ISO string,
        row[2] duration in decimal hours, row[3] availability conflicts

    MyManus sends dates as days since 1900-01-01 and times as minutes since midnight.
    """
    convertedSchedule = []

    # MyManus start date
    start_date = datetime(1900, 1, 1)

    # Convert Timezone so it can be used in the datetime object
    convertedTimezone = pytz.timezone(config.eventTimezone)

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
