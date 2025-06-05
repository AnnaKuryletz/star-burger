import requests
from django.conf import settings
from foodcartapp.models import Location

from geopy.geocoders import Yandex


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
    if address in coords_cache:
        coords = coords_cache[address]
    else:
        geolocator = Yandex(api_key=settings.YANDEX_GEOCODER_API_KEY)
        location, _ = Location.objects.get_or_create(address=address)

        if not location.lat or not location.lon:
            try:
                geo = geolocator.geocode(address)
                if geo:
                    location.lat = geo.latitude
                    location.lon = geo.longitude
                    location.save()
            except Exception as e:
                print(f"Geocoding error: {e}")
                coords_cache[address] = None
                return

        coords = (location.lat, location.lon) if location.lat and location.lon else None
        coords_cache[address] = coords

    if coords:
        location = Location.objects.get(address=address)
        obj.location = location
        updated_objects.append(obj)