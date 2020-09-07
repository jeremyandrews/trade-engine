import json
from django.urls import reverse
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from spaprofile.models import SpaProfile
from spauser import utils
from spauser.models import SpaUser
from otp.tests import create_totp, totp_login


def view_profile(self, token=None):
    url = reverse('spaprofile:profile-view')
    if token:
        return self.client.get(url, {}, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.get(url, {}, format='json')

def edit_profile(self, token=None, data={}):
    url = reverse('spaprofile:profile-edit')
    if token:
        return self.client.post(url, data, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.post(url, data, format='json')

class SpaProfileTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_view_empty_profile(self):
        """
        View an empty profile
        """
        # Create user.
        utils.create_user(self)

        # Confirm we can't view user profile before logging in.
        response = view_profile(self)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Log in.
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # View the user profile.
        response = view_profile(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['first_name'], None)
        self.assertEqual(content['last_name'], None)
        self.assertEqual(content['date_of_birth'], None)
        self.assertEqual(content['phone_number'], '')
        self.assertEqual(content['country'], '')
        self.assertEqual(content['totp_enabled'], False)

    def test_view_and_edit_profile(self):
        """
        Edit a profile
        """
        data = {
            'first_name': 'first',
            'last_name': 'last',
        }

        # Create user.
        response = utils.create_user(self)

        # Fail to edit name fields if not logged in.
        response = edit_profile(self, data=data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Log in.
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Edit name fields.
        response = edit_profile(self, token=token, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(SpaProfile.objects.count(), 1)
        self.assertEqual(SpaProfile.objects.get().first_name, 'first')


        # View the updated user profile.
        response = view_profile(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['first_name'], 'first')
        self.assertEqual(content['last_name'], 'last')
        self.assertEqual(content['date_of_birth'], None)
        self.assertEqual(content['phone_number'], '')
        self.assertEqual(content['country'], '')

        # Edit country field, leaving name fields.
        response = edit_profile(self, token=token, data={'country': 'US'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # View the updated user profile.
        response = view_profile(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['first_name'], 'first')
        self.assertEqual(content['last_name'], 'last')
        self.assertEqual(content['date_of_birth'], None)
        self.assertEqual(content['phone_number'], '')
        self.assertEqual(content['country'], 'US')

        # Zero out the user profile.
        response = edit_profile(self, token=token, data={'first_name': None, 'last_name': None, 'country': None})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # View the now empty user profile.
        response = view_profile(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['first_name'], None)
        self.assertEqual(content['last_name'], None)
        self.assertEqual(content['date_of_birth'], None)
        self.assertEqual(content['phone_number'], '')
        self.assertEqual(content['country'], '')

        # Fails to set an invalid phone number.
        response = edit_profile(self, token=token, data={'phone_number': 'not-valid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Sets a valid phone number.
        response = edit_profile(self, token=token, data={'phone_number': '+18005551212'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['phone_number'], '+18005551212')

        # Fails to set an invalid date of birth.
        response = edit_profile(self, token=token, data={'date_of_birth': '01-31-1900'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Sets a valid date of birth.
        response = edit_profile(self, token=token, data={'date_of_birth': '1900-01-31'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['date_of_birth'], '1900-01-31')

        # Fails to set an invalid country.
        response = edit_profile(self, token=token, data={'country': 'Nonsuch'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Sets a valid country.
        response = edit_profile(self, token=token, data={'country': 'italy'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['country'], 'IT')

        # There should still only be a single database entry.
        self.assertEqual(SpaProfile.objects.count(), 1)
        self.assertEqual(SpaProfile.objects.get().last_name, None)

    def test_delete_user_profile(self):
        """
        Delete a user and confirm profile gets deleted.
        """
        # Create a user.
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SpaProfile.objects.count(), 1)

        # Log in and delete user.
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = utils.delete_user(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SpaProfile.objects.count(), 0)

        # Create three users.
        response = utils.create_user(self)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = utils.create_user(self, email='b@example.com')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = utils.create_user(self, email='c@example.com')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SpaProfile.objects.count(), 3)

        # Log in and delete only one of the users.
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = utils.delete_user(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(SpaProfile.objects.count(), 2)

    def test_totp_protects_profile(self):
        """
        A user with a verified totp device must validate it before accessing/editing Profile
        """

        # Create and log in user.
        response = utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        nototp_token = content['token']

        # Verify that currently we can view and edit our profile
        response = view_profile(self, token=nototp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = {
            'first_name': 'first',
            'last_name': 'last',
        }
        response = edit_profile(self, token=nototp_token, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Now verify a TOTP device and confirm that we no longer can view/edit without it.
        response = create_totp(self, token=nototp_token)
        totp_token = totp_login(self, SpaUser.objects.get())
        response = view_profile(self, token=nototp_token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = edit_profile(self, token=nototp_token, data=data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Finally, verify we CAN view/edit with a validated TOTP
        response = view_profile(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['totp_enabled'], True)
        response = edit_profile(self, token=totp_token, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
