from django.http import JsonResponse
from django.templatetags.static import static


from .models import Product, Order, OrderItem
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status


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

@api_view(['POST'])
def register_order(request):
    serialized_order = request.data

    if 'products' not in serialized_order:
        return Response({'products': 'Обязательное поле.'}, status=status.HTTP_400_BAD_REQUEST)

    products = serialized_order['products']

    if products is None:
        return Response({'products': 'Это поле не может быть пустым.'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(products, list):
        return Response({'products': f'Ожидался список со значениями, но был получен «{type(products).__name__}».'},
                        status=status.HTTP_400_BAD_REQUEST)

    if not products:
        return Response({'products': 'Этот список не может быть пустым.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        first_name = serialized_order['firstname']
        last_name = serialized_order['lastname']
        address = serialized_order['address']
        phone_number = serialized_order['phonenumber']
    except (KeyError, TypeError):
        return Response({'error': 'Некорректные данные заказа'}, status=status.HTTP_400_BAD_REQUEST)

    order = Order.objects.create(
        first_name=first_name,
        last_name=last_name,
        address=address,
        phone_number=phone_number,
    )

    for product in products:
        try:
            OrderItem.objects.create(
                order=order,
                product_id=product['product'],
                quantity=product['quantity']
            )
        except KeyError:
            return Response({'error': 'Некорректные данные продукта'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'message': 'Заказ успешно создан'}, status=status.HTTP_201_CREATED)
