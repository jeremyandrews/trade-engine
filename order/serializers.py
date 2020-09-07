import datetime

from rest_framework import serializers
from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    # Convert UUID id and wallet fields to String so it can be JSON encoded
    id = serializers.CharField(read_only=True)
    created = serializers.SerializerMethodField('convert_created_to_timestamp')
    modified = serializers.SerializerMethodField('convert_modified_to_timestamp')
    timeinforce = serializers.SerializerMethodField('convert_timeinforce_to_timestamp')

    class Meta:
        model = Order
        fields = ('id', 'wallet', 'label', 'description', 'cryptopair', 'base_currency', 'quote_currency', 'side',
                  'limit_price', 'volume', 'original_volume', 'fee', 'timeinforce', 'open', 'canceled', 'filled',
                  'created', 'modified')

    def convert_created_to_timestamp(self, obj):
        return int(obj.created.replace(tzinfo=datetime.timezone.utc).timestamp())

    def convert_modified_to_timestamp(self, obj):
        return int(obj.modified.replace(tzinfo=datetime.timezone.utc).timestamp())

    def convert_timeinforce_to_timestamp(self, obj):
        if obj.timeinforce:
            return int(obj.timeinforce.replace(tzinfo=datetime.timezone.utc).timestamp())
        else:
            return obj.timeinforce
