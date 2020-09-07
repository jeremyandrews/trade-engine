import json
import re
from pprint import pprint

from django.urls import reverse
from rest_framework import status
from django.conf import settings

from .models import Order
from address.models import Address
from wallet.models import Wallet
import spauser.utils
import address.utils
import wallet.utils


# Helper to invoke /api/order/create/ endpoint from a test.
def place_order(self, token=None, data={}):
    url = reverse('order:order-create')
    try:
        response = spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)
    except:
        response = None
        print("invalid wallet")
    return response

# Helper to invoke /api/order/cancel/ endpoint from a test.
def cancel_order(self, token=None, data={}):
    url = reverse('order:order-cancel')
    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

# Helper to invoke /api/order/history/ endpoint from a test.
def order_history(self, token=None, data={}, offset=None):
    url = reverse('order:order-history')
    if offset is not None:
        try:
            url += "?offset=%d" % offset
        except:
            print("invalid offset (%s), must be integer" % offset)
    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

# Helper to create wallets with test funds in them, necessary for our engine to accept trades.
def create_test_trading_wallets(
    self, add_valid_xtn=False, add_valid_xlt=False, add_valid_xdt=False,
    email1='a@example.com', email2='b@example.com'):
    # Create user1, log in.
    passphrase = 'thisISs3cured00d!'
    spauser.utils.create_user(self, email=email1)
    response = spauser.utils.user_login(self, email=email1)
    content = json.loads(response.content)
    token1 = content['token']
    wallet.utils.create_wallet_seed(self, token=token1, data={'passphrase': passphrase})

    # Create user2, log in.
    passphrase = 'thisISs3cured00d!'
    spauser.utils.create_user(self, email=email2)
    response = spauser.utils.user_login(self, email=email2)
    content = json.loads(response.content)
    token2 = content['token']
    wallet.utils.create_wallet_seed(self, token=token2, data={'passphrase': passphrase})

    # create bitcoin testnet wallet1
    response = wallet.utils.create_wallet(self, token=token1, data={'label': 'default',
                                                       'currencycode': 'XTN',
                                                       'passphrase': passphrase})
    content = json.loads(response.content)
    xtn_wallet_id1 = content['data']['id']
    initial_address_count = Address.objects.count()
    response = address.utils.create_address(self, token=token1, data={'wallet_id': xtn_wallet_id1, 'label': 'test'})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    self.assertEqual(Address.objects.count(), initial_address_count + 1)

    # create bitcoin testnet wallet2
    response = wallet.utils.create_wallet(self, token=token2, data={'label': 'default',
                                                       'currencycode': 'XTN',
                                                       'passphrase': passphrase})
    content = json.loads(response.content)
    xtn_wallet_id2 = content['data']['id']
    self.assertEqual(Address.objects.count(), initial_address_count + 1)
    response = address.utils.create_address(self, token=token2, data={'wallet_id': xtn_wallet_id2, 'label': 'test'})
    self.assertEqual(response.status_code, status.HTTP_200_OK)
    #content = json.loads(response.content)
    #pprint(content)
    self.assertEqual(Address.objects.count(), initial_address_count + 2)

    # create litecoin testnet wallet1
    response = wallet.utils.create_wallet(self, token=token1, data={'label': 'default',
                                                       'currencycode': 'XLT',
                                                       'passphrase': passphrase})
    content = json.loads(response.content)
    xlt_wallet_id1 = content['data']['id']
    self.assertEqual(Address.objects.count(), initial_address_count + 2)
    response = address.utils.create_address(self, token=token1, data={'wallet_id': xlt_wallet_id1, 'label': 'test'})
    self.assertEqual(Address.objects.count(), initial_address_count + 3)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

    # create litecoin testnet wallet2
    response = wallet.utils.create_wallet(self, token=token2, data={'label': 'default',
                                                       'currencycode': 'XLT',
                                                       'passphrase': passphrase})
    content = json.loads(response.content)
    xlt_wallet_id2 = content['data']['id']
    self.assertEqual(Address.objects.count(), initial_address_count + 3)
    response = address.utils.create_address(self, token=token2, data={'wallet_id': xlt_wallet_id2, 'label': 'test'})
    self.assertEqual(Address.objects.count(), initial_address_count + 4)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

    # create dogecoin testnet wallet1
    response = wallet.utils.create_wallet(self, token=token1, data={'label': 'default',
                                                       'currencycode': 'XDT',
                                                       'passphrase': passphrase})
    content = json.loads(response.content)
    xdt_wallet_id1 = content['data']['id']
    self.assertEqual(Address.objects.count(), initial_address_count + 4)
    response = address.utils.create_address(self, token=token1, data={'wallet_id': xdt_wallet_id1, 'label': 'test'})
    self.assertEqual(Address.objects.count(), initial_address_count + 5)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

    # create dogecoin testnet wallet2
    response = wallet.utils.create_wallet(self, token=token2, data={'label': 'default',
                                                       'currencycode': 'XDT',
                                                       'passphrase': passphrase})
    content = json.loads(response.content)
    xdt_wallet_id2 = content['data']['id']
    self.assertEqual(Address.objects.count(), initial_address_count + 5)
    response = address.utils.create_address(self, token=token2, data={'wallet_id': xdt_wallet_id2, 'label': 'test'})
    self.assertEqual(Address.objects.count(), initial_address_count + 6)
    self.assertEqual(response.status_code, status.HTTP_200_OK)

    # Bitcoin testnet
    public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XTN', test_user=1)
    load_test_addresses(public_addresses, wallet_id=xtn_wallet_id1, is_change=False)
    load_test_addresses(change_addresses, wallet_id=xtn_wallet_id1, is_change=True)
    print("Added {} external {} change bitcoin testnet addresses for user 1".format(len(public_addresses), len(change_addresses)))
    public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XTN', test_user=2)
    load_test_addresses(public_addresses, wallet_id=xtn_wallet_id2, is_change=False)
    load_test_addresses(change_addresses, wallet_id=xtn_wallet_id2, is_change=True)
    print("Added {} external {} change bitcoin testnet addresses for user 2".format(len(public_addresses), len(change_addresses)))

    # Litecoin testnet
    public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XLT', test_user=1)
    load_test_addresses(public_addresses, wallet_id=xlt_wallet_id1, is_change=False)
    load_test_addresses(change_addresses, wallet_id=xlt_wallet_id1, is_change=True)
    print("Added {} external {} change litecoin testnet addresses for user 1".format(len(public_addresses), len(change_addresses)))
    public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XLT', test_user=2)
    load_test_addresses(public_addresses, wallet_id=xlt_wallet_id2, is_change=False)
    load_test_addresses(change_addresses, wallet_id=xlt_wallet_id2, is_change=True)
    print("Added {} external {} change litecoin testnet addresses for user 2".format(len(public_addresses), len(change_addresses)))

    # Dogecoin testnet
    public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XDT', test_user=1)
    load_test_addresses(public_addresses, wallet_id=xdt_wallet_id1, is_change=False)
    load_test_addresses(change_addresses, wallet_id=xdt_wallet_id1, is_change=True)
    print("Added {} external {} change dogecoin testnet addresses for user 1".format(len(public_addresses), len(change_addresses)))
    public_addresses, change_addresses, mnemonic_seed, salt = wallet.utils.get_test_wallet_addresses(currencycode='XDT', test_user=2)
    load_test_addresses(public_addresses, wallet_id=xdt_wallet_id2, is_change=False)
    load_test_addresses(change_addresses, wallet_id=xlt_wallet_id2, is_change=True)
    print("Added {} external {} change dogecoin testnet addresses for user 2".format(len(public_addresses), len(change_addresses)))

    return token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
           token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2

