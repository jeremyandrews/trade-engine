import datetime

from rest_framework import serializers
from .models import Trade


class TradeSerializer(serializers.ModelSerializer):
    created = serializers.SerializerMethodField('convert_created_to_timestamp')
    modified = serializers.SerializerMethodField('convert_modified_to_timestamp')

    class Meta:
        model = Trade
        fields = ('id', 'buy_order', 'buy_order_settled_in',
                  'buy_order_settled_out', 'sell_order', 'sell_order_settled_in',
                  'sell_order_settled_out', 'cryptopair', 'label', 'description',
                  'price', 'volume', 'base_volume', 'buy_fee', 'sell_fee',
                  'created', 'modified')

    def convert_created_to_timestamp(self, obj):
        return int(obj.created.replace(tzinfo=datetime.timezone.utc).timestamp())

    def convert_modified_to_timestamp(self, obj):
        return int(obj.modified.replace(tzinfo=datetime.timezone.utc).timestamp())

class ReportingTradeSerializer(serializers.ModelSerializer):
    amount = serializers.IntegerField(source='volume')
    date = serializers.SerializerMethodField('convert_created_to_timestamp')

    class Meta:
        model = Trade
        fields = ('id', 'price', 'amount', 'date')

    def convert_created_to_timestamp(self, obj):
        return int(obj.created.replace(tzinfo=datetime.timezone.utc).timestamp())
