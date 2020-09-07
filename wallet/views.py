import secrets

from django.conf import settings
from rest_framework import views, permissions, generics, status
from rest_framework.response import Response
from mnemonic import Mnemonic
from pycoin.key.BIP32Node import BIP32Node
from pprint import pprint

import wallet.utils
from .models import Wallet
from .serializers import WalletSerializer
from blockchain.serializers import TransactionListingSerializer
from address.models import Address
import address.utils
from spauser.models import SpaUser
from otp import permissions as totp_permissions
import order.utils
import blockchain.utils
from blockchain.models import Transaction
import app.pagination


class WalletCreateView(views.APIView):
    """
    Use this endpoint to create a new wallet.

    Limitation: currently each user can only have 1 wallet per currency.
    """
    model = Wallet
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def post(self, request, format=None):
        # Currency code is required to create a wallet.
        currencycode, success = wallet.utils.get_currencycode(request)
        if success is not True:
            # If status code is set, then currencycode is a JSON-formatted error: abort!
            return Response(currencycode, status=success)

        # Passphrase is required to provide access to the wallet seed.
        passphrase, success = wallet.utils.get_passphrase(request)
        if success is not True:
            # If status code is set, then passphrase is a JSON-formatted error: abort!
            return Response(passphrase, status=success)

        if not wallet.utils.valid_passphrase(self.request.user, passphrase):
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "invalid passphrase",
                "code": status_code,
                "debug": {
                    "passphrase": self.request.user.passphrase,
                    "request": self.request.data,
                },
                "data": {},
            }
            return Response(data, status=status_code)

        # We currently only allow 1 wallet per user.
        serializer = WalletSerializer(Wallet(), data=request.data)
        if serializer.is_valid():
            wallets = Wallet.objects.filter(user=self.request.user.id, currencycode=currencycode)
            if len(wallets) > 0:
                status_code = status.HTTP_200_OK
                data = {
                    "status": "wallet already exists",
                    "code": status_code,
                    "debug": {
                        "request": self.request.data,
                    },
                    "data": {
                        "id": wallets[0].id,
                        "label": wallets[0].label,
                        "description": wallets[0].description,
                        "coin": settings.COINS[wallets[0].currencycode]['name'],
                        "symbol": wallets[0].currencycode,
                    },
                }
                return Response(data, status=status_code)
            else:
                # Data was validated, so create a new wallet.
                new_wallet = serializer.save()
                # Assign the wallet to the authenticated user.
                user = SpaUser.objects.get(email=self.request.user.email)
                new_wallet.user.add(user)

                # Regenerate the root HD wallet, from which we can create our per-coin account and derive addresses
                m = Mnemonic('english')
                root_seeds = wallet.utils.get_secrets(self.request.user, passphrase)
                salted_mnemonic = m.to_seed(root_seeds['mnemonic'], passphrase=root_seeds['salt'])
                root_wallet = BIP32Node.from_master_secret(master_secret=salted_mnemonic, netcode=new_wallet.currencycode)

                path = [
                    "44H",  # purpose (bip44)
                    "%sH" % settings.COINS[new_wallet.currencycode]['bip44_index'],    # coin type
                    "%sH" % settings.COINS[new_wallet.currencycode]['account_index'],  # support multiple testnets
                ]
                coin_account_key = root_wallet.subkey_for_path("/".join(path))
                #print("coin_account_key: %s" % coin_account_key)
                #print("coin_account_key public: %s" % coin_account_key.wallet_key(as_private=False))
                #print("coin_account_key private: %s" % coin_account_key.wallet_key(as_private=True))
                #print("coin_account_key address: %s" % coin_account_key.bitcoin_address())
                #print("coin_account_key wif: %s" % coin_account_key.wif())

                # This can create addresses and their WIFs for sending funds
                new_wallet.private_key = coin_account_key.wallet_key(as_private=True)
                # This can only create addresses (so can't be used to send funds)
                new_wallet.public_key = coin_account_key.wallet_key(as_private=False)
                new_wallet.save()

                status_code = status.HTTP_200_OK
                data = {
                    "status": "wallet created",
                    "code": status_code,
                    "debug": {
                        "created": new_wallet.created,
                        "modified": new_wallet.modified,
                        "last_external_index": new_wallet.last_external_index,
                        "last_change_index": new_wallet.last_change_index,
                        "private_key": new_wallet.private_key,
                        "public_key": new_wallet.public_key,
                    },
                    "data": {
                        "id": new_wallet.id,
                        "label": new_wallet.label,
                        "description": new_wallet.description,
                        "coin": settings.COINS[new_wallet.currencycode]['name'],
                        "symbol": new_wallet.currencycode,
                    }
                }
                return Response(data, status=status_code)

        # Invalid data provided.
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "invalid data",
            "code": status_code,
            "debug": {
                "request": request.data,
                "errors": serializer.errors,
            },
            "data": {
            },
        }
        return Response(data, status=status_code)

