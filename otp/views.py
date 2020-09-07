import uuid
from django.http import JsonResponse
from rest_framework import views, permissions
from rest_framework.response import Response
from rest_framework import status
from django_otp import devices_for_user, user_has_device
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from spauser.utils import get_custom_jwt
from . import permissions as otp_permissions


def get_user_totp_device(self, user, confirmed=None):
    devices = devices_for_user(user, confirmed=confirmed)
    for device in devices:
        if isinstance(device, TOTPDevice):
            return device

def get_user_static_device(self, user, confirmed=None):
    devices = devices_for_user(user, confirmed=confirmed)
    for device in devices:
        if isinstance(device, StaticDevice):
            return device

class TOTPCreateView(views.APIView):
    """
    Use this endpoint to set up a new TOTP device
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        device = get_user_totp_device(self, user)
        if not device:
            device = user.totpdevice_set.create(confirmed=False)
        url = device.config_url
        return Response(url, status=status.HTTP_201_CREATED)

class TOTPEnabledView(views.APIView):
    """
    Use this endpoint to check if user has enabled a TOTP device
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, format=None):
        user = request.user
        if user_has_device(user):
            return JsonResponse(True, safe=False)
        else:
            return JsonResponse(False, safe=False)

class TOTPVerifyView(views.APIView):
    """
    Use this endpoint to verify/enable a TOTP device
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token, format=None):
        user = request.user
        device = get_user_totp_device(self, user)
        if not device == None and device.verify_token(token):
            if not device.confirmed:
                device.confirmed = True
                device.save()
            token = get_custom_jwt(user, device)
            return Response({'token': token}, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def test(self, user):
        device = get_user_totp_device(self, user)
        if device:
            device.confirmed = True
            device.save()
            token = get_custom_jwt(user, device)
            return token
        return False

class TOTPDeleteView(views.APIView):
    """
    Use this endpoint to delete a TOTP device
    """
    permission_classes = [permissions.IsAuthenticated, otp_permissions.IsOtpVerified]

    def post(self, request, format=None):
        user = request.user
        devices = devices_for_user(user)
        for device in devices:
            device.delete()
        user.jwt_secret = uuid.uuid4()
        user.save()
        token = get_custom_jwt(user, None)
        return Response({'token': token}, status=status.HTTP_200_OK)

class StaticCreateView(views.APIView):
    """
    Use this endpoint to create static recovery codes.
    """
    permission_classes = [permissions.IsAuthenticated, otp_permissions.IsOtpVerified]
    number_of_static_tokens = 6

    def get(self, request, format=None):
        device = get_user_static_device(self, request.user)
        if not device:
            device = StaticDevice.objects.create(user=request.user, name="Static")

        device.token_set.all().delete()
        tokens = []
        for n in range(self.number_of_static_tokens):
            token = StaticToken.random_token()
            device.token_set.create(token=token)
            tokens.append(token)

        return Response(tokens, status=status.HTTP_201_CREATED)

class StaticVerifyView(views.APIView):
    """
    Use this endpoint to verify a static token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, token, format=None):
        user = request.user
        device = get_user_static_device(self, user)
        if not device == None and device.verify_token(token):
            token = get_custom_jwt(user, device)
            return Response({'token': token}, status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_400_BAD_REQUEST)

    def test(self, user):
        device = get_user_static_device(self, user)
        if device:
            device.confirmed = True
            device.save()
            token = get_custom_jwt(user, device)
            return token
        return False