def load_test_addresses(addresses, wallet_id, is_change=False):
    address_index = 0
    for index, address_to_load in enumerate(addresses):
        if is_change:
            label = 'test change address, index {}'.format(index)
        else:
            label = 'test address, index {}'.format(index)
        Address(label=label, p2pkh=address_to_load, wallet_id=wallet_id,
                index=index, is_change=is_change).save()

def get_fee(order, volume):
    # @TODO: calculate fee based on user history etc
    return int(volume * .005)

def get_side(request):
    # Determine which side of the trade this is, or generate error.
    try:
        value = str(request.data['side'])
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "side is a required parameter",
            "code": status_code,
            "debug": {
                "exception": str(e),
            },
            "data": {},
        }
        return data, status_code

    if value not in ["buy", "sell"]:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "side parameter must be set to 'buy' or 'sell'",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_cryptopair(request, is_required=True):
    # Determine which cryptopair is being traded, or generate error.
    try:
        value = str(request.data['cryptopair'])
    except Exception as e:
        if is_required:
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "cryptopair is a required parameter",
                "code": status_code,
                "debug": {
                    "exception": str(e),
                },
                "data": {},
            }
            return data, status_code
        else:
            # Optional, none set.
            return None, True

    cryptopairs = settings.CRYPTOPAIRS.keys()
    if value not in cryptopairs:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "cryptopair parameter must be set to one of: %s" % cryptopairs,
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_volume(request):
    # Determine how much currency in this order, or generate error.
    try:
        value = int(request.data['volume'])
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "volume is a required parameter",
            "code": status_code,
            "debug": {
                "exception": str(e),
            },
            "data": {},
        }
        return data, status_code

    if value <= 0:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "volume must be a positive integer",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_limit_price(request):
    # Determine if this is a limit_price order or a market order, or generate error.
    try:
        value = int(request.data['limit_price'])
    except Exception as e:
        value = 0

    if value < 0:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "limit_price can not be a negative integer",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_timeinforce(request):
    # Determine if this order has a time limit or not, or generate error.
    try:
        value = int(request.data['timeinforce'])
    except Exception as e:
        value = 0

    if value < 0:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "timeinforce can not be a negative integer",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_order_id(request):
    # Allows orders to be canceled by order id.
    try:
        value = request.data['id']
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "id is a required parameter",
            "code": status_code,
            "debug": {
                "exception": str(e),
            },
            "data": {},
        }
        return data, status_code

    # Order ids must be a properly formatted UUID4
    regex = re.compile('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', re.I)
    match = regex.match(value)
    if not match:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "id must be a valid UUID4",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_open_filter(request):
    # Optionally filter order history by open or closed orders.
    try:
        value = int(request.data['open_filter'])
    except Exception as e:
        value = None

    if value not in [True, False, None]:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "open_filter can be set to True, False, or None",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_canceled_filter(request):
    # Optionally filter order history by canceled or not canceled orders.
    try:
        value = request.data['canceled_filter']
    except Exception as e:
        value = None

    if value not in [True, False, None]:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "canceled_filter can be set to True, False, or None",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_side_filter(request):
    # Optionally filter order history by side
    try:
        value = request.data['side_filter']
    except Exception as e:
        value = None

    if value not in ['buy', 'sell', True, False, None]:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "side_filter can be set to buy, sell, True, False, or None",
            "code": status_code,
            "debug": {
                "invalid value": value,
            },
            "data": {},
        }
        return data, status_code

    return value, True

def get_user_fee_percent(identifiers, request, user_id):
    # @TODO: calculate based on relevant variables
    # For now we set a flat .5% fee for all orders
    return .5
