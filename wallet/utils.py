import json
import binascii
import re
import base58
from pprint import pprint

from django.conf import settings
from django.urls import reverse
from rest_framework import status
import requests
from pycoin.key.BIP32Node import BIP32Node
from mnemonic import Mnemonic

import wallet.rpc
import reporting.utils
import trade.utils
import spauser.utils
from address.models import Address
from wallet.models import Wallet
from order.models import Order
from trade.models import Trade
import blockchain.utils


def get_unsettled_open_orders_or_filled_trades_out(identifiers, wallet):
    balance_out = 0

    # Look for open buy orders from same wallet where quote currency matches wallet currency.
    # A buy order has a side of True (see order.models for definition).
    # A buy order is an ask for base currency: open buy orders subtract quote currency from the wallet.
    for open_buy_order in Order.objects.filter(wallet=wallet, quote_currency=wallet.currencycode, side=True, open=True):
        balance_out += open_buy_order.volume
        reporting.utils.audit(message="open buy order with wallet in quote currency", details={
            'identifiers': identifiers,
            'open_order_details': {
                'id': open_buy_order.id,
                'cryptopair': open_buy_order.cryptopair,
                'description': open_buy_order.description,
                'volume': open_buy_order.volume,
                'fee': open_buy_order.fee,
                'balance_out': balance_out,
            }
        })

    # Look for open sell orders from same wallet where base currency matches wallet currency.
    # A sell order has a side of False (see order.models for definition).
    # A sell order is an offer for base currency: open sell orders subtract base currency from the wallet.
    for open_sell_order in Order.objects.filter(wallet=wallet, base_currency=wallet.currencycode, side=False, open=True):
        balance_out += open_sell_order.volume
        reporting.utils.audit(message="open sell order with wallet in base currency", details={
            'identifiers': identifiers,
            'open_order_details': {
                'id': open_sell_order.id,
                'cryptopair': open_sell_order.cryptopair,
                'description': open_sell_order.description,
                'volume': open_sell_order.volume,
                'fee': open_sell_order.fee,
                'balance_out': balance_out,
            }
        })

    # Look for unsettled trades of buy orders from same wallet where quote currency matches wallet currency.
    for unsettled_buy_trade in Trade.objects.filter(buy_order__wallet=wallet,
                                                    buy_order__quote_currency=wallet.currencycode,
                                                    buy_order_settled_out=trade.models.SETTLED_NONE):
        balance_out += unsettled_buy_trade.volume
        reporting.utils.audit(message="unsettled buy order trade from quote currency wallet", details={
            'identifiers': identifiers,
            'open_order_details': {
                'id': unsettled_buy_trade.id,
                'cryptopair': unsettled_buy_trade.cryptopair,
                'volume': unsettled_buy_trade.volume,
                'price': unsettled_buy_trade.price,
                'buy_fee': unsettled_buy_trade.buy_fee,
                'balance_out': balance_out,
            }
        })

    # Look for unsettled trades of sell orders from same wallet where base currency matches wallet currency.
    for unsettled_sell_trade in Trade.objects.filter(sell_order__wallet=wallet,
                                                     sell_order__base_currency=wallet.currencycode,
                                                     sell_order_settled_out=trade.models.SETTLED_NONE):
        balance_out += unsettled_sell_trade.base_volume
        reporting.utils.audit(message="unsettled sell order trade from base currency wallet", details={
            'identifiers': identifiers,
            'open_order_details': {
                'id': unsettled_sell_trade.id,
                'cryptopair': unsettled_sell_trade.cryptopair,
                'base_volume': unsettled_sell_trade.base_volume,
                'volume': unsettled_sell_trade.volume,
                'price': unsettled_sell_trade.price,
                'buy_fee': unsettled_sell_trade.buy_fee,
                'balance_out': balance_out,
            }
        })

    return balance_out

