import json

from rest_framework import serializers
from blockchain.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'address', 'txid', 'height', 'timestamp', 'value_in', 'from_object',
                  'value_out', 'to_object', 'fee', 'value_unspent', 'created', 'modified')

class TransactionListingSerializer(serializers.ModelSerializer):
    from_object = serializers.SerializerMethodField('decode_from_object')
    to_object = serializers.SerializerMethodField('decode_to_object')

    class Meta:
        model = Transaction
        fields = ('txid', 'height', 'timestamp', 'value_in', 'from_object', 'value_out', 'to_object', 'fee')

    def decode_from_object(self, obj):
        return json.loads(obj.from_object)

    def decode_to_object(self, obj):
        return json.loads(obj.to_object)
