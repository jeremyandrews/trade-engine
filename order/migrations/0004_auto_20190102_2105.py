# Generated by Django 2.1.2 on 2019-01-02 21:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('order', '0003_auto_20190102_1117'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='limit',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='order',
            name='original_volume',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='order',
            name='volume',
            field=models.BigIntegerField(default=0),
        ),
    ]
