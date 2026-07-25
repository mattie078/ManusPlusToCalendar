import os
from dotenv import load_dotenv

# Google OAuth scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Extra percentage paid on top of the hourly rate for Sunday shifts (0.5 = +50%)
EXTRA_SUNDAY_PERCENTAGE = 0.5

# Absence fields that can overlap a shift and mark it as an availability conflict
AVAILABILITY_CONFLICT_FIELDS = ['unavailability', 'illness', 'vacation', 'holiday']

# Event settings (populated from the environment)
eventTimezone = None
eventSummary = None
eventLocation = None

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


def load_from_env():
    """Load the .env file and populate the configuration values."""
    load_dotenv()

    global eventTimezone, eventSummary, eventLocation
    global travelAllowancePerKm, singleRideJourneyKm
    global icloudUsername, icloudAppPassword, icloudCalendarName

    eventTimezone = os.getenv('event_timezone')
    eventSummary = os.getenv('event_summary')
    eventLocation = os.getenv('event_location')
    travelAllowancePerKm = float(os.getenv('travel_allowance_per_km') or 0)
    singleRideJourneyKm = float(os.getenv('single_ride_journey_km') or 0)
    icloudUsername = os.getenv('icloud_username')
    icloudAppPassword = os.getenv('icloud_app_password')
    icloudCalendarName = os.getenv('icloud_calendar_name') or 'Work'
