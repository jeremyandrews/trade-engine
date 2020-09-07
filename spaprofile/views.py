from django.http import JsonResponse
from rest_framework import views, permissions
from rest_framework.response import Response
from rest_framework import status
from django_otp import user_has_device
from django_countries import countries

from .serializers import SpaProfileSerializer
from .models import SpaProfile
from spauser.models import SpaUser
from otp import permissions as totp_permissions


class SpaProfileView(views.APIView):
    """
    Use this endpoint to view a user's profile.
    """
    model = SpaProfile
    serializer_class = SpaProfileSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def get_object(self):
      return SpaUser.objects.get(email=self.request.user.email)

    def get(self, request, format=None):
        user = self.get_object()
        serializer = SpaProfileSerializer(user.spaprofile)
        data = serializer.data
        data['totp_enabled'] = user_has_device(request.user)
        return JsonResponse(data, safe=False)

class SpaProfileEditView(views.APIView):
    """
    Use this endpoint to edit a user's profile.
    """
    model = SpaProfile
    serializer_class = SpaProfileSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def get_object(self):
      return SpaUser.objects.get(email=self.request.user.email)

    def post(self, request, format=None):
        user = self.get_object()
        serializer = SpaProfileSerializer(user.spaprofile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SpaProfileCountriesView(views.APIView):
    """
    Use this endpoint to view a user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(selfself, request, format=None):
        codes = {}
        for code, name in list(countries):
            codes.update({code: name})
        return JsonResponse(codes, safe=False)

