"""Sync a MyManus work schedule into Google Calendar and/or Apple Calendar.

Run with: python main.py
"""

import sys
import traceback

from manusplustocalendar import config
from manusplustocalendar.manus_client import (
    getBearerToken, getUserInformation, getWorkweeks, convertSchedule,
)
from manusplustocalendar.google_calendar import (
    setupGoogleCalendar, saveToGoogleCalendar, isGoogleConfigured,
)
from manusplustocalendar.icloud_calendar import saveToICloudCalendar


def isICloudConfigured():
    return bool(config.icloudUsername and config.icloudAppPassword)


def main():
    config.load_from_env()

    googleConfigured = isGoogleConfigured()
    icloudConfigured = isICloudConfigured()

    if not googleConfigured and not icloudConfigured:
        print('Warning: no calendar is configured, so the schedule will be fetched '
              'but not written anywhere. See README.md steps 5 and 6.')

    token = getBearerToken()

    # Fills in the company and employee ids needed to build the schedule URL
    getUserInformation(token)

    rawSchedule = getWorkweeks(token, config.WEEKS_TO_SYNC)
    convertedSchedule = convertSchedule(rawSchedule)

    # Expected once a contract ends, so say so rather than looking like a failure
    if not convertedSchedule:
        print('No shifts found in the next %d weeks. Nothing to sync.' % config.WEEKS_TO_SYNC)
        return

    print('Found %d shift(s) to sync.' % len(convertedSchedule))

    if googleConfigured:
        service = setupGoogleCalendar()
        saveToGoogleCalendar(service, convertedSchedule)
    else:
        print('Google Calendar not configured, skipping.')

    if icloudConfigured:
        saveToICloudCalendar(convertedSchedule)
    else:
        print('iCloud Calendar not configured, skipping.')


if __name__ == "__main__":
    try:
        main()
    except config.ConfigError as error:
        # A setup mistake, not a bug, so show the message without a traceback
        print('\nConfiguration problem:\n%s' % error)
        sys.exit(1)
    except KeyboardInterrupt:
        print('\nInterrupted.')
        sys.exit(130)
    except Exception:
        print('\nSomething went wrong. The full error follows.\n')
        traceback.print_exc()
        print('\nSee the Troubleshooting section of README.md.')
        sys.exit(1)
