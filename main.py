import os

import config
from manus_client import getBearerToken, getUserInformation, getWorkweeks, convertSchedule
from google_calendar import setupGoogleCalendar, saveToGoogleCalendar
from icloud_calendar import saveToICloudCalendar


def main():
    # Load the environment variables
    config.load_from_env()

    # Get the bearer token
    token = getBearerToken()

    # Get the user information about the company id and the user id
    getUserInformation(token)

    # Get the schedule of the user for x weeks
    rawSchedule = getWorkweeks(token, 5)

    # Convert schedule to normal datetime format
    convertedSchedule = convertSchedule(rawSchedule)

    # Save the schedule to Google Calendar if configured (credentials.json present)
    if os.path.exists("credentials.json"):
        service = setupGoogleCalendar()
        saveToGoogleCalendar(service, convertedSchedule)
    else:
        print('Google Calendar not configured (no credentials.json), skipping.')

    # Save the schedule to iCloud Calendar if configured
    if config.icloudUsername and config.icloudAppPassword:
        saveToICloudCalendar(convertedSchedule)
    else:
        print('iCloud Calendar not configured, skipping.')


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(e)
