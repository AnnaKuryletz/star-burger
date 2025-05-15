from rest_framework import serializers
from foodcartapp.models import Order, OrderItem
from rest_framework.serializers import ModelSerializer

from foodcartapp.services.geolocation import (
    get_or_update_coordinates,
)


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

        coords_cache = {} 
        updated_orders = []

        get_or_update_coordinates(
            obj=order,
            address=order.address,
            coords_cache=coords_cache,
            updated_objects=updated_orders,
        )

        if updated_orders:
            Order.objects.bulk_update(updated_orders, ["location"])

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