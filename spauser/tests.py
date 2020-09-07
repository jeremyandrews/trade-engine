import json

from django.core.cache import cache

from rest_framework import status
from rest_framework.test import APITestCase

from .models import SpaUser
from . import utils
from otp.tests import create_totp, totp_login

class SpaUserTests(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_create_user(self):
        """
        Create a user.
        """
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SpaUser.objects.count(), 1)
        self.assertEqual(SpaUser.objects.get().email, 'a@example.com')

    def test_no_create_user_duplicate_email(self):
        """
        Try and create the same user twice.
        """
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # try and create the same user twice in a row
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_create_user_no_password(self):
        """
        Try and create a user without a password.
        """
        response = utils.create_user(self, password=None)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_available(self):
        """
        Test email is available before creating user.
        """
        response = utils.is_available(self)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = utils.is_available(self)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_user_and_login(self):
        """
        Create a user.
        """
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = utils.user_login(self)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        assert 'token' in content
        token = content['token']
        assert len(token) == 296

        # Can't view user details with submitting token.
        response = utils.view_user(self, None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Can't view user details with submitting wrong token.
        response = utils.view_user(self, 'not-a-valid-token')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Can view user details with submitting right token.
        response = utils.view_user(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        assert 'id' in content
        assert 'email' in content
        assert 'username' not in content
        self.assertIsNotNone(content['id'])
        assert content['email'] == 'a@example.com'

    def test_delete_user(self):
        """
        Create a user.
        """
        # Create a user.
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SpaUser.objects.count(), 1)

        # Try and delete without logging in.
        response = utils.delete_user(self)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Log in and delete user.
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = utils.delete_user(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SpaUser.objects.count(), 0)

    def test_change_password(self):
        """
        Change user password.
        """
        # Create a user and log in.
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SpaUser.objects.count(), 1)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Change password.
        response = utils.change_password(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Old token is no longer valid.
        response = utils.view_user(self, token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Can't log in with old password
        response = utils.user_login(self)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Log in with new password.
        response = utils.user_login(self, password='news3cretABC')
        content = json.loads(response.content)
        token = content['token']
        response = utils.view_user(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_totp_protects_user(self):
        """
        A user with a verified totp device must validate it before viewing self
        """

        # Create and log in user.
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        nototp_token = content['token']

        # Verify that currently we can view self
        response = utils.view_user(self, token=nototp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now verify a TOTP device and confirm that we no longer can view self
        create_totp(self, token=nototp_token)
        totp_token = totp_login(self, SpaUser.objects.get())
        response = utils.view_user(self, token=nototp_token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Finally, verify we CAN view with a validated TOTP
        response = utils.view_user(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_logout(self):
        """
        Confirming once a user logs out, all their tokens are invalidated.
        """
        # Create user and log in.
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        nototp_token = content['token']
        response = utils.view_user(self, token=nototp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Also create a TOTP session for the user.
        create_totp(self, token=nototp_token)
        totp_token = totp_login(self, SpaUser.objects.get())
        response = utils.view_user(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Log out the user
        response = utils.user_logout(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # We should not have access to view the user with either token.
        response = utils.view_user(self, token=nototp_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = utils.view_user(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
