from datetime import datetime

import pytz

import config
from events import getRateForShift, buildEventDescription, buildShiftUid


def saveToICloudCalendar(convertedSchedule):
    # Imported lazily so caldav is only required when iCloud is actually configured
    import caldav
    from icalendar import Calendar as ICalendar, Event as IEvent

    client = caldav.DAVClient(url='https://caldav.icloud.com', username=config.icloudUsername, password=config.icloudAppPassword)
    principal = client.principal()

    calendars = principal.calendars()
    calendar = next((c for c in calendars if c.get_display_name() == config.icloudCalendarName), None)
    if calendar is None:
        knownNames = ', '.join("'%s'" % c.get_display_name() for c in calendars) or '(none)'
        raise Exception("No iCloud calendar named '%s' found. Available calendars: %s" % (config.icloudCalendarName, knownNames))

    # Fetch existing events once via a time-range search (iCloud rejects the per-UID REPORT
    # that event_by_uid uses) and index them by UID so re-runs update in place.
    rangeStart = datetime.fromisoformat(convertedSchedule[0][0])
    rangeEnd = datetime.fromisoformat(convertedSchedule[-1][1])
    existingByUid = {}
    for obj in calendar.search(start=rangeStart, end=rangeEnd, event=True, expand=False):
        try:
            existingByUid[str(obj.icalendar_component.get('UID'))] = obj
        except Exception:
            continue

    for schedule in convertedSchedule:
        currentHourRate = getRateForShift(schedule)
        conflicts = schedule[3] if len(schedule) > 3 else []
        description = buildEventDescription(currentHourRate, schedule[2], conflicts)
        uid = buildShiftUid(schedule)

        eventStart = datetime.fromisoformat(schedule[0])
        eventEnd = datetime.fromisoformat(schedule[1])

        existing = existingByUid.get(uid)
        # Skip re-uploading when the existing event already matches (avoids updating every run)
        if existing is not None and icloudEventMatches(existing, eventStart, eventEnd, description):
            print('iCloud event already exists, skipping: %s' % uid)
            continue

        cal = ICalendar()
        cal.add('prodid', '-//ManusPlusToCalendar//EN')
        cal.add('version', '2.0')

        vevent = IEvent()
        vevent.add('uid', uid)
        vevent.add('summary', config.eventSummary)
        vevent.add('dtstart', eventStart)
        vevent.add('dtend', eventEnd)
        vevent.add('dtstamp', datetime.now(pytz.timezone(config.eventTimezone)))
        if description:
            vevent.add('description', description)
        if config.eventLocation:
            vevent.add('location', config.eventLocation)
        cal.add_component(vevent)
        ical = cal.to_ical()

        if existing is not None:
            existing.data = ical
            existing.save()
            print('iCloud event updated: %s' % uid)
        else:
            calendar.save_event(ical)
            print('iCloud event created: %s' % uid)


def icloudEventMatches(existing, eventStart, eventEnd, description):
    """Return True when the stored iCloud event already has the expected times, summary,
    description and location, so it does not need to be re-uploaded."""
    try:
        component = existing.icalendar_component
    except Exception:
        return False

    def field(name):
        value = component.get(name)
        return '' if value is None else str(value)

    def wallClock(value):
        # Normalise to a naive local wall-clock time so a stored floating datetime
        # (which iCloud returns without a timezone) compares equal to our tz-aware value.
        if value is None or not isinstance(value, datetime):
            return None
        if value.tzinfo is not None:
            value = value.astimezone(pytz.timezone(config.eventTimezone))
        return value.replace(tzinfo=None)

    def moment(name):
        value = component.get(name)
        return wallClock(value.dt) if value is not None else None

    return (
        field('SUMMARY') == (config.eventSummary or '')
        and moment('DTSTART') == wallClock(eventStart)
        and moment('DTEND') == wallClock(eventEnd)
        and field('DESCRIPTION') == (description or '')
        and field('LOCATION') == (config.eventLocation or '')
    )
