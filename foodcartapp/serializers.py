from rest_framework import serializers
from foodcartapp.models import Order, OrderItem
from rest_framework.serializers import ModelSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


class OrderSerializer(ModelSerializer):
    products = OrderItemSerializer(many=True, allow_empty=False, write_only=True)

    class Meta:
        model = Order
        fields = ["firstname", "lastname", "address", "phonenumber", "products"]

    def create(self, validated_data):
        products_data = validated_data.pop("products")
        order = Order.objects.create(**validated_data)

        order_items = [
            OrderItem(
                order=order,
                product=product_data["product"],
                quantity=product_data["quantity"],
                price=product_data["product"].price,
            )
            for product_data in products_data
        ]

        OrderItem.objects.bulk_create(order_items)
        return order
