from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import DecimalField, F, Sum
from django.utils import timezone

from phonenumber_field.modelfields import PhoneNumberField


class OrderQuerySet(models.QuerySet):
    def with_total_price(self):
        return self.annotate(
            total_price=Sum(
                F('items__price') * F('items__quantity'),
                output_field=DecimalField()
            )
        )

class Restaurant(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    address = models.CharField(
        'адрес',
        max_length=100,
        blank=True,
    )
    contact_phone = models.CharField(
        'контактный телефон',
        max_length=50,
        blank=True,
    )

    class Meta:
        verbose_name = 'ресторан'
        verbose_name_plural = 'рестораны'

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        products = (
            RestaurantMenuItem.objects
            .filter(availability=True)
            .values_list('product')
        )
        return self.filter(pk__in=products)


class ProductCategory(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(
        'название',
        max_length=50
    )
    category = models.ForeignKey(
        ProductCategory,
        verbose_name='категория',
        related_name='products',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    price = models.DecimalField(
        'цена',
        max_digits=8,
        decimal_places=2,
        null=False,
        blank=False,
        validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        'картинка'
    )
    special_status = models.BooleanField(
        'спец.предложение',
        default=False,
        db_index=True,
    )
    description = models.TextField(
        'описание',
        max_length=200,
        blank=True,
    )

    objects = ProductQuerySet.as_manager()

    class Meta:
        verbose_name = 'товар'
        verbose_name_plural = 'товары'

    def __str__(self):
        return self.name


class RestaurantMenuItem(models.Model):
    restaurant = models.ForeignKey(
        Restaurant,
        related_name='menu_items',
        verbose_name="ресторан",
        on_delete=models.CASCADE,
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='menu_items',
        verbose_name='продукт',
    )
    availability = models.BooleanField(
        'в продаже',
        default=True,
        db_index=True
    )

    class Meta:
        verbose_name = 'пункт меню ресторана'
        verbose_name_plural = 'пункты меню ресторана'
        unique_together = [
            ['restaurant', 'product']
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.product.name}"
    

class Order(models.Model):
    ORDER_STATUS = [
        ('raw', 'Необработанный'),
        ('in_progress', 'Отправлен на сборку'),
        ('in_delivery', 'Отправлен на доставку'),
        ('completed', 'Выполнен'),
    ]
    PAYMENT_METHOD = [
        ('cash', 'Наличные'),
        ('online', 'Электронно'),
    ]
    status = models.CharField(
        verbose_name='статус',
        max_length=20,
        choices=ORDER_STATUS,
        default='raw',
        db_index=True,
    )
    comment = models.TextField(
        blank=True,
        null=False,
        verbose_name='комментарий',
    )
    firstname = models.CharField(
        'имя',
        max_length=50
    )
    lastname = models.CharField(
        'фамилия',
        max_length=50
    )
    phonenumber = PhoneNumberField(
        'телефон',
        db_index=True
    )
    address = models.CharField(
        'адрес доставки',
        max_length=255
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD,
        default='не оплачено',
        db_index=True,
        verbose_name='Способ оплаты',
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name="Ресторан",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    registered_at = models.DateTimeField(
        default=timezone.now(),
        blank=True,
        verbose_name='дата создания',
        db_index=True
    )
    called_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='дата звонка',
        db_index=True,
    )
    delivered_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='дата доставки',
        db_index=True,
    )
    objects = OrderQuerySet.as_manager()

    class Meta:
        verbose_name = 'заказ'
        verbose_name_plural = 'заказы'
        ordering = ['-registered_at']

    def save(self, *args, **kwargs):
        if self.restaurant and self.status == 'raw':
            self.status = 'in_progress'
        super().save(*args, **kwargs)
        
    def __str__(self):
        return f'Заказ #{self.id} — {self.firstname} {self.lastname}'
    

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        related_name='items',
        verbose_name='заказ',
        on_delete=models.CASCADE
    )
    product = models.ForeignKey(
        'Product',
        related_name='order_items',
        verbose_name='товар',
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(
        'количество',
        default=1
    )
    price = models.DecimalField(
        'цена за единицу',
        max_digits=8,
        decimal_places=2,
        null=False,
        blank=False,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    


    class Meta:
        verbose_name = 'элемент заказа'
        verbose_name_plural = 'элементы заказа'

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)


