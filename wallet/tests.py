import json
import random
from pprint import pprint

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from django.shortcuts import get_object_or_404

from spauser.models import SpaUser
from address.models import Address
from wallet.models import Wallet
import blockchain.utils
import spauser.utils
import wallet.utils

def load_addresses_into_wallet(self, wallet_id, public_addresses, change_addresses):
    # Load pre-generated addresses so we can actually send funds
    for index, address_to_add in enumerate(public_addresses):
        known_address = Address(label='test address, index %d' % index, p2pkh=address_to_add,
                                wallet_id=wallet_id, index=index, is_change=False)
        known_address.save()
    self.assertEqual(Address.objects.count(), len(public_addresses))

    # Load pre-generated change addresses so we don't lose sent-funds
    for index, address_to_add in enumerate(change_addresses):
        known_address = Address(label='test address, index %d' % index, p2pkh=address_to_add,
                                wallet_id=wallet_id, index=index, is_change=True)
        known_address.save()
    self.assertEqual(Address.objects.count(), len(public_addresses) + len(change_addresses))

def generate_output(self, public_addresses, balance):
    output = {}
    total_send_amount = 0
    for _ in range(0, random.randint(1, 8)):
        send_to = public_addresses[random.randint(0, len(public_addresses) - 1)]
        send_amount = random.randint(2500, 250000)
        if send_to not in output:
            total_send_amount += send_amount
            output[send_to] = send_amount
    #print("sending %d to %d addresses" % (total_send_amount, len(output)))
    self.assertGreaterEqual(balance, total_send_amount)
    return output

class WalletTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_wallet_creation(self):
        """
        Verify basic wallet creation.
        """
        # Create first user.
        self.assertEqual(SpaUser.objects.count(), 0)
        spauser.utils.create_user(self)
        self.assertEqual(SpaUser.objects.count(), 1)

        # Can't create a wallet without first logging in.
        response = wallet.utils.create_wallet(self)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Log in.
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Wallet seed requires passphrase.
        response = wallet.utils.create_wallet_seed(self, token=token, data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'passphrase is required')

        # Unable to create a wallet without first creating a seed.
        self.assertEqual(Wallet.objects.count(), 0)
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'invalid passphrase')
        self.assertEqual(Wallet.objects.count(), 0)

        # Create a wallet seed.
        response = wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        # You must create a wallet seed before you can create wallets. The same seed is used for all wallets.
        '''
        {'code': 200,
         'data': {},
         'debug': {'mnemonic': 'volcano conduct tooth snake volcano raccoon mean cat '
                               'draft sunny point click dial earn boil voyage grit fee '
                               'height offer blush train ramp table',
                   'passphrase': 'thisISs3cured00d!',
                   'salt': 'k-PD3RpqL7R5g_6LPj5k84QbFX3BiNIDeDFKuIMydKK2IPNd_fa5J9PVSqLgb0tn'},
         'status': 'seed created'}
        '''
        self.assertEqual(content['status'], 'seed created')

        response = wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        # Attempting to create a wallet seed multiple times has no affect: once the seed is created, that's the seed
        # the user uses.
        '''
        {'code': 200,
         'data': {},
         'debug': {'mnemonic': 'volcano conduct tooth snake volcano raccoon mean cat '
                               'draft sunny point click dial earn boil voyage grit fee '
                               'height offer blush train ramp table',
                   'passphrase': 'thisISs3cured00d!',
                   'salt': 'k-PD3RpqL7R5g_6LPj5k84QbFX3BiNIDeDFKuIMydKK2IPNd_fa5J9PVSqLgb0tn'},
         'status': 'seed already created'}
        '''
        self.assertEqual(content['status'], 'seed already created')

        # Create a wallet.
        self.assertEqual(Wallet.objects.count(), 0)
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(Wallet.objects.count(), 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'coin': 'bitcoin',
                  'description': None,
                  'id': '201923f7-4909-41dd-b180-79e994bd654f',
                  'label': 'default',
                  'symbol': 'BTC'},
         'debug': {'created': '2019-01-15T09:39:13.691904Z',
                   'last_change_index': 0,
                   'last_external_index': 0,
                   'modified': '2019-01-15T09:39:14.124032Z',
                   'private_key': 'xprv9ywMy9MBnUhe5XXtEK6ki42prfzfvozUM5Dcu2qmtYJxro8EW6CUToZ7uMz5GxX5tFCZs2qTxcrqY2CrSB8zEkVi3SCdLcTUtQvJkLfyUqF',
                   'public_key': 'xpub6CviNet5crFwJ1cMLLdm5ByZQhqALGiKiJ9DhRFPSsqwjbTP3dWj1bsbkdxxFtBXWaQE33mbVYTao8whXKuZ3pnd16saP7BdBGnDWm1F4A3'},
         'status': 'wallet created'}
        '''
        self.assertEqual(content['data']['label'], 'default')
        self.assertEqual(content['data']['description'], None)
        self.assertEqual(content['data']['symbol'], 'BTC')
        self.assertEqual(content['data']['coin'], 'bitcoin')

    def test_one_wallet_per_user(self):
        '''
        Verify that each user only gets one wallet.
        '''
        # Create first user and log in.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet seed.
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})

        # Create one wallet.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.count(), 1)

        # Fail to create a second wallet.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        self.assertEqual(Wallet.objects.count(), 1)

        # Log in again as the same user, fail to create a second wallet with a fresh token.
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        self.assertEqual(Wallet.objects.count(), 1)

        # Create second user and log in.
        spauser.utils.create_user(self, email='b@example.com')
        response = spauser.utils.user_login(self, email='b@example.com')
        content = json.loads(response.content)
        token2 = content['token']

        # Create wallet for second user.
        wallet.utils.create_wallet_seed(self, token=token2, data={'passphrase': 'thisISs3cured00d!'})
        response = wallet.utils.create_wallet(self, token=token2, data={'label': 'default', 'currencycode': 'BTC',
                                                           'passphrase': 'thisISs3cured00d!'})
        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.count(), 2)

        # Fail to create a second wallet for either user
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        self.assertEqual(Wallet.objects.count(), 2)
        response = wallet.utils.create_wallet(self, token=token2, data={'label': 'default', 'currencycode': 'BTC',
                                                           'passphrase': 'thisISs3cured00d!'})
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        self.assertEqual(Wallet.objects.count(), 2)

    def test_wallet_multiple_currency(self):
        '''
        Verify that each user only gets one wallet per currency type.
        '''
        # Create user and log in.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet seed.
        response = wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})

        # Create BTC wallet.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.count(), 1)

        # Create LTC wallet.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'LTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.count(), 2)

        # Create DOGE wallet.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'DOGE',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Wallet.objects.count(), 3)

        # Fail to create a second wallet in any currency.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'LTC',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'DOGE',
                                                          'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "wallet already exists")
        self.assertEqual(Wallet.objects.count(), 3)

    def test_wallet_field_validators(self):
        '''
        Verify that field types are correctly validated.
        '''
        # Create first user and log in.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet seed.
        passphrase = 'thisISs3cured00d!'
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': passphrase})

        # We're required to set currencycode.
        response = wallet.utils.create_wallet(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'currencycode is required')
        self.assertEqual(Wallet.objects.count(), 0)

        # We're required to set passphrase.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'passphrase is required')
        self.assertEqual(Wallet.objects.count(), 0)

        # We're required to set valid passphrase.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': 'sillyANDwrong'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'invalid passphrase')
        self.assertEqual(Wallet.objects.count(), 0)

        # Label must be set to 'default'.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'something random', 'currencycode': 'BTC',
                                                          'passphrase': passphrase})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "invalid data")
        self.assertEqual(Wallet.objects.count(), 0)

        # Currencycode must be valid.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'NONE',
                                                          'passphrase': passphrase})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "invalid data")
        self.assertEqual(Wallet.objects.count(), 0)

        # Create a wallet.
        wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC', 'passphrase': passphrase})
        self.assertEqual(Wallet.objects.count(), 1)

        # Fail to create a second wallet
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': passphrase})
        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content['status'], "wallet already exists")
        self.assertEqual(Wallet.objects.count(), 1)

    def test_list_wallet(self):
        '''
        Verify that we can list a wallet after it's created.
        '''
        # Create user, log in, and create a wallet.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        # Create a wallet seed.
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})
        wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                               'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(Wallet.objects.count(), 1)

        # Exactly one wallet is listed.
        response = wallet.utils.list_wallets(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        # There are three types of balances:
        #  - blockchain: the value of coins found within the user's wallets
        #  - trading: the value of coins available for trading (blockchain minus orders and trades out, plus trades in)
        #  - withdrawal: the value of coins available for withdrawal (blockchain minus orders and trades out)
        '''
        {'code': 200,
         'data': [{'balance': {'blockchain': 0, 'trading': 0, 'withdrawal': 0},
                   'currencycode': 'BTC',
                   'description': None,
                   'id': '96dea482-4720-437e-96eb-68b021bd0d05',
                   'label': 'default'}],
         'debug': {},
         'status': '1 wallet found'}
         '''
        self.assertEqual(content['status'], '1 wallet found')
        self.assertEqual(len(content['data']), 1)
        for user_wallet in content['data']:
            # We only allow a 'default' label.
            self.assertEqual(user_wallet['label'], 'default')
            self.assertEqual(user_wallet['currencycode'], 'BTC')
            self.assertEqual(user_wallet['balance']['blockchain'], 0)
            self.assertEqual(user_wallet['balance']['withdrawal'], 0)
            self.assertEqual(user_wallet['balance']['trading'], 0)

    def test_list_no_wallet(self):
        '''
        Verify that we return a 404 if we try and list wallets and a user doesn't have one.
        '''
        # Create user and log in.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        self.assertEqual(Wallet.objects.count(), 0)

        # 200 OK when trying to list wallets and none exist.
        response = wallet.utils.list_wallets(self, token=token)
        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content['code'], 200)
        self.assertEqual(content['status'], "no wallets found")
        self.assertEqual(Wallet.objects.count(), 0)

    def test_list_wallet_multi_user(self):
        '''
        Verify that a user can only list their own wallet.
        '''
        # Create user, log in, and create a wallet.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})
        wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC', 'description': 'one',
                                               'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(Wallet.objects.count(), 1)

        # Create a second user, log in, and create a wallet.
        spauser.utils.create_user(self, email='b@example.com')
        response = spauser.utils.user_login(self, email='b@example.com')
        content = json.loads(response.content)
        token2 = content['token']
        wallet.utils.create_wallet_seed(self, token=token2, data={'passphrase': 'thisISs3cured00d!'})
        wallet.utils.create_wallet(self, token=token2, data={'label': 'default', 'currencycode': 'BTC', 'description': 'two',
                                                'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(Wallet.objects.count(), 2)

        # Exactly one wallet is listed for the first user
        response = wallet.utils.list_wallets(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], '1 wallet found')
        self.assertEqual(len(content['data']), 1)
        for user_wallet in content['data']:
            # Confirm this is the correct wallet.
            self.assertEqual(user_wallet['description'], 'one')
            self.assertEqual(user_wallet['label'], 'default')
            self.assertEqual(user_wallet['currencycode'], 'BTC')
            self.assertEqual(user_wallet['balance']['blockchain'], 0)
            self.assertEqual(user_wallet['balance']['withdrawal'], 0)
            self.assertEqual(user_wallet['balance']['trading'], 0)

        # Exactly one wallet is listed for the second user
        response = wallet.utils.list_wallets(self, token=token2)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], '1 wallet found')
        self.assertEqual(len(content['data']), 1)
        for user_wallet in content['data']:
            # Confirm this is the correct wallet.
            self.assertEqual(user_wallet['description'], 'two')
            self.assertEqual(user_wallet['label'], 'default')
            self.assertEqual(user_wallet['currencycode'], 'BTC')
            self.assertEqual(user_wallet['balance']['blockchain'], 0)
            self.assertEqual(user_wallet['balance']['withdrawal'], 0)
            self.assertEqual(user_wallet['balance']['trading'], 0)

    def test_list_wallet_multi_currency(self):
        '''
        Verify that a user can list wallets in multiple currencies.
        '''
        # Create user, log in, and create wallets in three currencies.
        spauser.utils.create_user(self)
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        # Create a wallet seed.
        response = wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})
        wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'DOGE', 'description': 'dogecoin', 'passphrase': 'thisISs3cured00d!'})
        wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'LTC', 'description': 'litecoin', 'passphrase': 'thisISs3cured00d!'})
        wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC', 'description': 'bitcoin', 'passphrase': 'thisISs3cured00d!'})
        self.assertEqual(Wallet.objects.count(), 3)

        # Three wallets are listed
        response = wallet.utils.list_wallets(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content["data"]), 3)
        self.assertEqual(content["status"], "3 wallets found")
        for user_wallet in content["data"]:
            if user_wallet['currencycode'] == 'BTC':
                self.assertEqual(user_wallet['description'], 'bitcoin')
                self.assertEqual(user_wallet['currencycode'], 'BTC')
                self.assertEqual(user_wallet['label'], 'default')
                self.assertEqual(user_wallet['balance']['blockchain'], 0)
                self.assertEqual(user_wallet['balance']['withdrawal'], 0)
                self.assertEqual(user_wallet['balance']['trading'], 0)
            elif user_wallet['currencycode'] == 'LTC':
                self.assertEqual(user_wallet['description'], 'litecoin')
                self.assertEqual(user_wallet['currencycode'], 'LTC')
                self.assertEqual(user_wallet['label'], 'default')
                self.assertEqual(user_wallet['balance']['blockchain'], 0)
                self.assertEqual(user_wallet['balance']['withdrawal'], 0)
                self.assertEqual(user_wallet['balance']['trading'], 0)
            elif user_wallet['currencycode'] == 'DOGE':
                self.assertEqual(user_wallet['description'], 'dogecoin')
                self.assertEqual(user_wallet['currencycode'], 'DOGE')
                self.assertEqual(user_wallet['label'], 'default')
                self.assertEqual(user_wallet['balance']['blockchain'], 0)
                self.assertEqual(user_wallet['balance']['withdrawal'], 0)
                self.assertEqual(user_wallet['balance']['trading'], 0)
            else:
                # We can't get here.
                self.assertEqual(True, False)

    def test_list_wallet_with_funds(self):
        '''
        Verify that we can list a wallet with a balance
        '''
        # Create user and log in.
        response = spauser.utils.create_user(self)
        content = json.loads(response.content)
        user_id = content['id']
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet seed and then a wallet.
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': 'thisISs3cured00d!'})
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'XLT',
                                               'passphrase': 'thisISs3cured00d!'})
        content = json.loads(response.content)
        litecoin_testnet4_wallet_id = content['data']['id']
        self.assertEqual(Wallet.objects.count(), 1)

        # Manually add a live address to the wallet:
        #  - http://dev.net:8001/api/address/litecoin_testnet4/n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU
        #  - https://chain.so/address/LTCTEST/n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU
        # Address balance: 0
        known_address = Address(label='manual', p2pkh='n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU',
                                wallet_id=litecoin_testnet4_wallet_id)
        known_address.save()
        # Manually add another live address to the wallet:
        #  - http://dev.net:8001/api/address/litecoin_testnet4/mjd6G8yeuaw7YHb3QZWoHg2ureFaVFBvCP
        #  - https://chain.so/address/LTCTEST/mjd6G8yeuaw7YHb3QZWoHg2ureFaVFBvCP
        # Balance: 0
        known_address = Address(label='manual', p2pkh='mjd6G8yeuaw7YHb3QZWoHg2ureFaVFBvCP',
                                wallet_id=litecoin_testnet4_wallet_id)
        known_address.save()
        # Manually add a third live address to the wallet:
        # - http://dev.net:8001/api/address/litecoin_testnet4/mg7xzNUDpGyLR4UmC8GV6UwE5GzNLT7haq
        # - https://chain.so/address/LTCTEST/mg7xzNUDpGyLR4UmC8GV6UwE5GzNLT7haq
        # Balance: 0
        known_address = Address(label='manual', p2pkh='mg7xzNUDpGyLR4UmC8GV6UwE5GzNLT7haq',
                                wallet_id=litecoin_testnet4_wallet_id)
        known_address.save()

        wallet_balance = 0

        # @TODO: handle the errors if the litecoin-testnet4 container isn't running
        # Exactly one wallet is listed.
        response = wallet.utils.list_wallets(self, token=token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], '1 wallet found')
        self.assertEqual(len(content['data']), 1)
        for user_wallet in content['data']:
            # We only allow a 'default' label.
            self.assertEqual(user_wallet['label'], 'default')
            self.assertEqual(user_wallet['currencycode'], 'XLT')
            # Wallet balance: 10000000000 + 0 + 20000000000
            # There are three types of balances:
            #  - blockchain: the value of coins found within the user's wallets
            #  - trading: the value of coins available for trading (blockchain minus orders and trades out, plus trades in)
            #  - withdrawal: the value of coins available for withdrawal (blockchain minus orders and trades out)
            # As this user has made no orders and no trades, all balances are the same.
            self.assertEqual(user_wallet['balance']['blockchain'], wallet_balance)
            self.assertEqual(user_wallet['balance']['withdrawal'], wallet_balance)
            self.assertEqual(user_wallet['balance']['trading'], wallet_balance)

        # list transactions
        response = wallet.utils.list_transactions(self, token=token, data={'wallet_id': litecoin_testnet4_wallet_id})
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'transactions': [{'fee': 10000000,
                                    'from_object': "[{'address': "
                                                   "'mjnHsCzRWjXfgRTu86Ny1AsDD2Qt92JfDt', "
                                                   "'value': 2136159800, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   'False}]',
                                    'height': 469869,
                                    'timestamp': 1521094942,
                                    'to_object': "[{'address': "
                                                 "'mzMQK8eirMbtLWt3TtPVbLbPCPYwaxg9Wb', "
                                                 "'value': 2126159800, 'is_spent': "
                                                 "True, 'in_wallet': False}, "
                                                 "{'address': "
                                                 "'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', "
                                                 "'value': 10000000000, 'is_spent': "
                                                 "True, 'in_wallet': True}]",
                                    'txid': '1628711f407ce4b39523f713e9428cbdf4bc5a209e881ecb081973ae4261d3ff',
                                    'value_in': 10000000000,
                                    'value_out': 0},
                                   {'fee': 10000000,
                                    'from_object': "[{'address': "
                                                   "'miumhNkh9wsDQwXX5UrVoiqkRcZbJgfdqC', "
                                                   "'value': 41815400, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   'False}]',
                                    'height': 466734,
                                    'timestamp': 1520865100,
                                    'to_object': "[{'address': "
                                                 "'mvyhG17sCo1fCxjMWV9oPsLbBEj3GuzkLr', "
                                                 "'value': 31815400, 'is_spent': True, "
                                                 "'in_wallet': False}, {'address': "
                                                 "'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', "
                                                 "'value': 10000000000, 'is_spent': "
                                                 "True, 'in_wallet': True}]",
                                    'txid': 'f2ea71ad79f4dcd357196a0a5b1c10453c5abbaececa4d62be67ab97a2563f71',
                                    'value_in': 10000000000,
                                    'value_out': 0},
                                   {'fee': 10000000,
                                    'from_object': "[{'address': "
                                                   "'mnHf2BgmVGmck43NDSw4NmmvCsRJrMukYm', "
                                                   "'value': 1843919800, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   'False}]',
                                    'height': 465822,
                                    'timestamp': 1520777316,
                                    'to_object': "[{'address': "
                                                 "'ms9Z1SD4Gu2yLbLL66fhFn7D7kRF7ZTWA1', "
                                                 "'value': 1833919800, 'is_spent': "
                                                 "True, 'in_wallet': False}, "
                                                 "{'address': "
                                                 "'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', "
                                                 "'value': 10000000000, 'is_spent': "
                                                 "True, 'in_wallet': True}]",
                                    'txid': '5b71d0408d114bd04f2be5382c2780262af996ffe4827795845f101a7d4a1d6e',
                                    'value_in': 10000000000,
                                    'value_out': 0},
                                   {'fee': 10000000,
                                    'from_object': "[{'address': "
                                                   "'mn98jrUAPMMSeCHX1xZ4U8nQiicdrWLtfn', "
                                                   "'value': 2877400775, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   'False}]',
                                    'height': 430905,
                                    'timestamp': 1519973187,
                                    'to_object': "[{'address': "
                                                 "'mqYkXS1St67h656u9YryCw4rR8bTwv78HX', "
                                                 "'value': 2867400775, 'is_spent': "
                                                 "True, 'in_wallet': False}, "
                                                 "{'address': "
                                                 "'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', "
                                                 "'value': 10000000000, 'is_spent': "
                                                 "True, 'in_wallet': True}]",
                                    'txid': 'dd6f3416914f32539e7d923c81be83aa750259caef547337237660a493b0cb6c',
                                    'value_in': 10000000000,
                                    'value_out': 0},
                                   {'fee': 10000000,
                                    'from_object': "[{'address': "
                                                   "'n1WESwdpcr1grLXbKZa3eBbxdAsVviuLi3', "
                                                   "'value': 345609600, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   "False}, {'address': "
                                                   "'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', "
                                                   "'value': 5000000000, 'in_wallet': "
                                                   'False}]',
                                    'height': 430406,
                                    'timestamp': 1519898683,
                                    'to_object': "[{'address': "
                                                 "'n1EPqYvggYxyaZSawyJVASGsikfrYAH12g', "
                                                 "'value': 335609600, 'is_spent': "
                                                 "True, 'in_wallet': False}, "
                                                 "{'address': "
                                                 "'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', "
                                                 "'value': 10000000000, 'is_spent': "
                                                 "True, 'in_wallet': True}]",
                                    'txid': 'eb97ffbd35dbf9fd8238966cbc977f0ed641078edcf5254174257ac7ea2586ac',
                                    'value_in': 10000000000,
                                    'value_out': 0}],
                  'wallet': {'balance': 60000000000,
                             'currencycode': 'XLT',
                             'description': None,
                             'id': 'ae0ab7c3-c2f1-429d-bd5b-3b6da22a85b7',
                             'label': 'default',
                             'transaction_count': 25}},
         'debug': {},
         'pager': {'count': 25,
                   'next': 'http://testserver/api/wallet/transactions/?limit=5&offset=15',
                   'previous': 'http://testserver/api/wallet/transactions/?limit=5&offset=5'},
         'status': 'wallet transactions'}
        '''
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content['status'], 'wallet transactions')
        self.assertEqual(content['data']['wallet']['currencycode'], 'XLT')
        self.assertEqual(content['data']['wallet']['balance'], wallet_balance)
        self.assertEqual(content['data']['wallet']['transaction_count'], content['pager']['count'])

        response = wallet.utils.list_transactions(self, token=token, data={'wallet_id': litecoin_testnet4_wallet_id}, limit=3)
        content = json.loads(response.content)
        self.assertEqual(content['data']['wallet']['transaction_count'], content['pager']['count'])
        #pprint(content['data']['transactions'][0])
        last_transaction_height = content['data']['transactions'][0]['height']
        last_transaction_value_in = content['data']['transactions'][0]['value_in']
        last_transaction_value_out = content['data']['transactions'][0]['value_out']
        wallet_balance = content['data']['wallet']['balance']
        blockchain_height = content['data']['blockchain']['height']

        # Filter more confirmations than the blockchain has, so all unspent are moved into pending balance.
        confirmations = 100000000000

        litecoin_testnet4_wallet = get_object_or_404(Wallet, user=user_id, id=litecoin_testnet4_wallet_id)
        blockchain_balance, pending_balance, pending_details = blockchain.utils.get_balance(identifiers={}, user_wallet=litecoin_testnet4_wallet, confirmations=confirmations)
        '''
        (0,
         50000000000,
         {'519d1d866f0babe0cd882832e1355a45626281375aff0eb6525014bc3363cc2a': {'0': 10000000000,
                                                                               'height': '408325'},
          '6c40d1cff22db811251800873e69fd9db0bde9a717764358e342eca5a07c4d44': {'1': 10000000000,
                                                                               'height': '390062'},
          '848650bed53826dff7c6df21cc806200a4ad33e9428ec28b5883691c2c637285': {'0': 10000000000,
                                                                               'height': '389474'},
          'a8c31123fc89b732bde3b886d63a73a53ccbb1e4e0a2a72c0e72198b9ef29626': {'0': 10000000000,
                                                                               'height': '429047'},
          'cba6181abed6183cbdd18bab1bb46f5097f0965414af0ece32d692330c005e5d': {'0': 10000000000,
                                                                               'height': '427492'}})
        '''
        self.assertEqual(blockchain_balance, 0)
        self.assertEqual(pending_balance, wallet_balance)

    def test_wallet_send_litecoin(self):
        public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XLT')

        # The first ten public addresses returned should be as follows:
        known_public_addresses = [
            'n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn',
            'n3gYbfQdb7BLJGxGwY4z483DHCWmBw7GRA',
            'mpAguj9No3X7NeDfjejTw9CTQkBZSY5w6v',
            'mqzMZqaNNPBs9Bj9XGSKxB1X23jySz2duV',
            'mhewyCgGDFKoEeivE6x46ibujQJMEMxre7',
            'mzMXDbE6JRx7EagiqTaL2w6sooMsEamdAm',
            'mqvUwMie7QbetXujEJDTccbxAXES7PYPok',
            'mtKEx5hzjibPZyRBmzxd4FACEfZXZTk3YT',
            'mpXDuHniRKtPgMWRb7j4AXa8Fzk2DG3mGB',
            'n1kmRdFZPMgyHeYJMsr42hUZaDsvDt9FMK',
        ]
        for index, address in enumerate(known_public_addresses):
            self.assertEqual(public_addresses[index], known_public_addresses[index])

        # The first ten change addresses returned should be as follows:
        known_change_addresses = [
            'n3c2Vg8R2kHnvuFR5E7HBcHb3wvHNUGXuA',
            'mxRoo3TayNmeR8MAGddQ7gqJgEjxdpCHMc',
            'mto18zZATzWJ9f9prGkheqo23EAbrDFV59',
            'mkxpZvWvsFJQ8CJaKAE4bqGHCKSPuqGEf3',
            'mxavdGdKnqvMvVpUushttfQYYn6zGv1Jvf',
            'mnN9rNVoZ82hJ3Mpy5TmowRbcR8aJxuKuy',
            'mi5bxRWBq69xMDgZkc42MnxTj7TJNhw6mP',
            'mmELS2QqnNe413qjtpft8MmgFfzfPEDvMR',
            'moibcZ5pRKbLgQvSbnZEUynw2A6H7qYCP2',
            'mu2cZdyzmTpHX1uyR94hwDxScr3SdAJwtV',
        ]
        for index, address in enumerate(known_change_addresses):
            self.assertEqual(change_addresses[index], known_change_addresses[index])

        # There are more than 30 public addresses returned, as more than the first ten are on the blockchain
        self.assertGreater(len(public_addresses), 30)

        # There are more than 30 change addresses returned, as more than the first ten are on the blockchain
        self.assertGreater(len(change_addresses), 30)

        # Create user and log in
        response = spauser.utils.create_user(self)
        content = json.loads(response.content)
        user_id = content['id']
        user = SpaUser.objects.get()
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet for the user
        passphrase = 'thisISs3cured00d!'
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': passphrase})
        wallet.utils.store_secrets(user, passphrase=passphrase, mnemonic=mnemonic_seed, salt=salt)
        # litecoin testnet is XLT
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'XLT',
                                                          'passphrase': passphrase})
        content = json.loads(response.content)
        wallet_id = content['data']['id']
        self.assertEqual(Wallet.objects.count(), 1)

        load_addresses_into_wallet(self, wallet_id, public_addresses, change_addresses)

        # Validate test addresses have sufficient funds
        response = wallet.utils.list_transactions(self, token=token, data={'wallet_id': wallet_id})
        content = json.loads(response.content)
        balance = content['data']['wallet']['balance']

        # Send funds to a random external address
        output = generate_output(self, public_addresses, balance)
        to_addresses = []
        total_value = 0
        for to_address in output.keys():
            to_addresses.append(to_address)
            total_value += output[to_address]

        # Invalid passphrase
        data = {'wallet_id': wallet_id, 'passphrase': 'this_is_WR0Ng', 'output': output,
                'priority': {'number_of_blocks': random.randint(1, 1008)}}
        response = wallet.utils.send_funds(self, token=token, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'invalid passphrase')

        # Valid passphrase
        data['passphrase'] = passphrase
        response = wallet.utils.send_funds(self, token=token, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        if content['status'] != "funds sent":
            print("DEBUG:")
            print(response)
            print(content)
        try:
            txid = content['data']['txid']
            fee = content['data']['fee']
        except Exception as e:
            txid = ''
            fee = 0
            print("error extracting content: %s" % e)
        self.assertEqual(64, len(txid))
        print("litecoin testnet4 (XLT) txid(%s) sent %s to %s (fee %s)" %
              (txid, wallet.utils.convert_to_decimal(total_value), ", ".join(to_addresses),
               wallet.utils.convert_to_decimal(fee)))

    def test_wallet_send_bitcoin(self):
        # Generate bitcoin testnet addresses
        public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XTN')

        # The first ten public bitcoin testnet addresses returned should be as follows:
        known_public_addresses = [
            'mqwwDHh9n1aevBinpNdYpJyYxdBLgozniK',
            'mjytDV9266vy22EQmnzYig7c8e8qjnbcJD',
            'mw62SZHYb6AXci9RwQyQKeQUUKqtWeCS1R',
            'mxBi6mdAsK1uid1Vmfqkxo9Z19XF2nWrat',
            'n19eiVyjYJLrURm7pxBnfe8MtTN2RB5Wkd',
            'muqggmbA63aLHtU4q9qeXC6wwZ2CN9wekm',
            'mxkFuRdn99rZKdk7xb4DS9Er4acYdoYpz1',
            'miGPwkkfF8hqC7T35hvVgZbkKTi2MoD1m7',
            'mxcKpkex7nXUH47Vmm5BvaSbg3caHTpGeN',
            'mpK67fzaatHUNN3qzgNzkuKCHZsYtC8Qhm',
        ]
        for index, address in enumerate(known_public_addresses):
            self.assertEqual(public_addresses[index], known_public_addresses[index])

        # The first ten bitcoin testnet change addresses returned should be as follows:
        known_change_addresses = [
            'myDc8hg8mcBwPgKjyRyJJiT4Zi7w2jMPBC',
            'mofazUvq1DQdGm75t9RA1Kr7YURpQsWe7h',
            'mn52MBiMg3bkgt3vo7dysWAi94mxQ3UPeQ',
            'mnnTyz15QfURz8rwXGGFTELr54Ned7p1E3',
            'mnfwXkQfypX4XinJqv3319FrNKyZVPxcNW',
            'miaFiwhUJ9he9xyRaiSQd4kFKKLdEY3oyd',
            'mokesNb1ZdnBNLtyqPsej2nkGNTXbXkh4G',
            'mmDSq7DYMzhcenR3gM72d9ZxQUsDFVX9Gc',
            'mrXnve7NmFZxmbqKtjYUQRciMMJo8kiFo3',
            'mgAzEXTqSyffg1ZkVtLULjaRyAqm1UNDRb',
        ]
        for index, address in enumerate(known_change_addresses):
            self.assertEqual(change_addresses[index], known_change_addresses[index])

        # There are more than 30 public addresses returned, as more than the first ten are on the blockchain
        self.assertGreater(len(public_addresses), 22)

        # As of yet no change addresses are used, so we only get back 20 addresses
        self.assertGreater(len(change_addresses), 19)

        # Create user and log in
        response = spauser.utils.create_user(self)
        content = json.loads(response.content)
        user_id = content['id']
        user = SpaUser.objects.get()
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet for the user
        passphrase = 'thisISs3cured00d!'
        # This generates random secrets, but we'll over-write with our own next
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': passphrase})
        # Now over-write the randomly generated secrets with those we use for our test wallets
        wallet.utils.store_secrets(user, passphrase=passphrase, mnemonic=mnemonic_seed, salt=salt)
        # bitcoin testnet is XTN
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'XTN',
                                                          'passphrase': passphrase})
        content = json.loads(response.content)
        #pprint(content)
        # We've successfully created a wallet for bitcoin testnet3 coins, verify it used the secrets we over-wrote
        # Note: this requires that debug information is exposed, the tests won't pass if testing is disabled.
        self.assertEqual(content['debug']['public_key'], 'tpubDDeeL2FMzXjHyMSJwGev3kGUqWBhsqXTv6ysj1JKpd2mEoprAznEeYHai9E3e5iVvuycbjfWuLUPToPH1KvkkB3rXUAdYkznisFv43QoDqy')
        self.assertEqual(content['debug']['private_key'], 'tprv8gxcBcD7rA3d5tQX3czKeLcNGUfmiWLZLoP6SVG2QMENQKa5YbxeU3fiXz83whCjhWawNXHBEyBt3DEGjJJwVUryhcH9piPBrt1foayZhcB')
        '''
        {'code': 200,
         'data': {'coin': 'bitcoin_testnet3',
                  'description': None,
                  'id': '9fec84aa-3886-4e68-8a25-7821cb6de9a9',
                  'label': 'default',
                  'symbol': 'XTN'},
         'debug': {'created': '2019-02-17T10:52:38.703586Z',
                   'last_change_index': 0,
                   'last_external_index': 0,
                   'modified': '2019-02-17T10:52:38.956448Z',
                   'private_key': 'tprv8gxcBcD7rA3d9ejc9bfoeUcjecMf8btka98NVr9ufZb33NqVdSB6eb42u4f7SBAGZc3EVumBcpxZTUe3FD8HxQiR9rRFCdfU5qrkHMojvrh',
                   'public_key': 'tpubDDeeL2FMzXjJ37mQ3FLQ3tGrDdsbHw5f9Sj9nNCD5qPRss6GFpzgq5fu5BAcHTGXzZ3H5am68x74GrptDDVT3jbHWfnZD3Pa8oVbvEMuf44'},
         'status': 'wallet created'}
         '''

        wallet_id = content['data']['id']
        self.assertEqual(Wallet.objects.count(), 1)

        load_addresses_into_wallet(self, wallet_id, public_addresses, change_addresses)

        # Validate test addresses have sufficient funds
        response = wallet.utils.list_transactions(self, token=token, data={'wallet_id': wallet_id})
        content = json.loads(response.content)
        balance = content['data']['wallet']['balance']

        # Send funds to a random external address
        output = generate_output(self, public_addresses, balance)
        to_addresses = []
        total_value = 0
        for to_address in output.keys():
            to_addresses.append(to_address)
            total_value += output[to_address]

        # Invalid passphrase
        data = {'wallet_id': wallet_id, 'passphrase': 'this_is_WR0Ng', 'output': output,
                'priority': {'number_of_blocks': random.randint(1, 1008)}}
        response = wallet.utils.send_funds(self, token=token, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'invalid passphrase')

        # Valid passphrase
        data['passphrase'] = passphrase
        #pprint(data)
        response = wallet.utils.send_funds(self, token=token, data=data)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if content['status'] != "funds sent":
            print("DEBUG:")
            print(response)
            print(content)
        try:
            txid = content['data']['txid']
            fee = content['data']['fee']
        except Exception as e:
            txid = ''
            fee = 0
            print("error extracting content: %s" % e)
        self.assertEqual(64, len(txid))
        print("bitcoin testnet3 (XTN) txid(%s) sent %s to %s (fee %s)" %
              (txid, wallet.utils.convert_to_decimal(total_value), ", ".join(to_addresses),
               wallet.utils.convert_to_decimal(fee)))

    def test_wallet_send_dogecoin(self):
        # Generate dogecoin testnet addresses
        public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XDT')

        # The first ten public dogecoin testnet addresses returned should be as follows:
        known_public_addresses = [
            'neJE4YEXrmmsAMGhdf39CYQLFfDjsEThPM',
            'nkA2oqC9HSZT4CuArbK5i7wR1enQmFVx13',
            'ne6ofXNpiqBGBS2c2ByJHaf4BrT3mtBiBo',
            'nZ2DAAY7Hj6KNuTzhgLkjnSzzKGt8RX8Dv',
            'njhPvWfhne1iuQmdWP1ifrrniJFAwUV9ag',
            'noCfXHgd47q7aKWnYbBHNZpsV3HeDFcgt8',
            'naidzVwku24j4FX4XUx5UocMp72CCFVt59',
            'niFwRNbG3khcLp44qNXjnMF6NMxrewW2y1',
            'nkhRuk8Vqys1uL7XYWBtxDFay1KeyUWV5f',
            'nW3TJEooCMCxjyfVmZ7kGHMPQKSPNxC6iP',
        ]
        for index, address in enumerate(known_public_addresses):
            self.assertEqual(public_addresses[index], known_public_addresses[index])

        # The first ten bitcoin testnet change addresses returned should be as follows:
        known_change_addresses = [
            'nXcwrtVCYf4M7gVQwohf7SxjZ2pqAJk3hd',
            'nX2yMTmsbZPRGLJJ7eoyfaskvqB2JpFTGQ',
            'neDabmRK21MxTKcAukdPKNrvrH9hu62Zq7',
            'nYGJmDgvH4bPyftBjcvTg9C4axNgmQo3hM',
            'nUEx4ZW5dBN4ptdhnR5XTBvqhbk6MznxG4',
            'nZ9sPPL2E6KkPR9pSNMXTxcvwiyApLNSRz',
            'nXbNXi9F1KXgDVWc5u1CWfpDkVzxXv6zLn',
            'nooiBC3i224JGsgvXqYUoF45RF6dSovYSG',
            'nmtUX7ZUKAhd1YmdhMD2Fr7KtgmjERMZT9',
            'nbDRMTbGC7thLbfAkaLw6c4GPPoVmEvX9q',
        ]
        for index, address in enumerate(known_change_addresses):
            self.assertEqual(change_addresses[index], known_change_addresses[index])

        self.assertGreater(len(public_addresses), 19)
        self.assertGreater(len(change_addresses), 19)

        # Create user and log in
        response = spauser.utils.create_user(self)
        content = json.loads(response.content)
        user_id = content['id']
        user = SpaUser.objects.get()
        response = spauser.utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']

        # Create a wallet for the user
        passphrase = 'thisISs3cured00d!'
        # This generates random secrets, but we'll over-write with our own next
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': passphrase})
        # Now over-write the randomly generated secrets with those we use for our test wallets
        wallet.utils.store_secrets(user, passphrase=passphrase, mnemonic=mnemonic_seed, salt=salt)
        # dogecoin testnet is XDT
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'XDT',
                                                          'passphrase': passphrase})
        content = json.loads(response.content)
        #pprint(content)
        # We've successfully created a wallet for bitcoin testnet3 coins, verify it used the secrets we over-wrote
        # Note: this requires that debug information is exposed, the tests won't pass if testing is disabled.
        self.assertEqual(content['debug']['public_key'], 'tgpv1hh5sx6nCRVknx4DELjZBRsZukHb3YzNzWfYCBKwpTA8RgjQPtsQ5udeNYvL4XpKXeoHtoNU6uTLKFrLh67K2DJDUXrEMGLSNkpgSbPrN8t')
        self.assertEqual(content['debug']['private_key'], 'tgub5Sa7De2fkaA65oiNGaMXJHRANJfDsg26H7SkMHivcaD8yjr6ofRAjD3HwcqmcQtY1y5Q4T3P8dScAxQAxZJxFFseJ5AcVkELm8jWrwa38rw')
        '''
        {'code': 200,
         'data': {'coin': 'dogecoin_testnet3',
                  'description': None,
                  'id': 'a234a57a-8be0-4b38-b5b5-4fba0e59a633',
                  'label': 'default',
                  'symbol': 'XDT'},
         'debug': {'created': '2019-02-19T13:21:45.217727Z',
                   'last_change_index': 0,
                   'last_external_index': 0,
                   'modified': '2019-02-19T13:21:45.467088Z',
                   'private_key': 'tgub5Sa7De2fkaA65oiNGaMXJHRANJfDsg26H7SkMHivcaD8yjr6ofRAjD3HwcqmcQtY1y5Q4T3P8dScAxQAxZJxFFseJ5AcVkELm8jWrwa38rw',
                   'public_key': 'tgpv1hh5sx6nCRVknx4DELjZBRsZukHb3YzNzWfYCBKwpTA8RgjQPtsQ5udeNYvL4XpKXeoHtoNU6uTLKFrLh67K2DJDUXrEMGLSNkpgSbPrN8t'},
         'status': 'wallet created'}
        '''

        wallet_id = content['data']['id']
        self.assertEqual(Wallet.objects.count(), 1)

        load_addresses_into_wallet(self, wallet_id, public_addresses, change_addresses)

        # Validate test addresses have sufficient funds
        response = wallet.utils.list_transactions(self, token=token, data={'wallet_id': wallet_id})
        content = json.loads(response.content)
        balance = content['data']['wallet']['balance']

        # Send funds to a random external address
        output = generate_output(self, public_addresses, balance)
        to_addresses = []
        total_value = 0
        for to_address in output.keys():
            to_addresses.append(to_address)
            total_value += output[to_address]

        # Invalid passphrase
        data = {'wallet_id': wallet_id, 'passphrase': 'this_is_WR0Ng', 'output': output,
                'priority': {'number_of_blocks': random.randint(1, 1008)}}
        response = wallet.utils.send_funds(self, token=token, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'invalid passphrase')

        # Valid passphrase
        data['passphrase'] = passphrase
        #pprint(data)
        response = wallet.utils.send_funds(self, token=token, data=data)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if content['status'] != "funds sent":
            print("DEBUG:")
            print(response)
            print(content)
        try:
            txid = content['data']['txid']
            fee = content['data']['fee']
        except Exception as e:
            txid = ''
            fee = 0
            print("error extracting content: %s" % e)
        self.assertEqual(64, len(txid))
        print("dogecoin testnet3 (XDG) txid(%s) sent %s to %s (fee %s)" %
              (txid, wallet.utils.convert_to_decimal(total_value), ", ".join(to_addresses),
               wallet.utils.convert_to_decimal(fee)))