class WalletListView(views.APIView):
    """
    Use this endpoint to list a user's wallets.
    """
    model = Wallet
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def get(self, request, format=None):
        try:
            wallets = list(Wallet.objects.filter(user=self.request.user.id))
        except Exception as e:
            status_code = status.HTTP_200_OK
            data = {
                "status": "no wallets found",
                "code": status_code,
                "debug": {
                    "exception": str(e),
                },
                "data": {},
            }
            return Response(data, status=status_code)

        wallet_listing = []
        for user_wallet in wallets:
            serializer = WalletSerializer(user_wallet)

            wallet_detail = {}
            wallet_detail['id'] = serializer.data['id']
            wallet_detail['label'] = serializer.data['label']
            wallet_detail['description'] = serializer.data['description']
            wallet_detail['currencycode'] = serializer.data['currencycode']
            wallet_detail['balance'] = wallet.utils.get_balances(identifiers={}, user_wallet=user_wallet)

            wallet_listing.append(wallet_detail)

        wallets_found = len(wallet_listing)
        if wallets_found > 0:
            if wallets_found == 1:
                status_message = "%d wallet found" % wallets_found
            else:
                status_message = "%d wallets found" % wallets_found
        else:
            status_message = "no wallets found"

        status_code = status.HTTP_200_OK
        data = {
            "status": status_message,
            "code": status_code,
            "debug": {
            },
            "data": wallet_listing,
        }

        return Response(data, status=status_code)

class WalletTransactionsView(generics.GenericAPIView):
    """
    Use this endpoint to list all transactions within a wallet.
    """
    model = Wallet
    serializer_class = TransactionListingSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]
    pagination_class = app.pagination.Pagination

    def post(self, request, format=None):
        # Verify that a wallet_id has been passed in.
        wallet_id, success = wallet.utils.get_wallet_id(request)
        if success != True:
            # If status code is set, then wallet_id is a JSON-formatted error: abort!
            return Response(wallet_id, status=success)

        # Be sure the wallet exists and the user has access to it.
        user_wallet, success = wallet.utils.get_wallet(user_id=self.request.user.id, wallet_id=wallet_id)
        if success is not True:
            return Response(user_wallet, status=success)

        if user_wallet.currencycode not in settings.COINS.keys():
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "unsupported symbol",
                "code": status_code,
                "debug": {},
                "data": {
                    "symbol": user_wallet.currencycode,
                },
            }
            return Response(data, status=status_code)

        cache_height = blockchain.utils.get_cache_height(user_wallet=user_wallet)
        for address_in_wallet in Address.objects.filter(wallet=user_wallet.id).order_by('created'):
            blockchain.utils.update_cache(wallet_address=address_in_wallet, user_wallet=user_wallet, cache_height=cache_height)

        transaction_query = Transaction.objects.filter(address__wallet=user_wallet)
        transaction_count = transaction_query.count()
        transactions = transaction_query.order_by('-height')

        page = self.paginate_queryset(transactions)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            #next_page = app.pagination.Pagination.get_next_link(serializer)
            # @TODO: this is ugly, we invoke get_paginated_reponse which generates a Response object,
            # but then we simply extract the pager information so we can construct our own response
            # object. get_next_link() isn't available to us here(?), prehaps we need to create a
            # custom pager.
            serialized_data = self.get_paginated_response(serializer.data)
            pager = {
                "next": serialized_data.data['next'],
                "previous": serialized_data.data['previous'],
                "count": serialized_data.data['count'],
            }
        else:
            serializer = self.get_serializer(transactions, many=True)
            pager = {}

        balance, pending_balance, pending_details = blockchain.utils.get_balance(identifiers={}, user_wallet=user_wallet)

        data = {
            'wallet': {
                'id': user_wallet.id,
                'label': user_wallet.label,
                'balance': balance,
                'pending_balance': pending_balance,
                'pending_details': pending_details,
                'transaction_count': transaction_count,
                'description': user_wallet.description,
                'currencycode': user_wallet.currencycode,
            },
            'blockchain': {
                'height': blockchain.utils.get_height(currencycode=user_wallet.currencycode),
            },
            'transactions': serializer.data,
        }

        status_code = status.HTTP_200_OK
        response = {
            "status": "wallet transactions",
            "code": status_code,
            "pager": pager,
            "debug": {},
            "data": data,
        }
        return Response(response, status=status_code)

