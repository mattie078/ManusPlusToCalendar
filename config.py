import os
from dotenv import load_dotenv

# Google OAuth scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Extra percentage paid on top of the hourly rate for Sunday shifts (0.5 = +50%)
EXTRA_SUNDAY_PERCENTAGE = 0.5

# Absence fields that can overlap a shift and mark it as an availability conflict
AVAILABILITY_CONFLICT_FIELDS = ['unavailability', 'illness', 'vacation', 'holiday']

# Radius in meters Apple Calendar uses around the event location for travel time estimates
APPLE_LOCATION_RADIUS_METERS = 100

# Nominatim requires requests to identify the application they come from
GEOCODING_USER_AGENT = 'ManusPlusToCalendar (https://github.com/mattie078/ManusPlusToCalendar)'
GEOCODING_TIMEOUT_SECONDS = 10

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


def load_from_env():
    """Load the .env file and populate the configuration values."""
    load_dotenv()

    global eventTimezone, eventSummary, eventLocation, eventLocationTitle
    global travelAllowancePerKm, singleRideJourneyKm
    global icloudUsername, icloudAppPassword, icloudCalendarName

    eventTimezone = os.getenv('event_timezone')
    eventSummary = os.getenv('event_summary')
    eventLocation = os.getenv('event_location')
    eventLocationTitle = os.getenv('event_location_title')
    travelAllowancePerKm = float(os.getenv('travel_allowance_per_km') or 0)
    singleRideJourneyKm = float(os.getenv('single_ride_journey_km') or 0)
    icloudUsername = os.getenv('icloud_username')
    icloudAppPassword = os.getenv('icloud_app_password')
    icloudCalendarName = os.getenv('icloud_calendar_name') or 'Work'
