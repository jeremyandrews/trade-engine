import json

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from pprint import pprint

import order.utils



'''
Introduction to orders:

POST `/api/order/create/`

  All orders use a single cryptopair. A cryptopair is comprised of a Base Currency and a Quote
currency. The Base currency comes first in the name, followed by a dash, followed by the Quote
currency. For example, "BTC-LTC" has a base currency of "BTC", and a Quote currency of "LTC". The
volume, limit_price (if any), and fees of an order are always specified in the Quote currency.
  - To convert BTC to LTC, you have to sell the cryptopair.
  - To convert LTC to BTC, you have to buy the cryptopair.

  Fees are estimated when the order is placed, but are not actually subtracted until the trade is
made. Thus, a buy order for BTC-LTC with a limit of 118.0 and a volume of 118.0 may see a 0.5% fee
of 0.59 LTC when traded. After subtracting the exchange fee, there's 117.41 left, which becomes
0.995 BTC. Conversely, a sell order for BTC-LTC with a limit of 118.0 and a volume of 118.0 will
subtract 1.0 BTC from the user's BTC wallet, and add 117.41 to the user's LTC wallet.
'''

class OrderTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_order_parameters(self):
        """
        Verify order parameter validation.

        The following are examples of the errors generated when improper parameters are passed in. These tests are to
        ensure we properly handle improper data.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self)

        # Side must be set to 'buy' or 'sell'.
        response = order.utils.place_order(self, token=token1, data=({
            'side': True,
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "side parameter must be set to 'buy' or 'sell'")

        # Cryptopair must be set to a properly formatted pair.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN/XLT',
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'][0:43], "cryptopair parameter must be set to one of:")

        # Volume must be an integer.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN-XLT',
            'volume': 'abcdef',
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "volume is a required parameter")

        # Volume must be a positive integer.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN-XLT',
            'volume': 0,
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "volume must be a positive integer")

        # Limit must be a positive integer.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN-XLT',
            'volume': 1000,
            'limit_price': -100,
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "limit_price can not be a negative integer")

        # Time-In-Force must be a positive integer.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN-XLT',
            'volume': 1000,
            'limit_price': 50000000,
            'timeinforce': -100,
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "timeinforce can not be a negative integer")

        # Invalid limit_price and/or timeinforce are ignored.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN-XLT',
            'volume': 1000,
            'limit_price': 'abcdef',
            'timeinforce': 'zyxwvu',
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # All valid parameters, fails due to lack of funds in wallet.
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': 'XTN-XLT',
            'volume': 100000000000000,
            'limit_price': 100000000,
            'timeinforce': 86400,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "insufficient funds")

    def test_buy_order(self):
        """
        Verify order parameter validation.

        Endpoint:
            POST `/api/order/create/`

        Required parameters:
         - `side`: this must be set to `buy` or `sell`. Nothing else will be accepted.
         - `cryptopair`: string, for example `BTC-LTC` or `XTN-XLT` (all cryptopairs are defined in app.settings)
         - `volume`: integer representing quantity of quote currency (in satoshi) to trade.

        Optional parameters:
         - `limit_price`: integer (in satoshi), optional; for a buy this is a maximum, for a sell this is a minimum. If
                          blank or zero, this is a market order.
         - `timeinforce`: integer (in seconds), optional, the order will automatically cancel if not filled in this many
                          seconds. If blank or zero, this is a Good 'Til Canceled order and won't automatically cancel.

        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True)

        # A XTN-XLT cryptopair buy. This means converting XLT (Litecoin testnet) to XTN (Bitcoin testnet). The offer is
        # for 0.0165 XLT worth of XTN (volume), paying as much as 140.0 XLT per XTN. The order expires after 24 hours.
        cryptopair = 'XTN-XLT'
        base_currency = 'XTN'
        quote_currency = 'XLT'
        volume = 1420000  # volume is specified in XLT, so this is an offer for 0.0175 XLT
        limit_price = 14000000000  # willing to pay up to 1 XTN per 140 XLT
        timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': volume,
            'limit_price': limit_price,
            'timeinforce': timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XLT': 1650000,
                                      'XLT-fee': 1641750,
                                      'XTN': 11785,
                                      'XTN-fee': 11727},
                  'funds': {'available': 1717189,
                            'balance_of_trades_in': 0,
                            'balance_of_trades_out': 0,
                            'blockchain': {'balance': 1717189,
                                           'error_count': 0,
                                           'errors': []},
                            'currency': 'XLT'},
                  'order': {'base_currency': 'XTN',
                            'canceled': False,
                            'cryptopair': 'XTN-XLT',
                            'description': 'ask XTN for XLT',
                            'fee': 8250,
                            'filled': False,
                            'id': '394f7b53-1d92-4318-a11f-8858aa06e540',
                            'label': '',
                            'limit_price': 14000000000,
                            'open': True,
                            'original_volume': 1650000,
                            'quote_currency': 'XLT',
                            'side': 'buy',
                            'timeinforce': 86400,
                            'volume': 1650000,
                            'wallet': 'fee790d1-8595-48ee-87dd-ca76b9742073'},
                  'trades': []},
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'limit_price': 14000000000,
                               'side': 'buy',
                               'timeinforce': 86400,
                               'volume': 1650000}},
         'status': 'order accepted'}
        '''
        # The order is placed in XLT, but the response includes additional details about the estimated value:
        #  - the total value in XLT
        #  - the value in XLT minus the trade fee
        #  - the total value in XTN
        #  - the value in XTN minus the trade fee
        self.assertEqual(content['data']['estimated_value']['XLT'], volume)
        self.assertEqual(content['data']['estimated_value']['XTN'], int(volume / limit_price * 100000000))
        # The response also includes details about available funds:
        #  - currency: the currency all available funds values represent
        #  - blockchain balance: total value of coins in the currency wallet currently on the blockchain
        #  - balance_of_trades_out: the value of all open orders and all unsettled trades initiated from this wallet
        #  - balance_of_trades_in: the value of all unsettled trades into this wallet
        #  - available: block chain balance + balance_of_trades_in - balance_of_trades_out
        # The trading engine looks only at the available balance to determine if there are sufficient funds to place an
        # order.
        self.assertGreater(content['data']['funds']['available'], volume)
        # The order object mostly echo's the parameters that were sent. Some that are variable and may change in
        # response to placing an order:
        #  - description describes the trade, and changes based on buy versus sell
        #  - volume can be lower if there was one or more trades matched against our order (but original_volume will
        #    always match the volume parameter that was passed in)
        #  - fee is calculated (currently it's .5% of the order volume)
        #  - open will be set to False if the order was completely filled
        #  - filled will be nonzero if there were any trades, representing the number of trades made against this order
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "ask XTN for XLT")
        self.assertEqual(content['data']['order']['cryptopair'], cryptopair)
        self.assertEqual(content['data']['order']['base_currency'], base_currency)
        self.assertEqual(content['data']['order']['quote_currency'], quote_currency)
        self.assertEqual(content['data']['order']['volume'], volume)
        self.assertEqual(content['data']['order']['original_volume'], volume)
        self.assertEqual(content['data']['order']['fee'], int(volume * .005))
        self.assertEqual(content['data']['order']['side'], 'buy')
        self.assertEqual(content['data']['order']['limit_price'], limit_price)
        self.assertEqual(content['data']['order']['open'], True)
        self.assertEqual(content['data']['order']['canceled'], False)
        self.assertEqual(content['data']['order']['filled'], False)

    def test_sell_order(self):
        """
        Verify order parameter validation.

        Endpoint:
            POST `/api/order/create/`

        See test_buy_order for documentation: buy and sell orders essentially work the same.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True)

        # A XTN-XLT cryptopair sell. This means converting XTN (Bitcoin testnet) to XLT (Litecoin testnet). The ask is
        # for 0.0075 XLT worth of XTN (volume), for as much as 136.71 XLT per XTN. The order doesn't expire.
        cryptopair = 'XLT-XDT'
        base_currency = 'XLT'
        quote_currency = 'XDT'
        volume = 750000  # volume is specified in XDT, so this is an ask for 0.0075 XDT
        limit_price = 1367100000000  # willing to sell 13761.0 XDT for at least 1 XLT
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': volume,
            'limit_price': limit_price,
            'timeinforce': 0,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XDT': 750000,
                                      'XDT-fee': 746250,
                                      'XLT': 54,
                                      'XLT-fee': 54},
                  'funds': {'available': 1717189,
                            'balance_of_trades_in': 0,
                            'balance_of_trades_out': 0,
                            'blockchain': {'balance': 1717189,
                                           'error_count': 0,
                                           'errors': []},
                            'currency': 'XLT'},
                  'order': {'base_currency': 'XLT',
                            'canceled': False,
                            'cryptopair': 'XLT-XDT',
                            'description': 'offer XLT for XDT',
                            'fee': 3750,
                            'filled': False,
                            'id': '932ee4f7-98aa-419f-820c-4cbf21c6680d',
                            'label': '',
                            'limit_price': 1367100000000,
                            'open': True,
                            'original_volume': 750000,
                            'quote_currency': 'XDT',
                            'side': 'sell',
                            'timeinforce': 0,
                            'volume': 750000,
                            'wallet': '2dc4e331-e595-4ec5-b297-1f9c4b9198c5'},
                  'trades': []},
         'debug': {'request': {'cryptopair': 'XLT-XDT',
                               'limit_price': 1367100000000,
                               'side': 'sell',
                               'timeinforce': 0,
                               'volume': 750000}},
         'status': 'order accepted'}
        '''
        self.assertEqual(content['data']['estimated_value']['XDT'], volume)
        self.assertEqual(content['data']['estimated_value']['XLT'], int(volume / limit_price * 100000000))
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "offer XLT for XDT")
        self.assertEqual(content['data']['order']['cryptopair'], cryptopair)
        self.assertEqual(content['data']['order']['base_currency'], base_currency)
        self.assertEqual(content['data']['order']['quote_currency'], quote_currency)
        self.assertEqual(content['data']['order']['volume'], volume)
        self.assertEqual(content['data']['order']['original_volume'], volume)
        self.assertEqual(content['data']['order']['fee'], int(volume * .005))
        self.assertEqual(content['data']['order']['side'], 'sell')
        self.assertEqual(content['data']['order']['limit_price'], limit_price)
        self.assertEqual(content['data']['order']['open'], True)
        self.assertEqual(content['data']['order']['canceled'], False)
        self.assertEqual(content['data']['order']['filled'], False)

    def test_cancel_order(self):
        """
        Verify that order cancelations works correctly.

        Endpoint:
            POST `/api/order/cancel/`

        Required parameters:
         - `id`: the UUID4 unique identify for the order to be canceled

        Users can cancel orders as long as they've not been filled. Doing so returns the balance of the order to their
        wallet, again available for additional trades. If the balance is settled, it's also available for withdrawl.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)

        # Place a sell order
        cryptopair = 'XTN-XLT'
        volume = 750000
        limit_price = 1367100000000
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': volume,
            'limit_price': limit_price,
            'timeinforce': 0,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content['data']['trades']), 0)
        order_id = content['data']['order']['id']

        # Canceling an order with an invalidly formatted order ID gives an error.
        response = order.utils.cancel_order(self, token=token1, data=({
            'id': 'something-made-up',
        }))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 400,
         'data': {},
         'debug': {'invalid value': 'something-made-up'},
         'status': 'id must be a valid UUID4'}
        '''
        self.assertEqual(content['status'], 'id must be a valid UUID4')
        self.assertEqual(content['data'], {})

        # Pass in the correct order-id to cancel an order.
        response = order.utils.cancel_order(self, token=token1, data=({
            'id': order_id,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'order': {'base_currency': 'XLT',
                            'canceled': True,
                            'cryptopair': 'XLT-XDT',
                            'description': 'offer XLT for XDT',
                            'fee': 3750,
                            'filled': 0,
                            'label': '',
                            'limit_price': 1367100000000,
                            'open': False,
                            'original_volume': 750000,
                            'quote_currency': 'XDT',
                            'side': False,
                            'timeinforce': 0,
                            'volume': 750000,
                            'wallet': '4cb204ed-936d-49c8-ba78-31bcdf11a00d'}},
         'debug': {'request': {'id': 'e49366e1-3dc5-448e-8145-e260e4117069'}},
         'status': 'order canceled'}
        '''
        self.assertEqual(content['status'], 'order canceled')
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['canceled'], True)
        self.assertEqual(content['data']['order']['filled'], 0)

        # Place another sell order
        sell_volume = 75000
        sell_limit_price = 1367100000000
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
            'timeinforce': 0,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content['data']['trades']), 0)
        order_id = content['data']['order']['id']

        # Place a market buy, trading some of the above sell order
        buy_volume = 25000
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content['data']['trades']), 1)

        # Now cancel the sell order, and confirm we're able to cancel the unfilled version.
        response = order.utils.cancel_order(self, token=token1, data=({
            'id': order_id,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'order': {'base_currency': 'XTN',
                            'canceled': True,
                            'cryptopair': 'XTN-XLT',
                            'description': 'offer XTN for XLT',
                            'fee': 375,
                            'filled': 1,
                            'label': '',
                            'limit_price': 1367100000000,
                            'open': False,
                            'original_volume': 75000,
                            'quote_currency': 'XLT',
                            'side': False,
                            'timeinforce': 0,
                            'volume': 50000,
                            'wallet': '2bf895dd-207d-4afc-8d0d-8aaf8e57e95d'}},
         'debug': {'request': {'id': '2a4b42e7-a3b7-4955-94e7-ff0c9a8d822d'}},
         'status': 'order partially filled, unfilled portion canceled'}
        '''
        self.assertEqual(content['status'], 'order partially filled, unfilled portion canceled')
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['canceled'], True)
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertNotEqual(content['data']['order']['volume'], content['data']['order']['original_volume'])

        # Try to cancel the same order a second time, confirm it fails.
        response = order.utils.cancel_order(self, token=token1, data=({
            'id': order_id,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'order': {'base_currency': 'XTN',
                            'canceled': True,
                            'cryptopair': 'XTN-XLT',
                            'description': 'offer XTN for XLT',
                            'fee': 375,
                            'filled': 1,
                            'label': '',
                            'limit_price': 1367100000000,
                            'open': False,
                            'original_volume': 75000,
                            'quote_currency': 'XLT',
                            'side': False,
                            'timeinforce': 0,
                            'volume': 50000,
                            'wallet': 'aee7a2d5-f4df-48fc-8502-172258cb1625'}},
         'debug': {'request': {'id': '069d06e8-05c7-4d4b-a0bc-f85bf4024d98'}},
         'status': 'order already canceled'}
        '''
        # We can't cancel an already canceled order. Otherwise the order is unchanged.
        self.assertEqual(content['status'], 'order already canceled')
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['canceled'], True)
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertNotEqual(content['data']['order']['volume'], content['data']['order']['original_volume'])

        # Place another sell order
        sell_volume = 25000
        sell_limit_price = 1389500000000
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content['data']['trades']), 0)
        order_id = content['data']['order']['id']

        # Place a market buy, trading all the above order.
        buy_volume = 1000000
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content['data']['trades']), 1)

        # Now try to cancel the sell order, and confirm we're unable as it's already filled and closed.
        response = order.utils.cancel_order(self, token=token1, data=({
            'id': order_id,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
                 'data': {'order': {'base_currency': 'XTN',
                            'canceled': False,
                            'cryptopair': 'XTN-XLT',
                            'description': 'offer XTN for XLT',
                            'fee': 125,
                            'filled': 1,
                            'label': '',
                            'limit_price': 1389500000000,
                            'open': False,
                            'original_volume': 25000,
                            'quote_currency': 'XLT',
                            'side': False,
                            'timeinforce': 0,
                            'volume': 25000,
                            'wallet': 'c5e12e3a-4a13-4d08-a0bd-c7b2768db56f'}},
         'debug': {'request': {'id': 'eba8d42f-5a7f-4ff7-bfb7-f72479d282ac'}},
         'status': 'order fully filled, unable to cancel'}
        '''
        self.assertEqual(content['status'], 'order fully filled, unable to cancel')
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['canceled'], False)
        self.assertEqual(content['data']['order']['filled'], 1)

    def test_order_history(self):
        """
        Test order history.

        Endpoint:
            POST `/api/order/history/`

        Required parameters:
         - `cryptopair`: string, for example `BTC-LTC` or `XTN-XLT` (all cryptopairs are defined in app.settings)

        Optional parameters:
         - `open`: set to True or False to limit to open or closed orders
         - `canceled`: set to True or False to limit to canceled or not canceled orders
         - `side`: set to 'buy' (or True) or 'sell' (or False) to limit to buy or sell orders

         For example, all fully filled orders could be listed by filtering open=False&canceled=False. All open orders
         could be listed by filtering open=True.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self,
                                                                                                add_valid_xlt=True,
                                                                                                add_valid_xtn=True,
                                                                                                add_valid_xdt=True)

        # Create a buy order.
        cryptopair = 'XTN-XLT'
        buy1_volume = 25000
        buy1_limit_price = 14000000000
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy1_volume,
            'limit_price': buy1_limit_price,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 0)

        # Confirm that our order shows up in our order history
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'base_currency': 'XTN',
                   'canceled': False,
                   'created': 1549470512,
                   'cryptopair': 'XTN-XLT',
                   'description': 'ask XTN for XLT',
                   'fee': 125,
                   'filled': 0,
                   'id': 'ffa6ca5c-9b11-4f2a-ace7-39eb14ed2c44',
                   'label': '',
                   'limit_price': 14000000000,
                   'modified': 1549470512,
                   'open': True,
                   'original_volume': 25000,
                   'quote_currency': 'XLT',
                   'side': True,
                   'timeinforce': None,
                   'volume': 25000,
                   'wallet': 'cb679651-0b49-4215-993f-18b2d9e80a1a'}],
         'debug': {'request': {'cryptopair': 'XTN-XLT'}},
         'pager': {'count': 1, 'next': None, 'previous': None},
         'status': 'XTN-XLT history'}
        '''
        self.assertEqual(len(content['data']), 1)

        # Create another buy order.
        buy2_volume = 35000
        buy2_limit_price = 13500000000
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy2_volume,
            'limit_price': buy2_limit_price,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 0)

        # Create a buy order for a different cryptopair.
        cryptopair2 = 'XTN-XDT'
        buy3_volume = 25000
        buy3_limit_price = 192933432000000
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair2,
            'volume': buy3_volume,
            'limit_price': buy3_limit_price,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 0)

        # Create a sell order.
        sell1_volume = 11111
        sell1_limit_price = 13950000000
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell1_volume,
            'limit_price': sell1_limit_price,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 1)

        # Confirm that user1 only sees two orders in their order history (and not the order of the other pair).
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'base_currency': 'XTN',
                   'canceled': False,
                   'cryptopair': 'XTN-XLT',
                   'description': 'ask XTN for XLT',
                   'fee': 125,
                   'filled': 1,
                   'label': '',
                   'limit_price': 14000000000,
                   'open': True,
                   'original_volume': 25000,
                   'quote_currency': 'XLT',
                   'side': True,
                   'timeinforce': 0,
                   'volume': 13889,
                   'wallet': 'da96d73b-8274-4636-8e3d-2a5b183939de'},
                  {'base_currency': 'XTN',
                   'canceled': False,
                   'cryptopair': 'XTN-XLT',
                   'description': 'ask XTN for XLT',
                   'fee': 175,
                   'filled': 0,
                   'label': '',
                   'limit_price': 13500000000,
                   'open': True,
                   'original_volume': 35000,
                   'quote_currency': 'XLT',
                   'side': True,
                   'timeinforce': 0,
                   'volume': 35000,
                   'wallet': 'da96d73b-8274-4636-8e3d-2a5b183939de'}],
         'debug': {'request': {'cryptopair': 'XTN-XLT'}},
         'status': 'XTN-XLT history'}
        '''
        self.assertEqual(len(content['data']), 2)

        # Confirm that user2 only sees one order in their order history.
        response = order.utils.order_history(self, token=token2, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['status'], '%s history' % cryptopair)

        # Request user2 order history without specifying a cryptopair, see all order history (still just the one)
        response = order.utils.order_history(self, token=token2, data=({}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['status'], 'all history')

        # Now request user1 order history without specifying a cryptopair, see all order history (all three orders,
        # from two pairs).
        response = order.utils.order_history(self, token=token1, data=({}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']), 3)
        self.assertEqual(content['status'], 'all history')

        # Show only completely filled orders.
        response = order.utils.order_history(self, token=token2, data=({
            'cryptopair': cryptopair,
            'open_filter': False,
            'canceled_filter': False,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']), 1)

        # Show only open, sell orders.
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
            'open_filter': True,
            'side_filter': 'sell',
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [],
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'open_filter': True,
                               'side_filter': 'sell'}},
         'status': 'XTN-XLT history'}
        '''
        # Currently there aren't any open sell orders.
        self.assertEqual(len(content['data']), 0)

        # Create more than 25 orders to trigger a pager
        for _ in range(0,30):
            # Create another buy order.
            buyN_volume = 100
            buyN_limit_price = 12000000000
            response = order.utils.place_order(self, token=token1, data=({
                'side': 'buy',
                'cryptopair': cryptopair,
                'volume': buyN_volume,
                'limit_price': buyN_limit_price,
            }))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = json.loads(response.content)
            self.assertEqual(content['status'], "order accepted")
            self.assertEqual(len(content['data']['trades']), 0)

        # Request order history and confirm there's a pager
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        # There is another page of results
        self.assertNotEqual(content['pager']['next'], None)
        # This is the first page, there is not a previous page of results
        self.assertEqual(content['pager']['previous'], None)
        #pprint(content['pager'])
        '''
        {'count': 32,
         'next': 'http://testserver/api/order/history/?limit=25&offset=25',
         'previous': None}
        '''

        # Request order history and confirm there's a pager
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }), offset=25)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['pager'])
        '''
        {'count': 32,
         'next': None,
         'previous': 'http://testserver/api/order/history/?limit=25'}
         '''
        # This is the last page, there is not another page of results
        self.assertEqual(content['pager']['next'], None)
        # This is the last page, there is a previous page of results
        self.assertNotEqual(content['pager']['previous'], None)
