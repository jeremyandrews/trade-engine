# Generated by Django 2.1.2 on 2018-10-22 05:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wallet', '0003_auto_20181021_2100'),
    ]

    operations = [
        migrations.AddField(
            model_name='wallet',
            name='last_index',
            field=models.IntegerField(default=0),
        ),
    ]
