import json

from django.conf import settings
from rest_framework import views, permissions
from rest_framework.response import Response
from rest_framework import status
import requests

from .serializers import AddressSerializer
from .models import Address
from otp import permissions as totp_permissions
import address.utils
import blockchain.utils
import wallet.utils


class AddressCreateView(views.APIView):
    """
    Use this endpoint to create a new address within a wallet.

    Limitation: currently this assumes the user only has one wallet per currency.
    """
    model = Address
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def post(self, request, format=None):
        # Verify that a wallet_id has been passed in, where we can create our address.
        wallet_id, success = wallet.utils.get_wallet_id(request)
        if success != True:
            # If status code is set, then wallet_id is a JSON-formatted error: abort!
            return Response(wallet_id, status=success)

        # Be sure the wallet exists and the user has access to it.
        user_wallet, success = wallet.utils.get_wallet(user_id=self.request.user.id, wallet_id=wallet_id)
        if success is not True:
            return Response(user_wallet, status=success)

        if not user_wallet.private_key:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data = {
                "status": "wallet missing private key",
                "code": status_code,
                "debug": {
                    "wallet_id": user_wallet.id,
                },
                "data": {
                    "coin": settings.COINS[user_wallet.currencycode]['name'],
                    "symbol": user_wallet.currencycode,
                },
            }
            return Response(data, status=status_code)

        new_address, index = address.utils.get_new_address(user_wallet=user_wallet, is_change=False)
        # If index is False,
        if new_address is False:
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "invalid data",
                "code": status_code,
                "debug": {
                    "request": self.request.data,
                    "symbol": user_wallet.currencycode,
                },
                "data": {
                },
            }
            return Response(data, status=status_code)

        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            # Manually add the rest of the data to the object
            try:
                db_address = Address.objects.get(wallet_id=user_wallet.id, p2pkh=new_address['p2pkh'])
                # Address is already in wallet
                status_message = "address already exists"
            except:
                serializer.validated_data['wallet_id'] = user_wallet.id
                serializer.validated_data['p2pkh'] = new_address['p2pkh']
                serializer.validated_data['p2sh_p2wpkh'] = new_address['p2sh_p2wpkh']
                serializer.validated_data['bech32'] = new_address['bech32']
                serializer.validated_data['index'] = new_address['index']
                serializer.validated_data['is_change'] = False
                db_address = serializer.save()
                status_message = "address created"

            # Build a smaller dictionary which we expose through the API.
            # @TODO: this should be a serializer
            new_address = {
                'id': db_address.id,
                'label': db_address.label,
                'description': db_address.description,
                'p2pkh': new_address['p2pkh'],
                'p2sh_p2wpkh': new_address['p2sh_p2wpkh'],
                'bech32': new_address['bech32'],
                'index': new_address['index'],
                'is_change': False,
                'wallet_id': user_wallet.id,
                "coin": settings.COINS[user_wallet.currencycode]['name'],
                "symbol": user_wallet.currencycode,
            }
            status_code = status.HTTP_200_OK
            data = {
                "status": status_message,
                "code": status_code,
                "debug": {
                },
                "data": new_address,
            }
            return Response(data, status=status_code)
        else:
            # Invalid data provided.
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "invalid data",
                "code": status_code,
                "debug": {
                    "request": request.data,
                    "errors": serializer.errors,
                },
                "data": {
                },
            }
            return Response(data, status=status_code)
