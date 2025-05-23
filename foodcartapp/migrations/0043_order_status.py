# Generated by Django 4.2.20 on 2025-05-07 08:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('foodcartapp', '0042_alter_orderitem_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('raw', 'Необработанный'), ('confirmed', 'Подтверждён'), ('assembling', 'Собирается'), ('delivering', 'Доставляется'), ('done', 'Выполнен')], db_index=True, default='raw', max_length=20, verbose_name='статус'),
        ),
    ]
