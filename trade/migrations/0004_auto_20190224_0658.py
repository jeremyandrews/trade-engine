# Generated by Django 2.1.7 on 2019-02-24 06:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0003_trade_pending'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trade',
            name='pending',
        ),
        migrations.RemoveField(
            model_name='trade',
            name='settled',
        ),
        migrations.AddField(
            model_name='trade',
            name='base_settled',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='trade',
            name='quote_settled',
            field=models.SmallIntegerField(default=0),
        ),
    ]
