# Generated by Django 2.1.7 on 2019-02-23 16:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0002_trade_base_volume'),
    ]

    operations = [
        migrations.AddField(
            model_name='trade',
            name='pending',
            field=models.BooleanField(default=False),
        ),
    ]
