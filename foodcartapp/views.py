from django.db import transaction
from django.http import JsonResponse
from django.templatetags.static import static

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import Order, OrderItem, Product
from .serializers import OrderSerializer

def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse(
        [
            {
                "title": "Burger",
                "src": static("burger.jpg"),
                "text": "Tasty Burger at your door step",
            },
            {
                "title": "Spices",
                "src": static("food.jpg"),
                "text": "All Cuisines",
            },
            {
                "title": "New York",
                "src": static("tasty.jpg"),
                "text": "Food is incomplete without a tasty dessert",
            },
        ],
        safe=False,
        json_dumps_params={
            "ensure_ascii": False,
            "indent": 4,
        },
    )


def product_list_api(request):
    products = Product.objects.select_related("category").available()

    dumped_products = []
    for product in products:
        dumped_product = {
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "special_status": product.special_status,
            "description": product.description,
            "category": {
                "id": product.category.id,
                "name": product.category.name,
            }
            if product.category
            else None,
            "image": product.image.url,
            "restaurant": {
                "id": product.id,
                "name": product.name,
            },
        }
        dumped_products.append(dumped_product)
    return JsonResponse(
        dumped_products,
        safe=False,
        json_dumps_params={
            "ensure_ascii": False,
            "indent": 4,
        },
    )


@transaction.atomic
@api_view(["POST"])
def register_order(request):
    serializer = OrderSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    products_list = serializer.validated_data["products"]
    firstname = serializer.validated_data["firstname"]
    lastname = serializer.validated_data["lastname"]
    address = serializer.validated_data["address"]
    phonenumber = serializer.validated_data["phonenumber"]

    order = Order.objects.create(
        firstname=firstname,
        lastname=lastname,
        address=address,
        phonenumber=phonenumber,
        status='raw',
    )
    for product in products_list:
        product_obj = product.get('product')
        OrderItem.objects.create(
            order_id=order.id,
            product_id=product_obj.id,
            quantity=product.get('quantity'),
            price=product_obj.price,
        )

    order_serializer = OrderSerializer(order)

    return Response(order_serializer.data, status=status.HTTP_201_CREATED)