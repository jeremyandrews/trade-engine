# Generated by Django 2.1.7 on 2019-02-24 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('trade', '0004_auto_20190224_0658'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='trade',
            name='base_settled',
        ),
        migrations.RemoveField(
            model_name='trade',
            name='quote_settled',
        ),
        migrations.AddField(
            model_name='trade',
            name='settled',
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
