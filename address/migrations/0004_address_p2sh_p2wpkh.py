# Generated by Django 2.1.2 on 2018-12-22 07:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('address', '0003_auto_20181023_0634'),
    ]

    operations = [
        migrations.AddField(
            model_name='address',
            name='p2sh_p2wpkh',
            field=models.CharField(blank=True, editable=False, max_length=200, null=True),
        ),
    ]