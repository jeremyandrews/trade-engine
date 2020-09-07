import json
from pprint import pprint

from django.conf import settings
from django.forms.models import model_to_dict
from rest_framework import status
import requests

from address.models import Address
import address.utils
from blockchain.models import Transaction
import reporting.utils
import wallet.rpc


# This currently queries addressapi every time. We could consider a caching layer as new blocks only
# happen every ~10 minutes, and we get notified when there are changes (though a notification can get
# lost)
# Parameters:
#  - identifiers: used in the audit trail
#  - user_wallet: the wallet to return the balance for
#  - confirmation: how many confirmations are required to consider balance reliable
def get_balance(identifiers, user_wallet, confirmations=6):
    balance = 0
    pending_balance = 0
    pending_details = {}

    blockchain_height = None

    for address_in_wallet in Address.objects.filter(wallet=user_wallet.id):
        for address in [address_in_wallet.p2pkh, address_in_wallet.p2sh_p2wpkh, address_in_wallet.bech32]:
            if address:
                url = '%s://%s:%d/api/address/%s/%s/unspent' % (settings.ADDRESSAPI['protocol'],
                                                                settings.ADDRESSAPI['domain'],
                                                                settings.ADDRESSAPI['port'],
                                                                settings.COINS[user_wallet.currencycode]['name'],
                                                                address)
                reporting.utils.audit(message="blockchain: querying", details={
                    'identifiers': identifiers,
                    'url': url,
                })
                try:
                    response = requests.get(url)
                    addressapi = json.loads(response.content)
                    reporting.utils.audit(message="blockchain: queried", details={
                        'identifiers': identifiers,
                        'addressapi': addressapi,
                    })
                    if response.status_code != status.HTTP_404_NOT_FOUND:
                        if not blockchain_height:
                            blockchain_height = get_height(currencycode=user_wallet.currencycode)
                        assert(blockchain_height > 0)
                        # Loop through unspent, and split out those that are pending from those that have sufficient
                        # confirmations to consider permanent.
                        for txid in addressapi['data']['unspent']:
                            tx_height = int(addressapi['data']['unspent'][txid]['height'])
                            for key in addressapi['data']['unspent'][txid]:
                                if key != 'height':
                                    #print("txid(%s) needed height: %d, height: %d" % (txid, (blockchain_height - confirmations), tx_height))
                                    if (blockchain_height - confirmations) > tx_height:
                                        balance += addressapi['data']['unspent'][txid][key]
                                    else:
                                        pending_balance += addressapi['data']['unspent'][txid][key]
                                        pending_details[txid] = addressapi['data']['unspent'][txid]
                        reporting.utils.audit(message="blockchain: add unspent balance", details={
                            'identifiers': identifiers,
                            'unspent_balance': addressapi['data']['balance'],
                            'balance': balance,
                        })
                except Exception as e:
                    reporting.utils.audit(message="blockchain: error", details={
                        'identifiers': identifiers,
                        'error': str(e),
                    })
                    print("error while getting blockchain balance, request to %s failed" % url)

    return balance, pending_balance, pending_details

def is_address_on_blockchain(currencycode, address_to_check, confirmations=6):
    url = '%s://%s:%d/api/address/%s/%s' % (settings.ADDRESSAPI['protocol'],
                                            settings.ADDRESSAPI['domain'],
                                            settings.ADDRESSAPI['port'],
                                            settings.COINS[currencycode]['name'],
                                            address_to_check)
    try:
        response = requests.get(url)
        addressapi = json.loads(response.content)
        if response.status_code == status.HTTP_404_NOT_FOUND:
            return False

        # Loop through transactions, and confirm that at least one has at least the number of confirmations required
        for tx in addressapi['data']['transactions']:
            if tx['confirmations'] >= confirmations:
                return True
        # If we got here, the transaction(s) associated with this address haven't been sufficiently confirmed
        return False
    except Exception as e:
        print("error while looking for address on blockchain, request to %s failed: %s" % (url, e))
        return False

# Parameters:
# - wallet_address: the address we are currently processing
# - user_wallet: the wallet the address is contained in
# - cache_height: maximum height already in cache
def update_cache(wallet_address, user_wallet, cache_height):
    for address_hash in [wallet_address.p2pkh, wallet_address.p2sh_p2wpkh, wallet_address.bech32]:
        # @TODO: optimize the backend API to accept cache_height, and only return new data
        # Possibly include cache_height + a hash of all txids, to validate the cache
        if address_hash:
            url = '%s://%s:%d/api/address/%s/%s' % (settings.ADDRESSAPI['protocol'],
                                                         settings.ADDRESSAPI['domain'],
                                                         settings.ADDRESSAPI['port'],
                                                         settings.COINS[user_wallet.currencycode]['name'],
                                                         address_hash)
            try:
                response = requests.get(url)
                if response.status_code != status.HTTP_404_NOT_FOUND:
                    addressapi = json.loads(response.content)
                    unspent = addressapi['data']['balance']
                    for transaction in addressapi['data']['transactions']:
                        # No need to reprocess old transactions
                        if transaction['block'] > cache_height:
                            # Once a value is spent, it can't be unspent. However, an unspent value can be spent at any
                            # time in future blocks, so all unspent needs to be re-evaluated regularly.
                            value_unspent = 0
                            from_object=[]
                            for from_element in transaction['from']:
                                if from_element['address']:
                                    from_element['in_wallet'] = address.utils.is_address_in_wallet(
                                        address_to_check=from_element['address'], user_wallet=user_wallet)
                                else:
                                    from_element['in_wallet'] = False
                                from_object.append(from_element)

                            to_object=[]
                            for to_element in transaction['to']:
                                if to_element['address']:
                                    to_element['in_wallet'] = address.utils.is_address_in_wallet(
                                        address_to_check=to_element['address'], user_wallet=user_wallet)
                                else:
                                    to_element['in_wallet'] = False
                                to_object.append(to_element)
                                if to_element['is_spent'] is False and to_element['in_wallet'] is True:
                                    value_unspent += to_element['value']
                            new_transaction = Transaction(
                                address=wallet_address,
                                txid=transaction['txid'],
                                height=transaction['block'],
                                timestamp=transaction['timestamp'],
                                value_in=transaction['value_in'],
                                from_object=json.dumps(from_object),
                                value_out=transaction['value_out'],
                                to_object=json.dumps(to_object),
                                fee=transaction['fee'],
                                value_unspent=value_unspent,
                            )
                            new_transaction.save()
            except Exception as e:
                print("request to %s failed: %s" % (url, str(e)))

def get_cache_height(user_wallet):
    try:
        cached_transaction = Transaction.objects.filter(address__wallet=user_wallet).order_by('-height')[0]
        height = cached_transaction.height
    except Exception as e:
        # Nothing cached
        height = 0
    return height

# Get current blockchain height
def get_height(currencycode):
    return wallet.rpc.rpc_request(currencycode=currencycode, method='getblockcount', parameters=[])
