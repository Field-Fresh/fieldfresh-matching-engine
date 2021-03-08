import math

## General utils for preprocessing and matching engine stuff

EARTH_RADIUS_KM = 6371

def distance(origin, destination) -> float:
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = EARTH_RADIUS_KM # km

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c

    return d