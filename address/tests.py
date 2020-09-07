import json
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from pprint import pprint

from .models import Address
from spauser import utils
import address.utils
import wallet.utils


class AddressTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_address_creation(self):
        """
        Verify basic address creation.
        """
        # Create user, log in, and create a bitcoin wallet.
        passphrase = 'thisISs3cured00d!'
        utils.create_user(self)
        response = utils.user_login(self)
        content = json.loads(response.content)
        token = content['token']
        wallet.utils.create_wallet_seed(self, token=token, data={'passphrase': passphrase})
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'BTC',
                                                          'passphrase': passphrase})
        content = json.loads(response.content)
        btc_wallet_id = content['data']['id']

        # Create a bitcoin address.
        self.assertEqual(Address.objects.count(), 0)
        response = address.utils.create_address(self, token=token, data={'wallet_id': btc_wallet_id, 'label': 'test'})
        #content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(Address.objects.count(), 1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], 'address created')
        self.assertEqual(content['data']['label'], 'test')
        # P2PKH Bitcoin addresses start with 1.
        self.assertEqual(content['data']['p2pkh'][:1], '1')
        # Load from database and be sure it matches
        bitcoin_address = Address.objects.get(wallet=btc_wallet_id)
        self.assertEqual(content['data']['p2pkh'], bitcoin_address.p2pkh)
        # Bech32 Bitcoin addresses start with bc1.
        self.assertEqual(bitcoin_address.bech32[:3], 'bc1')

        # Request address again: the first address wasn't used so we get back the same address
        response = address.utils.create_address(self, token=token, data={'wallet_id': btc_wallet_id, 'label': 'test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Address.objects.count(), 1)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'address already exists')

        # Request address but with typo in wallet_id
        response = address.utils.create_address(self, token=token, data={'wallet_id': 'no-such-wallet', 'label': 'test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Address.objects.count(), 1)
        content = json.loads(response.content)
        self.assertEqual(content['status'], 'wallet not found')

        # Create a litecoin wallet and address.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'LTC', 'passphrase': 'thisISs3cured00d!'})
        content = json.loads(response.content)
        ltc_wallet_id = content['data']['id']
        response = address.utils.create_address(self, token=token, data={'wallet_id': ltc_wallet_id, 'label': 'test', 'passphrase': 'thequickbrownfox1234ABRAMAGIC'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Address.objects.count(), 2)
        content = json.loads(response.content)
        self.assertEqual(content['data']['label'], 'test')
        # P2PKH Litecoin addresses start with L.
        self.assertEqual(content['data']['p2pkh'][:1], 'L')
        litecoin_address = Address.objects.get(wallet=ltc_wallet_id)
        # Bech32 Litecoin addresses start with lc1.
        #self.assertEqual(litecoin_address.bech32[:3], 'lc1')

        # Create a dogecoin wallet and address.
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'DOGE', 'passphrase': 'thisISs3cured00d!'})
        content = json.loads(response.content)
        doge_wallet_id = content['data']['id']
        response = address.utils.create_address(self, token=token, data={'wallet_id': doge_wallet_id, 'label': 'test', 'passphrase': 'thequickbrownfox1234ABRAMAGIC'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Address.objects.count(), 3)
        content = json.loads(response.content)
        self.assertEqual(content['data']['label'], 'test')
        # P2PKH Dogecoin addresses start with D.
        self.assertEqual(content['data']['p2pkh'][:1], 'D')
        dogecoin_address = Address.objects.get(wallet=doge_wallet_id)
        # Dogecoin doesn't support Bech32 addresses yet.
        # @TODO: see if Bech32 arrives in 1.14
        #self.assertIsNone(dogecoin_address.bech32)

        # Create a litecoin testnet4 wallet
        response = wallet.utils.create_wallet(self, token=token, data={'label': 'default', 'currencycode': 'XLT', 'passphrase': 'thisISs3cured00d!'})
        content = json.loads(response.content)
        litecoin_testnet4_wallet_id = content['data']['id']
        address.utils.create_address(self, token=token, data={'wallet_id': litecoin_testnet4_wallet_id, 'label': 'testnet'})
        self.assertEqual(Address.objects.count(), 4)

        # Manually add a live address to the wallet: https://chain.so/address/LTCTEST/n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU
        known_address = Address(label='manual', p2pkh='n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', wallet_id=litecoin_testnet4_wallet_id)
        known_address.save()
        self.assertEqual(Address.objects.count(), 5)
