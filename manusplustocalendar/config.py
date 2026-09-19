import os

import pytz
from dotenv import load_dotenv

# Google OAuth scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Files read and written at runtime, relative to the working directory
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# Extra percentage paid on top of the hourly rate for Sunday shifts (0.5 = +50%)
EXTRA_SUNDAY_PERCENTAGE = 0.5

# Absence fields that can overlap a shift and mark it as an availability conflict
AVAILABILITY_CONFLICT_FIELDS = ['unavailability', 'illness', 'vacation', 'holiday']

# Radius in meters Apple Calendar uses around the event location for travel time estimates
APPLE_LOCATION_RADIUS_METERS = 100

# Nominatim requires requests to identify the application they come from
GEOCODING_USER_AGENT = 'ManusPlusToCalendar (https://github.com/mattie078/ManusPlusToCalendar)'
GEOCODING_TIMEOUT_SECONDS = 10

# How many weeks ahead to sync, counting the current week
WEEKS_TO_SYNC = 5

# Settings that must be filled in before the script can run
REQUIRED_SETTINGS = ('company_name', 'manus_username', 'manus_password',
                     'event_summary', 'event_timezone')

# MyManus account (populated from the environment)
companyName = None
manusUsername = None
manusPassword = None

# Event settings (populated from the environment)
eventTimezone = None
eventSummary = None
eventLocation = None
eventLocationTitle = None

# Travel allowance settings (populated from the environment)
travelAllowancePerKm = 0.0
singleRideJourneyKm = 0.0

# iCloud settings (populated from the environment)
icloudUsername = None
icloudAppPassword = None
icloudCalendarName = 'Work'

# Runtime state, populated while the schedule is fetched
hourRate = 0
nodeId = None
employeeId = None


class ConfigError(Exception):
    """Raised for a bad or incomplete .env, so main.py can skip the traceback."""


def readText(name):
    return (os.getenv(name) or '').strip()


def readNumber(name):
    """Read an optional numeric setting, treating blank as zero."""
    raw = readText(name)
    if not raw:
        return 0.0
    try:
        # Accept '0,23' as well as '0.23'
        return float(raw.replace(',', '.'))
    except ValueError:
        raise ConfigError("%s must be a number (for example 0.23), but is '%s'." % (name, raw))


def load_from_env():
    """Load the .env file, populate the configuration values and validate them."""
    load_dotenv()

    global companyName, manusUsername, manusPassword
    global eventTimezone, eventSummary, eventLocation, eventLocationTitle
    global travelAllowancePerKm, singleRideJourneyKm
    global icloudUsername, icloudAppPassword, icloudCalendarName

    companyName = readText('company_name')
    manusUsername = readText('manus_username')
    manusPassword = os.getenv('manus_password') or ''

    eventTimezone = readText('event_timezone')
    eventSummary = readText('event_summary')
    eventLocation = readText('event_location')
    eventLocationTitle = readText('event_location_title')

    travelAllowancePerKm = readNumber('travel_allowance_per_km')
    singleRideJourneyKm = readNumber('single_ride_journey_km')

    icloudUsername = readText('icloud_username')
    icloudAppPassword = os.getenv('icloud_app_password') or ''
    icloudCalendarName = readText('icloud_calendar_name') or 'Work'

    validate()


def validate():
    values = {
        'company_name': companyName,
        'manus_username': manusUsername,
        'manus_password': manusPassword,
        'event_summary': eventSummary,
        'event_timezone': eventTimezone,
    }

    missing = sorted(name for name in REQUIRED_SETTINGS if not values[name])
    if missing:
        raise ConfigError(
            "These required settings are still empty in .env: %s\n"
            "Open .env and fill them in." % ', '.join(missing)
        )

    if eventTimezone not in pytz.all_timezones:
        raise ConfigError(
            "event_timezone '%s' is not a known timezone.\n"
            "Use a TZ database name such as 'Europe/Amsterdam'." % eventTimezone
        )

    # The allowance needs both halves to add up to anything
    if bool(travelAllowancePerKm) != bool(singleRideJourneyKm):
        print("Warning: travel allowance needs both travel_allowance_per_km and "
              "single_ride_journey_km; one is empty, so no allowance will be shown.")
