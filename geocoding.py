import requests

import config

# The looked up location is cached so the geocoder is queried once per session instead of
# once per event. A failed lookup is cached too, so a run never retries a hopeless address.
cachedAddress = None
cachedCoordinates = None


def getLocationCoordinates():
    """Return the (latitude, longitude) of the configured event location, or None when it
    cannot be resolved. The geocoder is only called the first time per session."""
    global cachedAddress, cachedCoordinates

    if not config.eventLocation:
        return None

    if cachedAddress != config.eventLocation:
        cachedAddress = config.eventLocation
        cachedCoordinates = lookupCoordinates(config.eventLocation)

    return cachedCoordinates


def lookupCoordinates(address):
    """Geocode an address through OpenStreetMap's Nominatim, which needs no API key."""
    try:
        response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': address, 'format': 'json', 'limit': 1},
            # Nominatim rejects requests that do not identify the application
            headers={'User-Agent': config.GEOCODING_USER_AGENT},
            timeout=config.GEOCODING_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        results = response.json()
    except (requests.RequestException, ValueError) as error:
        print('Could not look up the coordinates of "%s": %s' % (address, error))
        return None

    if not results:
        print('No coordinates found for "%s", using a text only location.' % address)
        return None

    print('Resolved "%s" to %s, %s' % (address, results[0]['lat'], results[0]['lon']))
    return float(results[0]['lat']), float(results[0]['lon'])


def roundCoordinates(coordinates):
    """Round to the precision the calendar keeps, so comparing stored against expected
    coordinates does not report a difference that is not there."""
    return None if coordinates is None else (round(coordinates[0], 5), round(coordinates[1], 5))
