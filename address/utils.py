import json
from pprint import pprint

from django.conf import settings
from django.urls import reverse
from django.db import connection
from django.db.models import Q
from rest_framework import status
import requests
from pycoin.key.BIP32Node import BIP32Node
from pycoin.tx.pay_to.ScriptPayToAddressWit import ScriptPayToAddressWit
from pycoin.ui import address_for_pay_to_script_wit, address_for_pay_to_script

import spauser.utils
from blockchain.models import Transaction


def address_is_used(address_to_check, user_wallet):
    try:
        transactions = Transaction.objects.filter(address__wallet=user_wallet)
        # Return True if any of the passed in addresses are being used
        for address_type in address_to_check:
            if address_type == 'p2pkh':
                is_used = transactions.filter(address__p2pkh=address_to_check[address_type])[:1]
            elif address_type == 'p2sh_pwwpkh':
                is_used = transactions.filter(address__p2wpkh=address_to_check[address_type])[:1]
            elif address_type == 'p2sh_pwwpkh':
                is_used = transactions.filter(address__bech32=address_to_check[address_type])[:1]
            if is_used.id:
                return True
        return False
    except Exception as e:
        #print ("error: %s" % str(e))
        return False

def is_address_in_wallet(address_to_check, user_wallet):
    # Check if this address exists in any form in the user's wallet
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT TRUE FROM address_address AS aa "
            "WHERE wallet_id = %s AND %s IN (aa.p2pkh, aa.p2sh_p2wpkh, aa.bech32)", [user_wallet.id, address_to_check])
        try:
            result, = cursor.fetchone()
        except Exception as e:
            result = False

    return result

def get_new_exchange_address(self, currencycode):
    # @TODO: this should ues a real wallet, and generate real addresses

    # Bitcoin, Litecoin, Dogecoin
    if currencycode in ['BTC', 'LTC', 'DOGE']:
        print("ERROR: we're not ready to settle real funds ({}) in get_new_exchange_address".format(currencycode))
        return None
    # Bitcoin testnet
    elif currencycode == 'XTN':
        # Address taken from order.utils xtn_test_addresses1
        return 'mqwwDHh9n1aevBinpNdYpJyYxdBLgozniK'
    # Litecoin testnet
    elif currencycode == 'XLT':
        # Address taken from order.utils xlt_test_addresses1
        return 'mqkapiZXy29m14hDxUvhfTgASryxrVucUX'
    # Dogecoin testnet
    elif currencycode == 'XDT':
        # Address taken from order.utils xdt_test_addresses1
        return 'neJE4YEXrmmsAMGhdf39CYQLFfDjsEThPM'
    else:
        print("ERROR: invalid currencycode({}) in get_new_exchange_address".format(currencycode))
        return None

def get_new_address(user_wallet, is_change=False, get_all_addresses=False):
    # Be sure this is a valid currency supported by the exchange
    if user_wallet.currencycode in settings.COINS.keys():
        all_addresses = []
        last_active_address = 0

        # Use the wallet's public_key to generate addresses.
        wallet_public_key = BIP32Node.from_hwif(user_wallet.public_key)

        # External address
        if not is_change:
            wallet_base = wallet_public_key.subkey(i=0, is_hardened=False, as_private=False)
            index = user_wallet.last_external_index
        # Change address
        else:
            wallet_base = wallet_public_key.subkey(i=1, is_hardened=False, as_private=False)
            index = user_wallet.last_change_index

        if get_all_addresses:
            index = 0

        # If index is non-zero, then increment by one to generate a new unused
        # index.
        if index > 0:
            index += 1

        # Look for an unused address.
        # @TODO: https://github.com/ .. /issues/6 search through a gap of 20
        searching = True
        while searching:
            # Create addresses following BIP44
            # https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki
            address_key = wallet_base.subkey(i=index, is_hardened=False, as_private=False)
            new_address = {
                'index': index,
                'p2pkh': address_key.bitcoin_address()
            }
            # Generate bech32 for Bitcoin and Bitcoin Testnet
            # @TODO get working with LTC https://github.com/richardkiss/pycoin/issues/323
            if user_wallet.currencycode in ['BTC', 'XTN']:
                try:
                    script = ScriptPayToAddressWit(b'\0', address_key.hash160(use_uncompressed=False)).script()
                    new_address['p2sh_p2wpkh'] = address_for_pay_to_script(script, netcode=user_wallet.currencycode)
                    new_address['bech32'] = address_for_pay_to_script_wit(script, netcode=user_wallet.currencycode)
                except Exception as e:
                    #print(e)
                    new_address['p2sh_p2wpkh'] = None
                    new_address['bech32'] = None
            else:
                new_address['p2sh_p2wpkh'] = None
                new_address['bech32'] = None
            #print("coin: %s, p2pkh: %s, p2sh_p2wpkh: %s, bech32: %s" % (user_wallet.currencycode, p2pkh, p2sh_p2wpkh, bech32))

            if address_is_used(new_address, user_wallet):
                index += 1
                if get_all_addresses:
                    all_addresses.append(new_address)
            else:
                last_active_address += 1
                if get_all_addresses and last_active_address > 20:
                    searching = False
                else:
                    searching = False
                #print("%s address: %s" % (user_wallet.currencycode, p2pkh))
        if get_all_addresses:
            return all_addresses, index
        else:
            return new_address, index
    else:
        return False, False

def create_address(self, token=None, data={}):
    url = reverse('address:address-create')
    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

def get_address_details(self, details, coin):
    try:
        address_details = details['data']['address']
        print("SUCCESS: %s backend enabled" % coin)
    except:
        print("WARNING: %s backend disabled" % coin)
        address_details = False
    return address_details
