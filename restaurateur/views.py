from collections import defaultdict
from django import forms
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.db.models import Prefetch
from django.conf import settings
from foodcartapp.models import Order, Product, Restaurant, RestaurantMenuItem, Location
from django.conf import settings
from collections import defaultdict
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Case, When, IntegerField
import requests
import logging

from foodcartapp.models import Order

from geopy.geocoders import Yandex
from geopy.distance import distance
from geopy.exc import GeocoderServiceError

geolocator = Yandex(api_key=settings.YANDEX_GEOCODER_API_KEY)
GEOCODER_API_KEY = settings.YANDEX_GEOCODER_API_KEY
GEOCODER_API_URL = "https://geocode-maps.yandex.ru/1.x"

logger = logging.getLogger(__name__)


def fetch_coordinates(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return (location.latitude, location.longitude)
    except GeocoderServiceError:
        return None
    return None


class Login(forms.Form):
    username = forms.CharField(
        label="Логин",
        max_length=75,
        required=True,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Укажите имя пользователя"}
        ),
    )
    password = forms.CharField(
        label="Пароль",
        max_length=75,
        required=True,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "Введите пароль"}
        ),
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={"form": form})

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(
            request,
            "login.html",
            context={
                "form": form,
                "ivalid": True,
            },
        )


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy("restaurateur:login")


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_products(request):
    restaurants = list(Restaurant.objects.order_by("name"))
    products = list(Product.objects.prefetch_related("menu_items"))

    products_with_restaurant_availability = []
    for product in products:
        availability = {
            item.restaurant_id: item.availability for item in product.menu_items.all()
        }
        ordered_availability = [
            availability.get(restaurant.id, False) for restaurant in restaurants
        ]

        products_with_restaurant_availability.append((product, ordered_availability))

    return render(
        request,
        template_name="products_list.html",
        context={
            "products_with_restaurant_availability": products_with_restaurant_availability,
            "restaurants": restaurants,
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_restaurants(request):
    return render(
        request,
        template_name="restaurants_list.html",
        context={
            "restaurants": Restaurant.objects.all(),
        },
    )


@user_passes_test(is_manager, login_url="restaurateur:login")
def view_orders(request):
    orders = (
        Order.objects.with_total_price()
        .exclude(status="completed")
        .annotate(
            is_raw=Case(
                When(status="raw", then=1), default=0, output_field=IntegerField()
            )
        )
        .select_related("restaurant", "location")
        .prefetch_related("items__product")
        .order_by("-is_raw", "-id")
    )

    restaurants = list(Restaurant.objects.select_related("location").order_by("name"))
    menu_items = RestaurantMenuItem.objects.filter(availability=True).select_related(
        "restaurant", "product"
    )

    available_in = defaultdict(set)
    for item in menu_items:
        available_in[item.product_id].add(item.restaurant_id)

    restaurants_to_update = []
    restaurant_coords = {}

    for restaurant in restaurants:
        if restaurant.location.lat and restaurant.location.lon:
            restaurant_coords[restaurant.id] = (
                restaurant.location.lat,
                restaurant.location.lon,
            )
        else:
            lat, lon = fetch_coordinates(
                settings.YANDEX_GEOCODER_API_KEY, restaurant.address
            )
            restaurant.location.lat = lat
            restaurant.location.lon = lon
            restaurant_coords[restaurant.id] = (lat, lon) if lat and lon else None
            restaurants_to_update.append(restaurant)

    if restaurants_to_update:
        Restaurant.objects.bulk_update(restaurants_to_update, ["location"])

    orders_to_update = []
    order_coords = {}
    for order in orders:
        if order.location and order.location.lat and order.location.lon:
            order_coords[order.id] = (order.location.lat, order.location.lon)
        else:
            lat, lon = fetch_coordinates(
                settings.YANDEX_GEOCODER_API_KEY, order.address
            )
            if lat and lon:
                location, _ = Location.objects.get_or_create(
                    address=order.address, defaults={"lat": lat, "lon": lon}
                )
                if location.lat is None or location.lon is None:
                    location.lat = lat
                    location.lon = lon
                    location.save()
                order.location = location
                order_coords[order.id] = (lat, lon)
                orders_to_update.append(order)

    if orders_to_update:
        Order.objects.bulk_update(orders_to_update, ["location"])
        Location.objects.bulk_update(
            [order.location for order in orders_to_update if order.location],
            ["lat", "lon"],
        )

    order_infos = []

    for order in orders:
        products = [item.product for item in order.items.all()]
        order_point = order_coords.get(order.id)
        geocode_error = order_point is None

        suitable_restaurants = []
        if order_point:
            for restaurant in restaurants:
                if all(
                    restaurant.id in available_in[product.id] for product in products
                ):
                    rest_point = restaurant_coords.get(restaurant.id)
                    if rest_point:
                        dist = distance(order_point, rest_point).km
                        suitable_restaurants.append((restaurant, round(dist, 2)))
            suitable_restaurants.sort(key=lambda r: r[1])

        assigned_info = None
        if order.restaurant:
            rest_point = restaurant_coords.get(order.restaurant.id)
            if order_point and rest_point:
                assigned_info = (
                    order.restaurant,
                    round(distance(order_point, rest_point).km, 2),
                )
            else:
                assigned_info = (order.restaurant, None)

        order_infos.append(
            {
                "order": order,
                "available_restaurants": suitable_restaurants,
                "assigned_restaurant_info": assigned_info,
                "geocode_error": geocode_error,
            }
        )

    return render(request, "order_items.html", {"order_infos": order_infos})


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
