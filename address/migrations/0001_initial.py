# Generated by Django 2.1.1 on 2018-09-27 12:38

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('wallet', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('label', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True, null=True)),
                ('p2pkh', models.CharField(editable=False, max_length=200)),
                ('bech32', models.CharField(blank=True, editable=False, max_length=2048, null=True)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('secret_exponent', models.CharField(blank=True, editable=False, max_length=200, null=True)),
                ('wif', models.CharField(blank=True, editable=False, max_length=200, null=True)),
                ('passphrase', models.CharField(blank=True, editable=False, max_length=2048, null=True)),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='wallet.Wallet')),
            ],
        ),
    ]
