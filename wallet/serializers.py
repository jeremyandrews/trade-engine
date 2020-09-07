from rest_framework import serializers
from django.conf import settings

from wallet.models import Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'label', 'description', 'currencycode', 'created', 'modified')

    def validate_label(self, value):
        """
        For now we require that the label always be "default".

        At a later time we will support multiple wallets per user, and will remove this requirement.
        """
        # @TODO: remove this to support multiple wallets.
        if value not in ['default']:
            # ValidationError results in a 400 error
            raise serializers.ValidationError("Label must be 'default'")
        return value

    def validate_currencycode(self, value):
        """
        Check that the currencycode is one we currently support.
        """
        # @TODO: get supported currency codes from configuration.
        if value not in settings.COINS:
            # ValidationError results in a 400 error
            raise serializers.ValidationError("Unrecognized currency code")
        return value
