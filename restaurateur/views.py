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
from foodcartapp.models import Order, Product, Restaurant, RestaurantMenuItem
from django.conf import settings
from collections import defaultdict
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from geopy.distance import geodesic
import requests
import logging

from foodcartapp.models import Order

from geopy.geocoders import Yandex
from geopy.distance import distance
from geopy.exc import GeocoderServiceError

geolocator = Yandex(api_key=settings.YANDEX_GEOCODER_API_KEY)


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
        label='Логин', max_length=75, required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Укажите имя пользователя'
        })
    )
    password = forms.CharField(
        label='Пароль', max_length=75, required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )


class LoginView(View):
    def get(self, request, *args, **kwargs):
        form = Login()
        return render(request, "login.html", context={
            'form': form
        })

    def post(self, request):
        form = Login(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                if user.is_staff:  # FIXME replace with specific permission
                    return redirect("restaurateur:RestaurantView")
                return redirect("start_page")

        return render(request, "login.html", context={
            'form': form,
            'ivalid': True,
        })


class LogoutView(auth_views.LogoutView):
    next_page = reverse_lazy('restaurateur:login')


def is_manager(user):
    return user.is_staff  # FIXME replace with specific permission


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_products(request):
    restaurants = list(Restaurant.objects.order_by('name'))
    products = list(Product.objects.prefetch_related('menu_items'))

    products_with_restaurant_availability = []
    for product in products:
        availability = {item.restaurant_id: item.availability for item in product.menu_items.all()}
        ordered_availability = [availability.get(restaurant.id, False) for restaurant in restaurants]

        products_with_restaurant_availability.append(
            (product, ordered_availability)
        )

    return render(request, template_name="products_list.html", context={
        'products_with_restaurant_availability': products_with_restaurant_availability,
        'restaurants': restaurants,
    })


@user_passes_test(is_manager, login_url='restaurateur:login')
def view_restaurants(request):
    return render(request, template_name="restaurants_list.html", context={
        'restaurants': Restaurant.objects.all(),
    })




GEOCODER_API_KEY = settings.YANDEX_GEOCODER_API_KEY
GEOCODER_API_URL = 'https://geocode-maps.yandex.ru/1.x'

logger = logging.getLogger(__name__)



@user_passes_test(is_manager, login_url='restaurateur:login')
def view_orders(request):
    orders = (
        Order.objects
        .with_total_price()
        .exclude(status='completed')
        .prefetch_related('items__product')
        .select_related('restaurant')
        .order_by('-id')
    )

    menu_items = RestaurantMenuItem.objects.filter(availability=True).select_related('restaurant', 'product')

    available_in = defaultdict(set)
    for item in menu_items:
        available_in[item.product_id].add(item.restaurant_id)

    restaurants = list(Restaurant.objects.all())

    restaurant_locations = {}
    for restaurant in restaurants:
        coords = fetch_coordinates(settings.YANDEX_GEOCODER_API_KEY, restaurant.address)
        if coords:
            restaurant_locations[restaurant.id] = coords

    order_infos = []
    for order in orders:
        products = [item.product for item in order.items.all()]
        suitable_restaurants = []
        order_coords = fetch_coordinates(settings.YANDEX_GEOCODER_API_KEY, order.address)

        if order_coords:
            for restaurant in restaurants:
                if all(restaurant.id in available_in[product.id] for product in products):
                    coords = restaurant_locations.get(restaurant.id)
                    if coords:
                        distance = geodesic(order_coords, coords).km
                        suitable_restaurants.append((restaurant, round(distance, 3)))
        else:
            suitable_restaurants = None

        assigned_restaurant_info = None
        assigned_restaurant = next((r for r in restaurants if r.id == order.restaurant_id), None)
        if assigned_restaurant:
            assigned_coords = restaurant_locations.get(order.restaurant_id)
            if order_coords and assigned_coords:
                distance = geodesic(order_coords, assigned_coords).km
                assigned_restaurant_info = (assigned_restaurant, round(distance, 3))
            else:
                assigned_restaurant_info = (assigned_restaurant, None)

        order_infos.append({
            'order': order,
            'available_restaurants': suitable_restaurants,
            'assigned_restaurant_info': assigned_restaurant_info,
        })

    return render(request, 'order_items.html', {'order_infos': order_infos})


def fetch_coordinates(GEOCODER_API_KEY, address):
    try:
        response = requests.get(GEOCODER_API_URL, params={
            'geocode': address,
            'apikey': GEOCODER_API_KEY,
            'format': 'json',
        })
        response.raise_for_status()
        found_places = response.json()['response']['GeoObjectCollection']['featureMember']
        if not found_places:
            return None
        most_relevant = found_places[0]
        lon, lat = map(float, most_relevant['GeoObject']['Point']['pos'].split(" "))
        return lat, lon
    except requests.exceptions.RequestException as e:
        logger.error(f"Geocoding request failed: {e}")
        return None
