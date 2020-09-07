import uuid
from calendar import timegm
from datetime import datetime

from django.urls import reverse

from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework_jwt.utils import jwt_decode_handler
from rest_framework_jwt.compat import get_username, get_username_field
from rest_framework_jwt.settings import api_settings

from django_otp.models import Device


def get_custom_jwt(user, device):
    """
    Helper to generate a JWT for a validated OTP device.
    This resets the orig_iat timestamp, as we've re-validated the user.
    :param user: APIUser
    :param device: OTP Device (TOTP or Static)
    :return: JWT token
    """
    jwt_encode_handler = api_settings.JWT_ENCODE_HANDLER

    payload = jwt_otp_payload(user, device)
    return jwt_encode_handler(payload)

def otp_is_verified(self, request):
    """
    Helper to determine if user has verified OTP.
    :param self:
    :param request:
    :return: TRUE or FALSE
    """
    auth = JSONWebTokenAuthentication()
    jwt_value = auth.get_jwt_value(request)
    if jwt_value is None:
        return False

    payload = jwt_decode_handler(jwt_value)
    persistent_id = payload.get('otp_device_id')

    if persistent_id:
        device = Device.from_persistent_id(persistent_id)
        if (device is not None) and (device.user_id != request.user.id):
            return False
        else:
            # Valid device in JWT
            return True
    else:
        return False

def jwt_otp_payload(user, device = None):
    """
    Optionally include OTP device in JWT payload
    :param user:
    :param device: TOTP or Static
    :return: JWT payload object
    """
    username_field = get_username_field()
    username = get_username(user)

    payload = {
        'user_id': user.pk,
        'username': username,
        'exp': datetime.utcnow() + api_settings.JWT_EXPIRATION_DELTA
    }
    if isinstance(user.pk, uuid.UUID):
        payload['user_id'] = str(user.pk)

    payload[username_field] = username

    # Include original issued at time for a brand new token,
    # to allow token refresh
    if api_settings.JWT_ALLOW_REFRESH:
        payload['orig_iat'] = timegm(
            datetime.utcnow().utctimetuple()
        )

    if api_settings.JWT_AUDIENCE is not None:
        payload['aud'] = api_settings.JWT_AUDIENCE

    if api_settings.JWT_ISSUER is not None:
        payload['iss'] = api_settings.JWT_ISSUER

    # UserAPI additions
    if (user is not None) and (device is not None) and (device.user_id == user.id) and (device.confirmed is True):
        payload['otp_device_id'] = device.persistent_id
    else:
        payload['otp_device_id'] = None

    return payload

def get_data(self, email='a@example.com', password='s3cretABC'):
    return {
        'email': email,
        'password': password,
    }

def create_user(self, email='a@example.com', password='s3cretABC'):
    """
    Helper to create a user.
    """
    data = get_data(self, email, password)
    url = reverse('spauser:user-create')
    return self.client.post(url, data=data, format='json')

def client_get_optional_jwt(self, url, token=None, data={}):
    if token:
        return self.client.get(url, data=data, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.get(url, data=data, format='json')

def client_post_optional_jwt(self, url, token=None, data={}):
    if token:
        return self.client.post(url, data=data, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.post(url, data=data, format='json')

def view_user(self, token=None):
    """
    Helper to view a user.
    """
    url = reverse('spauser:user-view')
    return client_get_optional_jwt(self, url=url, token=token)

def user_logout(self, token=None):
    """
    Helper to log a user out.
    """
    url = reverse('spauser:user-logout-all')
    return client_post_optional_jwt(self, url=url, token=token)

def delete_user(self, token=None):
    """
    Helper to delete a user.
    """
    url = reverse('spauser:user-delete')
    data = {
        'current_password': 's3cretABC',
    }
    return client_post_optional_jwt(self, url=url, token=token, data=data)

def is_available(self, email='a@example.com'):
    url = reverse('spauser:email-available')
    data = {
        'email': email,
    }
    return self.client.post(url, data=data, format='json')

def user_login(self, email='a@example.com', password='s3cretABC'):
    """
    Helper to create JWT.
    """
    data = get_data(self, email, password)
    url = reverse('spauser:user-login')
    return self.client.post(url, data=data, format='json')

def change_password(self, current_password='s3cretABC', new_password='news3cretABC', token=None):
    """
    Helper to change password.
    """
    url = reverse('spauser:user-edit-password')
    data = {
        'current_password': current_password,
        'new_password': new_password,
    }
    return client_post_optional_jwt(self, url=url, token=token, data=data)