class WalletSendView(views.APIView):
    """
    Use this endpoint to send funds from a wallet.
    """
    model = Wallet
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def post(self, request, format=None):
        # Verify that a wallet_id has been passed in
        wallet_id, success = wallet.utils.get_wallet_id(request)
        if success is not True:
            # If status code is set, then wallet_id is a JSON-formatted error: abort!
            return Response(wallet_id, status=success)

        # Be sure the wallet exists and the user has access to it.
        user_wallet, success = wallet.utils.get_wallet(user_id=self.request.user.id, wallet_id=wallet_id)
        if success is not True:
            return Response(user_wallet, status=success)

        # Be sure wallet contains supported currency.
        if user_wallet.currencycode not in settings.COINS.keys():
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "invalid data",
                "code": status_code,
                "debug": {
                    "request": self.request.data,
                    "symbol": user_wallet.currencycode,
                },
                "data": {
                },
            }
            return Response(data, status=status_code)

        passphrase, success = wallet.utils.get_passphrase(request)
        if success != True:
            # If status code is set, then passphrase is a JSON-formatted error: abort!
            return Response(passphrase, status=success)

        if not wallet.utils.valid_passphrase(self.request.user, passphrase):
            status_code = status.HTTP_400_BAD_REQUEST
            data = {
                "status": "invalid passphrase",
                "code": status_code,
                "debug": {
                    "passphrase": self.request.user.passphrase,
                    "request": self.request.data,
                },
                "data": {},
            }
            return Response(data, status=status_code)

        output, output_total, success = wallet.utils.get_output(request, user_wallet=user_wallet)
        if success != True:
            # If status code is set, then output is a JSON-formatted error: abort!
            return Response(output, status=success)

        number_of_blocks, estimate_mode, success = wallet.utils.get_priority(request)
        if success != True:
            # If status code is set, then number_of_blocks is a JSON-formatted error: abort!
            return Response(number_of_blocks, status=success)

        # STEP 1: find enough unspent to cover desired transaction
        total_to_send = output_total
        unspent, addresses, unspent_total, success = wallet.utils.get_unspent_equal_or_greater(user_wallet, total_to_send)
        if success is not True:
            # If success isn't true, unspent contains an error: abort
            return Response(unspent, status=success)

        # STEP 2: calculate fee and change
        #   https://bitcoin.org/en/developer-reference#estimatefee
        fee, valid = wallet.utils.calculate_fee(wallet=user_wallet, vout=unspent, vin=output,
                                                number_of_blocks=number_of_blocks, estimate_mode=estimate_mode)

        if not valid:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data = {
                "status": "fee error",
                "code": status_code,
                "debug": {
                    "request": self.request.data,
                    "fee": fee,
                    "unspent": unspent,
                    "output": output,
                    "number_of_blocks": number_of_blocks,
                    "estimate_mode": estimate_mode,
                },
                "data": {},
            }
            return Response(data, status=status_code)

        # Check if our unspent can cover our desired transaction plus the calculated fee,
        # if not re-request unspent this time including enough for the fee.
        if (output_total + fee) > unspent_total:
            print("fee grew, re-request unspent")
            # TODO: loop in case this requires more unspent and therefor a larger fee
            unspent, addresses, unspent_total, success = wallet.utils.get_unspent_equal_or_greater(user_wallet, total_to_send + fee)
            if success is not True:
                # If success isn't true, unspent contains an error: abort
                return Response(unspent, status=success)

        change = unspent_total - (total_to_send + fee)
        #print("addresses: %s, unspent: %s, change: %s" % (addresses, unspent, change))

        # STEP 3: create a raw transaction including unspent and destination address
        final_output = {}
        for out_address in output:
            # Build an array of outputs we are sending
            final_output[out_address] = wallet.utils.convert_to_decimal(output[out_address])
            # An address may have multiple outputs, use a set to only get each address once

        new_change_address, change_index = address.utils.get_new_address(user_wallet=user_wallet, is_change=True)
        final_output[new_change_address['p2pkh']] = wallet.utils.convert_to_decimal(change)
        #pprint(final_output)
        raw_tx = wallet.utils.create_raw_transaction(currencycode=user_wallet.currencycode, input=unspent, output=final_output)
        #print("raw_tx: %s" % raw_tx)

        # STEP 4: sign the raw transaction
        # @TODO request private key from secrets database -- limit each wallet to only 1 private key
        private_keys = []
        # Load wallet's private key, effectively unlocking it
        unlocked_account = BIP32Node.from_hwif(user_wallet.private_key)
        # Get WIF for all addresses we're sending from
        for to_address in addresses:
            #print("to_address: %s" % to_address)
            loaded_address = Address.objects.filter(wallet=user_wallet.id, p2pkh=to_address)
            for la in loaded_address:
                if la.is_change:
                    is_change = 1
                else:
                    is_change = 0
                unlocked_address = unlocked_account.subkey_for_path("%d/%s" % (is_change, la.index))
                #print("wif: %s subkey path: %d/%s" % (unlocked_address.wif(), is_change, la.index))
                private_keys.append(unlocked_address.wif())

        #print("private_keys:")
        #pprint(private_keys)

        if user_wallet.currencycode in ['BTC', 'XTN']:
            # Starting with 0.17, bitcoind replaces the old sign RPC with a new one
            signed_tx = wallet.utils.sign_raw_transaction_with_key(currencycode=user_wallet.currencycode, raw_tx=raw_tx, private_keys=private_keys)
            #print("signed_tx: %s" % signed_tx)
        else:
            signed_tx = wallet.utils.sign_raw_transaction(currencycode=user_wallet.currencycode, raw_tx=raw_tx, output=[], private_keys=private_keys)
            #print("signed_tx: %s" % signed_tx)

        try:
            if signed_tx['complete'] is False:
                '''
                response (decoded): {'result': {'hex': '02000000011db9fe34f5a8c4854c68ca73faa92b41f479df0a562d76c3e69fefdf325855100000000000ffffffff02c4090000000000001976a914df75177fb70c628dc9387456a36c5c7f8f472f4488acdb9ee60e000000001976a914bb48756d3b4ab3d383713af776d16abef9243b3d88ac00000000', 'complete': False, 'errors': [{'txid': '10555832dfef9fe6c3762d560adf79f4412ba9fa73ca684c85c4a8f534feb91d', 'vout': 0, 'witness': [], 'scriptSig': '', 'sequence': 4294967295, 'error': 'Unable to sign input, invalid stack size (possibly missing key)'}]}, 'error': None, 'id': 51929}
                '''
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
                data = {
                    "status": "invalid transaction",
                    "code": status_code,
                    "debug": {
                        "request": self.request.data,
                        "fee": fee,
                        "signed_tx": signed_tx,
                        "output": final_output,
                        "spent": unspent,
                    },
                    "data": {},
                }
                return Response(data, status=status_code)
        except Exception as e:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            data = {
                "status": "signing error",
                "code": status_code,
                "debug": {
                    "request": self.request.data,
                    "fee": fee,
                    "signed_tx": signed_tx,
                    "output": final_output,
                    "unspent": unspent,
                    "exception": str(e),
                },
                "data": {},
            }
            return Response(data, status=status_code)

        # STEP 5: send the signed transaction
        txid = wallet.utils.send_signed_transaction(currencycode=user_wallet.currencycode, signed_tx=signed_tx['hex'])

        if txid:
            # funds were sent, add the change address to our wallet
            wallet.utils.add_addresses_to_wallet(wallet_id=user_wallet.id, label='change', p2pkh=new_change_address['p2pkh'],
                                                 p2sh_p2wpkh=None, bech32=None, index=change_index, is_change=True)
            status_message = "funds sent"
        else:
            status_message = "no funds sent"

        status_code = status.HTTP_200_OK
        data = {
            "status": status_message,
            "code": status_code,
            "debug": {
            },
            "data": {
                "txid": txid,
                "fee": fee,
                "output": final_output,
                "spent": unspent,
                "change_address": new_change_address['p2pkh'],
            },
        }
        return Response(data, status=status_code)