def get_unsettled_trades_in(identifiers, wallet, user_id):
    balance_in = 0

    for cryptopair in settings.CRYPTOPAIRS.keys():
        base_currency = settings.CRYPTOPAIRS[cryptopair]['base']
        quote_currency = settings.CRYPTOPAIRS[cryptopair]['quote']

        if wallet.currencycode == base_currency:
            # The wallet is part of this cryptopair, load the other half (quote currency) to look for relevant trades.
            try:
                pair_opposite_wallet = Wallet.objects.get(user=user_id, currencycode=quote_currency)
            except:
                # This wallet doesn't exist.
                continue
        elif wallet.currencycode == quote_currency:
            # The wallet is part of this cryptopair, load the other half (base currency) to look for relevant trades.
            try:
                pair_opposite_wallet = Wallet.objects.get(user=user_id, currencycode=base_currency)
            except:
                # This wallet doesn't exist.
                continue
        else:
            # The wallet is not part of this cryptopair, so skip onto the next.
            continue

        # A buy order is an ask for base currency: open buy orders add base currency and subtract quote currency.
        # Look for unsettled trades of buy orders from same wallet where base currency matches wallet currency.
        for unsettled_buy_trade in Trade.objects.filter(buy_order__wallet=pair_opposite_wallet,
                                                        buy_order__quote_currency=pair_opposite_wallet.currencycode,
                                                        buy_order_settled_in=trade.models.SETTLED_NONE):
            balance_in += unsettled_buy_trade.base_volume - trade.utils.convert_quote_to_base(volume=unsettled_buy_trade.buy_fee, price=unsettled_buy_trade.price)
            reporting.utils.audit(message="unsettled buy order trade into base currency wallet", details={
                'identifiers': identifiers,
                'open_order_details': {
                    'id': unsettled_buy_trade.id,
                    'cryptopair': unsettled_buy_trade.cryptopair,
                    'base_volume': unsettled_buy_trade.base_volume,
                    'volume': unsettled_buy_trade.volume,
                    'price': unsettled_buy_trade.price,
                    'buy_fee': unsettled_buy_trade.buy_fee,
                    'balance_in': balance_in,
                }
            })

        # A sell order is an ask for base currency: open sell orders subtract base currency and add quote currency.
        # Look for unsettled trades of sell orders from same wallet where quote currency matches wallet currency.
        for unsettled_sell_trade in Trade.objects.filter(sell_order__wallet=pair_opposite_wallet,
                                                         sell_order__base_currency=pair_opposite_wallet.currencycode,
                                                         sell_order_settled_in=trade.models.SETTLED_NONE):
            balance_in += unsettled_sell_trade.volume - unsettled_sell_trade.sell_fee
            reporting.utils.audit(message="unsettled sell order trade into quote currency wallet", details={
                'identifiers': identifiers,
                'open_order_details': {
                    'id': unsettled_sell_trade.id,
                    'cryptopair': unsettled_sell_trade.cryptopair,
                    'volume': unsettled_sell_trade.volume,
                    'price': unsettled_sell_trade.price,
                    'buy_fee': unsettled_sell_trade.buy_fee,
                    'balance_in': balance_in,
                }
            })

    return balance_in

def get_balances(identifiers, user_wallet):
    blockchain_balance, pending_balance, pending_details = blockchain.utils.get_balance(identifiers={}, user_wallet=user_wallet)
    orders_and_trades_out = get_unsettled_open_orders_or_filled_trades_out({}, wallet=user_wallet)
    user_object = user_wallet.user.get()
    trades_in = get_unsettled_trades_in(identifiers={}, wallet=user_wallet, user_id=user_object.id)
    trade_balance = blockchain_balance - orders_and_trades_out + trades_in
    withdrawal_balance = blockchain_balance - orders_and_trades_out
    return {
        'blockchain': blockchain_balance,
        'pending': pending_balance,
        'trading': trade_balance,
        'withdrawal': withdrawal_balance,
    }

