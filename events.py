from datetime import datetime

import config


def getRateForShift(schedule):
    # Apply the extra Sunday percentage so all calendars use the same rate
    if datetime.fromisoformat(schedule[0]).weekday() == 6: # Sunday
        return config.hourRate * (1 + config.EXTRA_SUNDAY_PERCENTAGE)
    return config.hourRate


def calculateWageForEvent(hourRate, duration):
    return None if hourRate == 0 else float(hourRate) * float(duration)


def buildEventDescription(hourRate, duration, conflicts):
    parts = []
    wage = calculateWageForEvent(hourRate, duration)
    if wage is not None:
        # Travel allowance covers the round trip (to work and back)
        travelAllowance = config.travelAllowancePerKm * config.singleRideJourneyKm * 2
        parts.append('Salary: € {:.2f}'.format(wage))
        if travelAllowance:
            parts.append('Allowance: € {:.2f}'.format(travelAllowance))
            parts.append('Total: € {:.2f}'.format(wage + travelAllowance))
    if conflicts:
        conflict_parts = []
        for field, period in conflicts:
            p_start = f"{int(period['startTime']) // 60:02d}:{int(period['startTime']) % 60:02d}"
            p_end = f"{int(period['endTime']) // 60:02d}:{int(period['endTime']) % 60:02d}"
            conflict_parts.append(f"{field} {p_start}-{p_end}")
        parts.append("Not available: " + ", ".join(conflict_parts))
    return "\n".join(parts)


def buildShiftUid(schedule):
    # Deterministic UID per shift so re-uploads update in place instead of duplicating
    return 'manus-%s@manusplustocalendar' % datetime.fromisoformat(schedule[0]).strftime('%Y%m%dT%H%M%S')
