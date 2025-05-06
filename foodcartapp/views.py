from django.http import JsonResponse
from django.templatetags.static import static


from .models import Product, Order, OrderItem
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

import re


def banners_list_api(request):
    # FIXME move data to db?
    return JsonResponse([
        {
            'title': 'Burger',
            'src': static('burger.jpg'),
            'text': 'Tasty Burger at your door step',
        },
        {
            'title': 'Spices',
            'src': static('food.jpg'),
            'text': 'All Cuisines',
        },
        {
            'title': 'New York',
            'src': static('tasty.jpg'),
            'text': 'Food is incomplete without a tasty dessert',
        }
    ], safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })


def product_list_api(request):
    products = Product.objects.select_related('category').available()

    dumped_products = []
    for product in products:
        dumped_product = {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'special_status': product.special_status,
            'description': product.description,
            'category': {
                'id': product.category.id,
                'name': product.category.name,
            } if product.category else None,
            'image': product.image.url,
            'restaurant': {
                'id': product.id,
                'name': product.name,
            }
        }
        dumped_products.append(dumped_product)
    return JsonResponse(dumped_products, safe=False, json_dumps_params={
        'ensure_ascii': False,
        'indent': 4,
    })



PHONE_REGEX = r'^\+79\d{9}$'  

@api_view(['POST'])
def register_order(request):
    serialized_order = request.data

    if 'products' not in serialized_order:
        return Response({'products': 'Обязательное поле.'}, status=status.HTTP_400_BAD_REQUEST)

    products = serialized_order['products']

    if products is None:
        return Response({'products': 'Это поле не может быть пустым.'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(products, list):
        return Response({
            'products': f'Ожидался список со значениями, но был получен «{type(products).__name__}».'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not products:
        return Response({'products': 'Этот список не может быть пустым.'}, status=status.HTTP_400_BAD_REQUEST)

    required_fields = ['firstname', 'lastname', 'phonenumber', 'address']
    missing_fields = [field for field in required_fields if field not in serialized_order]
    if missing_fields:
        return Response(
            {field: 'Обязательное поле.' for field in missing_fields},
            status=status.HTTP_400_BAD_REQUEST
        )

    errors = {}
    for field in required_fields:
        value = serialized_order.get(field)
        if value is None or value == '':
            errors[field] = 'Это поле не может быть пустым.'
        elif not isinstance(value, str):
            errors[field] = 'Not a valid string.'
    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    phone = serialized_order.get('phonenumber')
    if phone and not re.match(PHONE_REGEX, phone):
        return Response({'phonenumber': 'Введен некорректный номер телефона.'}, status=status.HTTP_400_BAD_REQUEST)
   
    for product_data in products:
        product_id = product_data.get('product')
        if not Product.objects.filter(pk=product_id).exists():
            return Response({'products': f'Недопустимый первичный ключ "{product_id}"'},
                            status=status.HTTP_400_BAD_REQUEST)

    order = Order.objects.create(
        first_name=serialized_order['firstname'],
        last_name=serialized_order['lastname'],
        address=serialized_order['address'],
        phone_number=serialized_order['phonenumber'],
    )

    for product_data in products:
        OrderItem.objects.create(
            order=order,
            product_id=product_data['product'],
            quantity=product_data['quantity']
        )

    return Response({'message': 'Заказ успешно создан'}, status=status.HTTP_201_CREATED)
