from django_countries.serializers import CountryFieldMixin

from rest_framework import serializers

from .models import SpaProfile


class SpaProfileSerializer(CountryFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = SpaProfile
        fields = ('first_name', 'last_name', 'date_of_birth', 'phone_number', 'country')