def get_test_wallet_addresses(currencycode, test_user=1):
    # Test wallets use a pre-generated HD wallet mnemonic_seed and salt so
    # we consistently generate the same addresses.
    if test_user == 1:
        mnemonic_seed  = 'text satoshi giant carbon bamboo cute utility matrix fee royal apology like swim brother tuition rocket lift hen ozone machine shop catch apology tourist'
        salt           = 'nl0pFAv5mwIAcgPyfgks6hGRmnd1PQKDSfP77twc9Hq6XxTqwdQstali4T-cPZ-K'
    elif test_user == 2:
        mnemonic_seed  = 'net veteran ketchup original deliver weasel afford world protect retreat leader embody replace install course push duty biology rule wink rule diamond pelican rib'
        salt           = 'nl0pFAv5mwIAcgPyfgks6hGRmnd1PQKDSfP77twc9Hq6XxTqwdQstali4T-cPZ-K'
    elif test_user == 3:
        mnemonic_seed  = 'file coyote vessel improve excuse human shrimp nation ridge blast cash original ginger exchange dish situate during blush chief equal buyer matter visual ritual'
        salt           = 'nl0pFAv5mwIAcgPyfgks6hGRmnd1PQKDSfP77twc9Hq6XxTqwdQstali4T-cPZ-K'
    elif test_user == 4:
        mnemonic_seed =  'holiday direct again wage any bleak dawn document lucky lizard become adjust rug metal patch coin warm future exhibit giggle treat stadium cruel soup'
        salt =           'nyLIvi4XMkoUC_0_Gex9MiJsXMH5iI8xzMZ1qQPZk97QmZIiR-UPjw-XxjW2Xng3'
    else:
        print("ERROR: unsupported test_user: {}".format(test_user))
        return False, False, False, False

    external_addresses, change_addresses = get_wallet_addresses(currencycode=currencycode, mnemonic_seed=mnemonic_seed, salt=salt)
    return external_addresses, change_addresses, mnemonic_seed, salt

def get_wallet_addresses(currencycode, mnemonic_seed, salt):
    m = Mnemonic('english')
    salted_mnemonic = m.to_seed(mnemonic_seed, passphrase=salt)

    try:
        path = [
            "44H",  # purpose (bip44)
            "%sH" % settings.COINS[currencycode]['bip44_index'],    # coin type
            "%sH" % settings.COINS[currencycode]['account_index'],  # support multiple testnets
        ]
    except Exception as e:
        print("Unexpected error, invalid currencycode?: {}".format(e))
        return None, None

    root_wallet = BIP32Node.from_master_secret(
        master_secret=salted_mnemonic,
        netcode=currencycode)

    coin_account_key = root_wallet.subkey_for_path("/".join(path))
    coin_account_private_key = coin_account_key.wallet_key(as_private=True)

    external_addresses = []
    index = 0
    addresses_since_found_on_blockchain = 0
    look_for_address = True
    while look_for_address:
        coin_wallet = BIP32Node.from_hwif(coin_account_private_key)
        subkey = coin_wallet.subkey_for_path("0/%d" % index)
        new_address = subkey.bitcoin_address()
        external_addresses.append(new_address)
        if blockchain.utils.is_address_on_blockchain(currencycode=currencycode, address_to_check=new_address, confirmations=1):
            addresses_since_found_on_blockchain = 0
        else:
            addresses_since_found_on_blockchain += 1
        index += 1
        if addresses_since_found_on_blockchain >= 20:
            look_for_address = False

    change_addresses = []
    index = 0
    addresses_since_found_on_blockchain = 0
    look_for_address = True
    while look_for_address:
        coin_wallet = BIP32Node.from_hwif(coin_account_private_key)
        subkey = coin_wallet.subkey_for_path("1/%d" % index)
        new_address = subkey.bitcoin_address()
        change_addresses.append(new_address)
        if blockchain.utils.is_address_on_blockchain(currencycode=currencycode, address_to_check=new_address, confirmations=1):
            addresses_since_found_on_blockchain = 0
        else:
            addresses_since_found_on_blockchain += 1
        index += 1
        if addresses_since_found_on_blockchain >= 20:
            look_for_address = False

    return external_addresses, change_addresses

def create_wallet_seed(self, token=None, data={}):
    url = reverse('wallet:wallet-create-seed')
    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

def create_wallet(self, token=None, data={}):
    url = reverse('wallet:wallet-create')
    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

def list_wallets(self, token=None, data={}):
    url = reverse('wallet:wallet-list')
    return spauser.utils.client_get_optional_jwt(self, url=url, token=token, data=data)