class WalletCreateSeedView(views.APIView):
    """
    Use this endpoint to create a new wallet seed.

    At this time, each user can only have one wallet seed.
    """
    model = Wallet
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def post(self, request, format=None):
        # @TODO: store a flag in the user or profile object indicating if a seed has been generated.

        # Require a secure passphrase has been passed in, we use this to encrypt the wallet seed.
        try:
            passphrase = request.data['passphrase']
            # @TODO: enforce some rules on the passphrase (length, character types, etc)
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
            return Response(data, status=status_code)

        # We start with an english-language mnemonic, using cryptographically secure random bytes as seed. This
        # critical piece of information can be used to regenerate the entire wallet and all contained addresses.
        # https://docs.python.org/3/library/secrets.html
        m = Mnemonic('english')
        mnemonic_seed = m.to_mnemonic(secrets.token_bytes(256 // 8))

        # Again using cryptographically secure random bytes, apply salt -- the salt is required together with the
        # above mnemonic to recreate the wallet and all addresses and so also must be backed up and secured.
        salt = secrets.token_urlsafe(48)

        success = wallet.utils.store_secrets(user=self.request.user, passphrase=passphrase, mnemonic=mnemonic_seed,
                                             salt=salt)
        if success:
            status_message = "seed created"
            debug = {
                'mnemonic': mnemonic_seed,
                'salt': salt,
                'passphrase': passphrase,
            }
        else:
            status_message = "seed already created"
            debug = wallet.utils.get_secrets(user=self.request.user, passphrase=passphrase)
            debug['passphrase'] = passphrase

        status_code = status.HTTP_200_OK
        data = {
            "status": status_message,
            "code": status_code,
            "debug": debug,
            "data": {},
        }
        return Response(data=data, status=status_code)
