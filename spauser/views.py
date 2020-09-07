import uuid
from django.conf import settings
from django.contrib.auth import user_logged_out
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import APIException
from rest_framework_jwt.views import RefreshJSONWebToken
from djoser.views import UserView, UserDeleteView, SetUsernameView, SetPasswordView
from djoser import serializers
from djoser.conf import settings as djoser_settings

from spauser.models import SpaUser
from otp import permissions as otp_permissions
from spauser.serializers import SpaUserRefreshJSONWebTokenSerializer


class SpaUserEmailView(views.APIView):
    """
    Use this endpoint to test if an email address can be used.
    """
    model = settings.AUTH_USER_MODEL
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        if 'email' not in request.data:
            raise APIException('The email field is required.')
        email = request.data["email"]
        if SpaUser.objects.filter(email=email).exists():
            return Response(status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_202_ACCEPTED)

class SpaUserLogoutAllView(views.APIView):
    """
    Use this endpoint to log out all sessions for a given user.
    """
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, *args, **kwargs):
        user = request.user
        user.jwt_secret = uuid.uuid4()
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SpaUserView(UserView):
    """
    Uses the default Djoser view, but add the IsOtpVerified permission.
    Use this endpoint to retrieve/update user.
    """
    model = SpaUser
    serializer_class = serializers.UserSerializer
    permission_classes = [permissions.IsAuthenticated, otp_permissions.IsOtpVerified]

class SpaUserDeleteView(UserDeleteView):
    """
    Uses the default Djoser view, but add the IsOtpVerified permission.
    Use this endpoint to remove actually authenticated user.
    """
    serializer_class = serializers.UserDeleteSerializer
    permission_classes = [permissions.IsAuthenticated, otp_permissions.IsOtpVerified]

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        instance.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

class SpaUserSetUsernameView(SetUsernameView):
    """
    Uses the default Djoser view, but add the IsOtpVerified permission.
    Use this endpoint to change user username.
    """
    permission_classes = [permissions.IsAuthenticated, otp_permissions.IsOtpVerified]

class SpaUserSetPasswordView(SetPasswordView):
    """
    Use this endpoint to change user password.
    """
    permission_classes = [permissions.IsAuthenticated, otp_permissions.IsOtpVerified]

    def get_serializer_class(self):
        if djoser_settings.SET_PASSWORD_RETYPE:
            return djoser_settings.SERIALIZERS.set_password_retype
        return djoser_settings.SERIALIZERS.set_password

    def _action(self, serializer):
        self.request.user.set_password(serializer.data['new_password'])
        self.request.user.save()

        if djoser_settings.LOGOUT_ON_PASSWORD_CHANGE:
            user_logged_out.send(
                sender=self.request.user.__class__, request=self.request, user=self.request.user
            )

        return Response(status=status.HTTP_204_NO_CONTENT)

class SpaUserRefreshJSONWebToken(RefreshJSONWebToken):
    """
    API View that returns a refreshed token (with new expiration) based on
    existing token

    Override the Django REST Framework JWT implementation.

    If 'orig_iat' field (original issued-at-time) is found, will first check
    if it's within expiration window, then copy it to the new token
    """
    serializer_class = SpaUserRefreshJSONWebTokenSerializer