def list_transactions(self, token=None, data={}, offset=None, limit=None):
    url = reverse('wallet:wallet-transactions')

    if offset is not None:
        try:
            url += "?offset=%d" % offset
        except:
            print("invalid offset (%s), must be integer" % offset)

    if limit is not None:
        try:
            if offset is not None:
                url += "&limit=%d" % limit
            else:
                url += "?limit=%d" % limit
        except Exception as e:
            print("invalid limit (%s), must be integer: %s" % (limit, str(e)))

    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

def send_funds(self, token=None, data={}):
    url = reverse('wallet:wallet-send')
    #pprint({'url': url, 'token': token, 'data': data})
    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)

def get_wallet_id(request):
    # Verify that a wallet_id has been passed in, where we can create our address.
    try:
        wallet_id = request.data['wallet_id']
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "wallet_id is required",
            "code": status_code,
            "debug": {
                "exception": str(e),
            },
            "data": {},
        }
        return data, status_code

    return wallet_id, True

def get_wallet(user_id, wallet_id):
    # Be sure the wallet exists and the user has access to it.
    try:
        user_wallet = Wallet.objects.get(user=user_id, id=wallet_id)
    except Exception as e:
        status_code = status.HTTP_200_OK
        data = {
            "status": "wallet not found",
            "code": status_code,
            "debug": {
                "user_id": user_id,
                "wallet_id": wallet_id,
                "exception": str(e),
            },
            "data": {
            },
        }
        return data, status_code
    return user_wallet, True

def get_secrets(user, passphrase):
    # @TODO: retrieve this from a remote secret store, decrypt with passphrase
    if valid_passphrase(user, passphrase):
        return {
            'mnemonic': user.mnemonic,
            'salt': user.salt,
        }
    else:
        return False

def store_secrets(user, passphrase, mnemonic, salt):
    # @TODO: store this to a remote secret store, encrypt with passphrase
    if user.passphrase or user.mnemonic or user.salt:
        return False
    else:
        user.passphrase = passphrase
        user.mnemonic = mnemonic
        user.salt = salt
        user.save()
    return True

def valid_passphrase(user, passphrase):
    # @TODO: we won't actually know the passphrase ...
    return user.passphrase == passphrase

def contains_invalid_chars(address, search=re.compile(r'[a-km-zA-HJ-Z1-9]{25,34}').search):
    return not bool(search(address))

def get_currencycode(request):
    try:
        currencycode = request.data['currencycode']
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "currencycode is required",
            "code": status_code,
            "debug": {
                "exception": str(e),
                "request": request.data,
            },
            "data": {},
        }
        return data, status_code

    return currencycode, True

def get_passphrase(request):
    try:
        passphrase = request.data['passphrase']
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "passphrase is required",
            "code": status_code,
            "debug": {
                "exception": str(e),
                "request": request.data,
            },
            "data": {},
        }
        return data, status_code

    return passphrase, True

def get_output(request, user_wallet):
    # Verify that one or more outputs has been passed in.
    try:
        output = request.data['output']
        total = 0
        for address in output:
            try:
                validated = validate_address(currencycode=user_wallet.currencycode, address=address)
            except Exception as e:
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
                data = {
                    "status": "failed to communicate with daemon",
                    "code": status_code,
                    "error": str(e),
                    "data": {
                        'symbol': user_wallet.currencycode,
                        'address': address,
                    },
                }
                return data, 0, status_code
            if not validated['isvalid']:
                print(user_wallet)
                status_code = status.HTTP_400_BAD_REQUEST
                data = {
                    "status": "invalid address",
                    "code": status_code,
                    "data": {
                        'symbol': user_wallet.currencycode,
                        'address': address,
                        'validate_address': validated,
                    },
                }
                return data, 0, status_code

            # If we got here, this is a valid address
            total += int(output[address])
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "invalid output",
            "code": status_code,
            "debug": {
                "exception": str(e),
                "request": request.data,
            },
            "data": {
            },
        }
        return data, 0, status_code

    return output, total, True

