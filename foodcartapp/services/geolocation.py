import requests
from django.conf import settings
from foodcartapp.models import Location


def fetch_coordinates(api_key, address):
    url = "https://geocode-maps.yandex.ru/1.x"
    params = {"apikey": api_key, "geocode": address, "format": "json"}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        geo_data = response.json()
        coords = geo_data["response"]["GeoObjectCollection"]["featureMember"][0][
            "GeoObject"
        ]["Point"]["pos"]
        lon, lat = map(float, coords.split(" "))
        return lat, lon
    except (IndexError, KeyError, ValueError, requests.RequestException):
        return None, None


def get_or_update_coordinates(obj, address, coords_cache, updated_objects):
    if obj.location and obj.location.lat and obj.location.lon:
        coords_cache[obj.id] = (obj.location.lat, obj.location.lon)
        return

    lat, lon = fetch_coordinates(settings.YANDEX_GEOCODER_API_KEY, address)
    if not (lat and lon):
        coords_cache[obj.id] = None
        return

    location, _ = Location.objects.get_or_create(
        address=address, defaults={"lat": lat, "lon": lon}
    )

    updated = False
    if location.lat is None or location.lon is None:
        location.lat = lat
        location.lon = lon
        updated = True

    obj.location = location
    coords_cache[obj.id] = (lat, lon)
    updated_objects.append(obj)

    if updated:
        location.save()
