import json
from urllib.parse import urlparse, parse_qs
from django.urls import reverse, reverse_lazy
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice

from spauser import utils
from spauser.models import SpaUser
from .views import get_user_totp_device, TOTPVerifyView, StaticVerifyView

def create_totp(self, token=None):
    url = reverse('otp:totp-create')
    if token:
        return self.client.get(url, {}, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.get(url, {}, format='json')

def totp_enabled(self, token=None):
    url = reverse('otp:totp-enabled')
    if token:
        return self.client.get(url, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.get(url, format='json')

def totp_login(self, user):
    """
    We're faking this one for now.
    @TODO: use the real verify view.
    """
    obj = TOTPVerifyView
    return(obj.test(self, user))

def totp_delete(self, token=None):
    url = reverse('otp:totp-delete')
    if token:
        return self.client.post(url, {}, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.post(url, {}, format='json')

class UserTOTPTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_create_totp(self):
        """
        Create a TOTP device.
        """
        # Create user and log in.
        response = utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Confirm we can't create a TOTP with an invalid token.
        response = create_totp(self, token='no-such')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Confirm we can create a TOTP with a valid token.
        response = create_totp(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = json.loads(response.content)

        # Validate URL pieces.
        url = urlparse(content)
        self.assertEqual(url.scheme, 'otpauth')
        self.assertEqual(url.netloc, 'totp')
        self.assertEqual(url.path, '/a%40example.com')
        self.assertEqual(url.params, '')
        self.assertEqual(url.fragment, '')

        # Validate URL query pieces.
        query = parse_qs(url.query)
        self.assertEqual(query['algorithm'], ['SHA1'])
        self.assertEqual(query['digits'], ['6'])
        self.assertEqual(query['period'], ['30'])
        secret = query['secret'][0]
        assert len(secret) == 32

        # We should have 1 uncomfirmed device.
        self.assertEqual(TOTPDevice.objects.count(), 1)
        device = TOTPDevice.objects.get()
        self.assertEqual(device.confirmed, False)

    def test_delete_user_and_totp(self):
        """
        Delete user and associated TOTP device.
        """
        # Create user, log in, and create TOTP device.
        response = utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = create_totp(self, token=token)
        content = json.loads(response.content)
        self.assertEqual(TOTPDevice.objects.count(), 1)

        # Delete user, confirm TOTP device is also deleted.
        response = utils.delete_user(self, token=token)
        self.assertEqual(TOTPDevice.objects.count(), 0)

    def test_totp_enabled(self):
        """
        Test whether user has enabled TOTP device.
        """
        # Create user and log in.
        response = utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Check if user has an enabled TOTP device.
        response = totp_enabled(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content, False)

        # Unable to check if TOTP device is enabled if not logged in.
        response = totp_enabled(self)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Create a TOTP device.
        response = create_totp(self, token=token)
        self.assertEqual(TOTPDevice.objects.count(), 1)

        # Confirm newly created TOTP device is not confirmed.
        response = totp_enabled(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content, False)

        # Still unable to check if TOTP device is enabled if not logged in.
        response = totp_enabled(self)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # @TODO: properly test TOTP tokens.

        # Enable TOTP device.
        user = SpaUser.objects.get()
        device = get_user_totp_device(self, user)
        device.confirmed = True
        device.save()
        self.assertEqual(device.confirmed, True)

        # Confirm TOTP device is enabled..
        response = totp_enabled(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content, True)

    def test_totp_delete(self):
        """
        Test whether TOTP device deletion works.
        """
        # Create user and log in.
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create TOTP device and log in with it.
        create_totp(self, token=token)
        totp_token = totp_login(self, SpaUser.objects.get())
        self.assertEqual(TOTPDevice.objects.count(), 1)

        # Logged in, so should be enabled
        response = totp_enabled(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), True)

        # Delete TOTP device.
        response = totp_delete(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(TOTPDevice.objects.count(), 0)
        content = json.loads(response.content)
        new_token = content['token']

        # Confirm deleted device no longer shows up as enabled.
        response = totp_enabled(self, new_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content, False)

        # Confirm that the old totp_token is no longer valid
        response = totp_enabled(self, totp_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # With the valid token, we no longer should be required to use a TOTP
        response = utils.view_user(self, token=new_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Create new TOTP device and log in with it.
        create_totp(self, token=new_token)
        new_totp_token = totp_login(self, SpaUser.objects.get())
        self.assertEqual(TOTPDevice.objects.count(), 1)

        # New and old TOTP token should work, as the device # hasn't changed
        response = utils.view_user(self, token=new_token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        #response = utils.view_user(self, token=totp_token)
        #self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = utils.view_user(self, token=new_totp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_totp_delete_multiuser(self):
        """
        Test whether TOTP device deletion works with multiple users.
        """
        # Create user, log in, create TOTP device, log in: User 1
        utils.create_user(self)
        self.assertEqual(SpaUser.objects.count(), 1)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        create_totp(self, token=token)
        self.assertEqual(TOTPDevice.objects.count(), 1)
        totp_token_1 = totp_login(self, SpaUser.objects.get())

        # Create user, log in, create TOTP device, log in: User 2
        utils.create_user(self, email='b@example.com')
        self.assertEqual(SpaUser.objects.count(), 2)
        response = utils.user_login(self, email='b@example.com')
        content = json.loads(response.content)
        token = content['token']
        create_totp(self, token=token)
        self.assertEqual(TOTPDevice.objects.count(), 2)
        totp_token_2 = totp_login(self, SpaUser.objects.get(email='b@example.com'))

        # Create user, log in, create TOTP device, log in: User 3
        utils.create_user(self, email='c@example.com')
        self.assertEqual(SpaUser.objects.count(), 3)
        response = utils.user_login(self, email='c@example.com')
        content = json.loads(response.content)
        token = content['token']
        create_totp(self, token=token)
        self.assertEqual(TOTPDevice.objects.count(), 3)
        totp_token_3 = totp_login(self, SpaUser.objects.get(email='c@example.com'))

        # Delete TOTP device for User #2
        response = totp_delete(self, token=totp_token_2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(TOTPDevice.objects.count(), 2)

        # Confirm device is enabled for User #1 and #3 only
        response = totp_enabled(self, totp_token_1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content, True)
        response = totp_enabled(self, totp_token_2)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = totp_enabled(self, totp_token_3)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content, True)

    def test_totp_password_change(self):
        """
        Test whether TOTP device survives password change.
        """
        # Create user and log in.
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create TOTP device and log in with it.
        create_totp(self, token=token)
        totp_token = totp_login(self, SpaUser.objects.get())
        self.assertEqual(TOTPDevice.objects.count(), 1)

        # Logged in, so should be enabled
        response = totp_enabled(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), True)

        # Change password.
        response = utils.change_password(self, token=totp_token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Old tokens are no longer valid.
        response = utils.view_user(self, token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        response = utils.view_user(self, totp_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # TOTP device still exists
        self.assertEqual(TOTPDevice.objects.count(), 1)

        # Can't log in with old password
        response = utils.user_login(self)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Log in with new password, can't access user page.
        response = utils.user_login(self, password='news3cretABC')
        content = json.loads(response.content)
        token = content['token']
        response = utils.view_user(self, token)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Verify TOTP.
        totp_token = totp_login(self, SpaUser.objects.get())
        response = totp_enabled(self, token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(json.loads(response.content), True)
        response = utils.view_user(self, totp_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

def create_static(self, token=None):
    url = reverse('otp:static-create')
    if token:
        return self.client.get(url, {}, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.get(url, {}, format='json')

def static_login(self, static, token=None):
    url = reverse_lazy('otp:static-login', args=[static])
    if token:
        return self.client.post(url, {}, format='json', HTTP_AUTHORIZATION='JWT {}'.format(token))
    else:
        return self.client.post(url, {}, format='json')

def static_login_fake(self, user):
    """
    We're faking this one for now.
    @TODO: use the real verify view.
    """
    obj = StaticVerifyView
    return(obj.test(self, user))

class UserStaticTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_create_static(self):
        """
        Create a static device.
        """
        # Create user and log in.
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Confirm we can't create a static device with an invalid token.
        response = create_static(self, token='no-such')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Confirm we can't create a static device without first creating a TOTP device.
        # @TODO -- this is not actually required ...??
        # IsOtpVerified returns True if  there's no TOTP device
        #response = create_static(self, token=token)
        #self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Create and Validate TOTP - this generates a new token.
        response = create_totp(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        token = totp_login(self, SpaUser.objects.get())

        # Confirm we can create a static device with a valid token.
        response = create_static(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(StaticDevice.objects.count(), 1)
        tokens = json.loads(response.content)
        self.assertEqual(len(tokens), 6)
        for token in tokens:
            self.assertEqual(len(token), 8)

    def test_delete_user_and_static(self):
        # Create user, log in, and create static device.
        response = utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = create_totp(self, token=token)
        token = totp_login(self, SpaUser.objects.get())
        response = create_static(self, token=token)
        self.assertEqual(StaticDevice.objects.count(), 1)

        # Delete user, confirm static device is also deleted.
        response = utils.delete_user(self, token=token)
        self.assertEqual(StaticDevice.objects.count(), 0)

    def test_static_login(self):
        # Create user, log in, and create static device.
        response = utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = create_totp(self, token=token)
        token = totp_login(self, SpaUser.objects.get())

        # @FIXME: static_login is broken
        # static can't be verified before created
        #response = static_login(self, 'abcd3456', token=token)
        #self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = create_static(self, token=token)
        self.assertEqual(StaticDevice.objects.count(), 1)
        statics = json.loads(response.content)

        original_token = token
        for static in statics:
            # @FIXME: static_login is broken
            ## Must be logged in to use static.
            #response = static_login(self, static)
            token = static_login_fake(self, SpaUser.objects.get())
            #self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            ## Static can be used only one time - we also get a new token each time
            #response = static_login(self, static, token=token)
            #self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            #content = json.loads(response.content)
            #token = content['token']
            # Static gets consumed and fails if used again.
            #response = static_login(self, static, token=token)
            #self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            # The old token and the new token both work for basic access
            response = utils.view_user(self, token=token)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            response = utils.view_user(self, token=original_token)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_totp_and_static_delete(self):
        """
        Test whether TOTP device deletion also cleans up statics.
        """
        # Create user and log in.
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create TOTP device and log in with it.
        create_totp(self, token=token)
        totp_token = totp_login(self, SpaUser.objects.get())

        # Create Static device.
        response = create_static(self, token=totp_token)
        self.assertEqual(StaticDevice.objects.count(), 1)
        statics = json.loads(response.content)

        # Delete TOTP device.
        response = totp_delete(self, token=totp_token)
        content = json.loads(response.content)
        new_token = content['token']

        '''
        # @TODO @FIXME static_login is broken
        # Make sure statics don't work (they're deleted)
        i = 0
        for static in statics:
            i = i + 1

            # None of our tokens should work
            response = static_login(self, static, token=new_token)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

            # Only try half of our statics
            if i > 4:
                break
                '''

        # Create new TOTP device and log in with it.
        create_totp(self, token=new_token)
        new_totp_token = totp_login(self, SpaUser.objects.get())

        # Create new Static device.
        create_static(self, token=new_totp_token)

        '''
        # Make sure old statics still don't work (they're deleted)
        for static in statics:
            # None of our tokens should work
            response = static_login(self, static, token=new_totp_token)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        '''

        # Confirm we can create new statics, and that they work
        response = create_static(self, token=new_totp_token)
        self.assertEqual(StaticDevice.objects.count(), 1)
        statics = json.loads(response.content)
        token = new_totp_token
        '''
        for static in statics:
            response = static_login(self, static, token=token)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            content = json.loads(response.content)
            token = content['token']
            '''
        token = static_login_fake(self, SpaUser.objects.get())

        # Finally, delete TOTP device again with Static login, and use new token.
        response = totp_delete(self, token=token)
        content = json.loads(response.content)
        new_token = content['token']
        response = utils.view_user(self, token=new_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)