def get_priority(request):
    # Verify the number of blocks and the mode is valid
    # { 'number_of_blocks': 4, 'estimate_mode': 'CONSERVATIVE' }
    try:
        priority = request.data['priority']
    except Exception as e:
        priority = []

    try:
        if 'number_of_blocks' in priority:
            number_of_blocks = int(priority['number_of_blocks'])
        else:
            number_of_blocks = 4

        if 'estimate_mode' in priority:
            estimate_mode = priority['estimate_mode']
        else:
            estimate_mode = 'CONSERVATIVE'
    except Exception as e:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "priority must define number_of_blocks and/or estimate_mode",
            "code": status_code,
            "debug": {
                "request": request.data,
                "priority": priority,
                "exception": str(e),
            },
            "data": {
            },
        }
        return data, 0, status_code

    if number_of_blocks < 0 or number_of_blocks > 1008:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "invalid number_of_blocks, must be a value from 0 to 1008",
            "code": status_code,
            "debug": {
                "request": request.data,
                "priority": priority,
                "number_of_blocks": number_of_blocks,
            },
            "data": {
            },
        }
        return data, 0, status_code

    if estimate_mode not in ["CONSERVATIVE", "ECONOMICAL"]:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "invalid estimate_mode, must be one of: CONSERVATIVE, ECONOMICAL",
            "code": status_code,
            "debug": {
                "request": request.data,
                "priority": priority,
                "estimate_mode": estimate_mode,
            },
            "data": {
            },
        }
        return data, 0, status_code

    return number_of_blocks, estimate_mode, True

def get_unspent_equal_or_greater(wallet, value_needed):
    addresses_with_unspent = set()
    addresses = set()
    unspent = []
    total = 0
    # @TODO: implement a smarter algorithm for finding unspent vout. For now we load wallet addresses in random order.
    for address_in_wallet in Address.objects.filter(wallet=wallet.id).order_by('?'):
        for an_address in [address_in_wallet.p2pkh, address_in_wallet.p2sh_p2wpkh, address_in_wallet.bech32]:
            if an_address:
                url = '%s://%s:%d/api/address/%s/%s/unspent' % (settings.ADDRESSAPI['protocol'],
                                                                settings.ADDRESSAPI['domain'],
                                                                settings.ADDRESSAPI['port'],
                                                                settings.COINS[wallet.currencycode]['name'],
                                                                an_address)
                try:
                    addresses.add(an_address)
                    response = requests.get(url)
                    addressapi = json.loads(response.content)
                except Exception as e:
                    print("request to %s failed" % url)
                    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                    data = {
                        'status': 'fail',
                        'code': status_code,
                        'debug': {
                            'url': url,
                            'error': str(e),
                        }
                    }
                    return data, False, False, status_code

                try:
                    # 'unspent' is only set if the address was found in the blockchain (ie, it's received funds)
                    if 'unspent' in addressapi['data']:
                        for txid in addressapi['data']['unspent']:
                            for vout in addressapi['data']['unspent'][txid]:
                                if vout != 'height':
                                    value = addressapi['data']['unspent'][txid][vout]
                                    total += value
                                    unspent.append({'txid': txid, 'vout': int(vout)})
                                    addresses_with_unspent.add(an_address)
                                    if total >= value_needed:
                                        # cash out as soon as we find enough money
                                        return unspent, addresses_with_unspent, total, True
                except Exception as e:
                    print("unexpected error: %s" % e)

    # If we get here, there's not enough money in the wallet
    status_code = status.HTTP_200_OK
    data = {
        "status": "insufficient funds",
        "code": status_code,
        "debug": {
            'wallet_id': wallet.id,
            'currencycode': wallet.currencycode,
            'unspent': unspent,
            'total': total,
            'addresses': addresses,
            'addresses_with_unspent': addresses_with_unspent,
        },
        "data": {},
    }
    return data, False, False, status_code

