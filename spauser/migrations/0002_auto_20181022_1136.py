# Generated by Django 2.1.2 on 2018-10-22 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('spauser', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='spauser',
            name='mnemonic',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
        migrations.AddField(
            model_name='spauser',
            name='seed',
            field=models.CharField(blank=True, max_length=128, null=True),
        ),
    ]