def calculate_fee(wallet, vin, vout, number_of_blocks, estimate_mode):
    mempool_info = get_mempool_info(currencycode=wallet.currencycode)
    try:
        # Bitcoind and Litecoind define both mempoolminfee and minrelaytxfee
        minimum_fee_multiplier = int(max(mempool_info['mempoolminfee'], mempool_info['minrelaytxfee']) * 100000000)
    except:
        # Dogecoin only defines mempoolminfee
        minimum_fee_multiplier = int(mempool_info['mempoolminfee'] * 100000000)

    if number_of_blocks == 0:
        # Don't make an RPC request for smart fee, just use the minimum allowed fee (this may not be accepted by the
        # network).
        fee_multiplier = minimum_fee_multiplier
    else:
        fee_multiplier = estimate_smart_fee(currencycode=wallet.currencycode, number_of_blocks=number_of_blocks,
                                            estimate_mode=estimate_mode)

    if not fee_multiplier:
        print("WARNING: Failed to estimate smart fee")
        fee_multiplier = {
            'feerate': minimum_fee_multiplier,
        }
    elif "errors" in fee_multiplier:
        print("WARNING: RPC call to estimatesmartfee failed with the following errors:")
        for error in fee_multiplier["errors"]:
            print(" - '%s'" % error)
        fee_multiplier = {
            'feerate': minimum_fee_multiplier,
        }

    # @TODO: it's possible to not have change, technically we shouldn't assume we have change here
    vin_count = len(vin)  #
    vout_count = len(vout) + 1  # +1 is for change
    transaction_size = vin_count * 180 + vout_count * 34 + 10 + vin_count
    calculated_fee = round(transaction_size / 1024 * fee_multiplier['feerate'])
    minimum_fee = round(transaction_size / 1024 * minimum_fee_multiplier)
    # Choose which ever fee is greater
    return max(calculated_fee, minimum_fee), True

def create_raw_transaction(currencycode, input, output):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='createrawtransaction', parameters=[input, output])

def sign_raw_transaction(currencycode, raw_tx, output, private_keys):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='signrawtransaction', parameters=[raw_tx, output,
                                                                                               private_keys])

def sign_raw_transaction_with_key(currencycode, raw_tx, private_keys, previous_txs=[]):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='signrawtransactionwithkey', parameters=[raw_tx,
                                                                                                      private_keys,
                                                                                                      previous_txs])

def send_signed_transaction(currencycode, signed_tx):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='sendrawtransaction', parameters=[signed_tx])

def estimate_smart_fee(currencycode, number_of_blocks=4, estimate_mode='CONSERVATIVE'):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='estimatesmartfee', parameters=[number_of_blocks,
                                                                                             estimate_mode])

def get_mempool_info(currencycode):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='getmempoolinfo')

def validate_address(currencycode, address):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='validateaddress', parameters=[address])

def convert_to_decimal(value):
    return value / 100000000

def convert_wif_to_private_key(wif):
    first_encode = base58.b58decode(wif)
    private_key_full = binascii.hexlify(first_encode)
    private_key = private_key_full[2:-8]
    return private_key.decode()

def add_addresses_to_wallet(wallet_id, label, p2pkh, p2sh_p2wpkh, bech32, index, is_change, is_used=False):
    """
    Add address to wallet if not already there.
    """
    if not Address.objects.filter(wallet_id=wallet_id, p2pkh=p2pkh).count():
        new_address = Address.objects.create(label=label, p2pkh=p2pkh, p2sh_p2wpkh=p2sh_p2wpkh, bech32=bech32,
                                             wallet_id=wallet_id, index=index, is_change=is_change)
        new_address.save()

    if is_used:
        # In HD wallets indexes start at 0 for external and change addresses. We track the last used address (one that
        # has appeared on the blockchain) as we can only create 20 unused addresses following the last used index. This
        # requirement makes our HD wallets portable, and is referred to as the address gap limit:
        # https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki#address-gap-limit
        user_wallet, = Wallet.objects.filter(id=wallet_id)
        if is_change:
            last_change_index = user_wallet.last_change_index
            if index > last_change_index:
                # This index is greater than the last_change_index in the wallet, update
                user_wallet.last_change_index = index
                user_wallet.save()
        else:
            last_external_index = user_wallet.last_external_index
            if index > last_external_index:
                # This index is greater than the last_external_index in the wallet, update
                user_wallet.last_external_index = index
                user_wallet.save()
