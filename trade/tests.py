import json
from pprint import pprint
from io import StringIO
import time

from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.management import call_command

import order.utils
import reporting.utils
import trade.models
import trade.utils


# When an order is placed, we check to see if it matches against existing open orders. We match orders using a basic
# price-time-priority (FIFO) algorithm. Buys are matched against the lowest sell prices, and sells are matched against
# the highest buy prices.

# https://www.investopedia.com/terms/m/matchingorders.asp
# "Under a basic FIFO algorithm, or price-time-priority algorithm, the earliest active buy order at the highest
# price takes priority over any subsequent order at that price, which in turn takes priority over any active buy
# order at a lower price. For example, if a buy order for 200 shares of stock at $90 per share precedes an order for
# 50 shares of the same stock at the same price, the system must match the entire 200-share order to one or more
# sell orders before beginning to match any portion of the 50-share order."

class TradeTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_limit_order_trade(self):
        """
        Verify basic limit order trade

        Endpoint:
            POST `/api/order/create/`

        Trades happen automatically when orders are placed, if there are matching orders. For our test, we first place
        a limit buy, then we place a sell with a lower limit price which triggers a trade.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)

        # Add a buy order to the orderbook. Buying a cryptopair means buying the base currency. So, this is a trade of
        # XLT for XTN.
        cryptopair = 'XTN-XLT'
        buy_volume = 1200000
        buy_limit_price = 13800000000
        buy_timeinforce = 86400
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume,
            'limit_price': buy_limit_price,
            'timeinforce': buy_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data']['order'])
        '''
        {'base_currency': 'XTN',
         'canceled': False,
         'cryptopair': 'XTN-XLT',
         'description': 'ask XTN for XLT',
         'fee': 8500,
         'filled': False,
         'id': 'a39d1e00-7196-48af-9006-f396546ff68a',
         'label': '',
         'limit_price': 13800000000,
         'open': True,
         'original_volume': 1500000,
         'quote_currency': 'XLT',
         'settled': False,
         'side': 'buy',
         'timeinforce': 86400,
         'volume': 1500000,
         'wallet': 'bdff8ce9-9f30-49a3-aff2-69758720d887'}
        '''
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "ask XTN for XLT")
        self.assertEqual(content['data']['order']['volume'], buy_volume)
        self.assertEqual(content['data']['order']['open'], True)
        # Importantly, no trades are made when the order is placed. This is a given, as this is the first trade in an
        # otherwise empty trading engine.
        self.assertEqual(content['data']['trades'], [])

        # Add a buy order to the orderbook. Selling a cryptopair means selling the base currency. So, this is a trade of
        # XTN for XLT. The sell price is lower than the buy price on the books, so it triggers a trade.
        sell_volume = 250000
        sell_limit_price = 13600000000
        sell_timeinforce = 86400
        # /api/order/create/
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
            'timeinforce': sell_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XLT': 250000,
                                      'XLT-fee': 248750,
                                      'XTN': 1838,
                                      'XTN-fee': 1829},
                  'funds': {'available': 10000000,
                            'balance_of_trades_in': 0,
                            'balance_of_trades_out': 0,
                            'blockchain': {'balance': 10000000,
                                           'error_count': 0,
                                           'errors': []},
                            'currency': 'XTN'},
                  'order': {'base_currency': 'XTN',
                            'canceled': False,
                            'cryptopair': 'XTN-XLT',
                            'description': 'offer XTN for XLT',
                            'fee': 1250,
                            'filled': 1,
                            'label': '',
                            'limit_price': 13600000000,
                            'open': False,
                            'original_volume': 250000,
                            'quote_currency': 'XLT',
                            'side': 'sell',
                            'timeinforce': 86400,
                            'volume': 250000,
                            'wallet': '2faa589f-822d-4558-8d6d-f98af3d4b217'},
                  'trades': [{'base_volume': 1811,
                              'buy_fee': 1250,
                              'buy_order': 'e51597c2-3589-4908-b5ba-7384943c6497',
                              'cryptopair': 'XTN-XLT',
                              'description': None,
                              'id': 1,
                              'label': '',
                              'price': 13800000000,
                              'sell_fee': 1250,
                              'sell_order': 'dd9b6876-7a57-4d87-af1c-e24eb60064a8',
                              'settled': False,
                              'volume': 250000}]},
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'limit_price': 13600000000,
                               'side': 'sell',
                               'timeinforce': 86400,
                               'volume': 250000}},
         'status': 'order accepted'}
        '''
        self.assertEqual(content['status'], "order accepted")
        # The sell order was matched with a buy order on the books. The buy order had more volume, so this sell volume
        # was filled and closed.
        self.assertEqual(content['data']['order']['wallet'], xtn_wallet_id2)
        self.assertEqual(content['data']['order']['description'], "offer XTN for XLT")
        self.assertEqual(content['data']['order']['cryptopair'], cryptopair)
        self.assertEqual(content['data']['order']['volume'], sell_volume)
        self.assertEqual(content['data']['order']['original_volume'], sell_volume)
        # @TODO: for now we assume the fee is .5%, eventually we need to support dynamic fees
        self.assertEqual(content['data']['order']['fee'], int(sell_volume * .005))
        self.assertEqual(content['data']['order']['side'], 'sell')
        self.assertEqual(content['data']['order']['limit_price'], sell_limit_price)
        # The sell was fully filled by a buy, so it is now closed:
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['canceled'], False)
        # The sell was matched against one buy, so the filled counter is incremented to 1:
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertEqual(content['data']['estimated_value']['XLT'], sell_volume)
        self.assertEqual(content['data']['estimated_value']['XTN'], int(sell_volume / sell_limit_price * 100000000))
        # The trade engine always matches orders and creates as many trades as possible. In this case, one trade was
        # created, fully filling the sell order:
        self.assertEqual(len(content['data']['trades']), 1)
        for new_trade in content['data']['trades']:
            self.assertEqual(new_trade['cryptopair'], cryptopair)
            # The trade is assigned the price of the buy order on the books, which is the best value currently possible
            # for the newly places sell order.
            self.assertEqual(new_trade['price'], buy_limit_price)
            # The trade is for all the volume of the sell order.
            self.assertEqual(new_trade['volume'], sell_volume)
            # The trade engine currently assigns a flat fee to both sides of the trade.
            self.assertEqual(new_trade['buy_fee'], int(sell_volume * .005))
            self.assertEqual(new_trade['sell_fee'], int(sell_volume * .005))
            # Trades are not settled until later, when funds are actually move on the blockchain.
            self.assertEqual(new_trade['buy_order_settled_in'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['buy_order_settled_out'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['sell_order_settled_in'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['sell_order_settled_out'], trade.models.SETTLED_NONE)

        # The sell order was fully filled, so the orderbook only has the remainder of the buy order, still available
        # for another trade.
        # /api/public/XTN-XLT/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair="XTN-XLT")
        content = response.data
        self.assertEqual(content['data']['bids'],
                         [
                             [buy_limit_price, buy_volume - sell_volume],
                         ])
        self.assertEqual(content['data']['asks'],
                         [])

    def test_market_order_trade(self):
        """
        Verify basic market order trade

        Endpoint:
            POST `/api/order/create/`

        Trades happen automatically when orders are placed, if there are matching orders. For our test, we first place
        a limit sell, then we place a market buy order which immediately gets filled.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)

        # Start by creating a limit sell order
        cryptopair = 'XTN-XLT'
        sell_volume = 1250000  # volume is specified in XLT
        sell_limit_price = 14000000000  # willing to accept a minimum of 1 XTN per 140 XLT
        sell_timeinforce = 0
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
            'timeinforce': sell_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XLT': 1250000,
                                      'XLT-fee': 1243750,
                                      'XTN': 8928,
                                      'XTN-fee': 8884},
                  'funds': {'available': 10000000,
                            'balance_of_trades_in': 0,
                            'balance_of_trades_out': 0,
                            'blockchain': {'balance': 10000000,
                                           'error_count': 0,
                                           'errors': []},
                            'currency': 'XTN'},
                  'order': {'base_currency': 'XTN',
                            'canceled': False,
                            'cryptopair': 'XTN-XLT',
                            'description': 'offer XTN for XLT',
                            'fee': 6250,
                            'filled': False,
                            'id': '44438a9d-bee4-409f-b3ea-2ad70a0c27d4',
                            'label': '',
                            'limit_price': 14000000000,
                            'open': True,
                            'original_volume': 1250000,
                            'quote_currency': 'XLT',
                            'side': 'sell',
                            'timeinforce': 0,
                            'volume': 1250000,
                            'wallet': 'c9240798-3814-4c27-98a2-912007fc30fd'},
                  'trades': []},
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'limit_price': 14000000000,
                               'side': 'sell',
                               'timeinforce': 0,
                               'volume': 1250000}},
         'status': 'order accepted'}
        '''
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "offer XTN for XLT")
        self.assertEqual(content['data']['order']['volume'], sell_volume)
        self.assertEqual(content['data']['order']['open'], True)
        # Importantly, no trades are made when this order is placed. This is a given, as this is the first trade in an
        # otherwise empty trading engine.
        self.assertEqual(content['data']['trades'], [])

        # Next we create a market buy order, and generate a trade between the open orders.
        buy_volume = 1500000
        buy_limit_price = 0
        buy_timeinforce = 86400
        # /api/order/create/
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume,
            'limit_price': buy_limit_price,
            'timeinforce': buy_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XLT': 1500000,
                                      'XLT-fee': 1492500,
                                      'XTN': 1500000,
                                      'XTN-fee': 1492501},
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
                            'fee': 7500,
                            'filled': 1,
                            'label': '',
                            'limit_price': 0,
                            'open': True,
                            'original_volume': 1500000,
                            'quote_currency': 'XLT',
                            'side': 'buy',
                            'timeinforce': 86400,
                            'volume': 250000,
                            'wallet': 'eb694da0-56da-462c-be4e-939f56dcb327'},
                  'trades': [{'base_volume': 8928,
                              'buy_fee': 6250,
                              'buy_order': '144b1c00-853d-4d46-a201-288926c6ba78',
                              'cryptopair': 'XTN-XLT',
                              'description': None,
                              'id': 1,
                              'label': '',
                              'price': 14000000000,
                              'sell_fee': 6250,
                              'sell_order': 'b56d0a4a-4dfc-408e-ab53-c8b22f7790fd',
                              'settled': False,
                              'volume': 1250000}]},
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'limit_price': 0,
                               'side': 'buy',
                               'timeinforce': 86400,
                               'volume': 1500000}},
         'status': 'order accepted'}
        '''
        # The trades are matched. The newly placed buy is for more volume than the sell on the books, so this time the
        # order is only partially filled.
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "ask XTN for XLT")
        self.assertEqual(content['data']['order']['cryptopair'], cryptopair)
        # Volume represents how much volume from the order is on the books. In this case, the order was partially
        # filled, so the trade engine subtracts the already traded volume. The original_volume parameter records how
        # much volume was in the original order.
        self.assertEqual(content['data']['order']['volume'], buy_volume - sell_volume)
        self.assertEqual(content['data']['order']['original_volume'], buy_volume)
        self.assertEqual(content['data']['order']['fee'], int(buy_volume * .005))
        self.assertEqual(content['data']['order']['side'], 'buy')
        self.assertEqual(content['data']['order']['limit_price'], buy_limit_price)
        # A sell was matched with the buy, but the sell was smaller so the buy order remains open:
        self.assertEqual(content['data']['order']['open'], True)
        self.assertEqual(content['data']['order']['canceled'], False)
        # The buy was matched against one sell, so the filled counter is incremented to one:
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertEqual(content['data']['estimated_value']['XLT'], buy_volume)
        # There is no trade history in the engine, so it defaults to a flat 1:1 ratio for XLT:XTN. This only affects
        # the estimated value, note that the real trade is based on a limit price.
        self.assertEqual(content['data']['estimated_value']['XTN'], buy_volume)
        # The new buy matched a sell on the books, creating a trade:
        self.assertEqual(len(content['data']['trades']), 1)
        for new_trade in content['data']['trades']:
            self.assertEqual(new_trade['cryptopair'], cryptopair)
            # The market buy was assigned a trade price of the sell order on the books:
            self.assertEqual(new_trade['price'], sell_limit_price)
            self.assertEqual(new_trade['volume'], sell_volume)
            self.assertEqual(new_trade['buy_fee'], int(sell_volume * .005))
            self.assertEqual(new_trade['sell_fee'], int(sell_volume * .005))
            self.assertEqual(new_trade['buy_order_settled_in'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['buy_order_settled_out'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['sell_order_settled_in'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['sell_order_settled_out'], trade.models.SETTLED_NONE)

        # There's still an open buy order, but it's a market order so it does not show up on the orderbook. The
        # orderbook only shows limit orders.
        # /api/public/<cryptopair>/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair=cryptopair)
        content = response.data
        self.assertEqual(content['data']['bids'],
                         # The market buy order still exists, but as it's a market order it doesn't show up in the
                         # orderbook.
                         [])
        self.assertEqual(content['data']['asks'],
                         # The limit sell order was completely filled, so it's no longer open and no longer shows up in
                         # the orderbook.
                         [])

        # The trade engine remembers the price of the previous trade: this now defines the ratio between XLT and XTN.
        previous_trade_price = sell_limit_price

        # Now place a market sell order, to confirm a market order matched with a market order is correctly assigned the
        # price of the previous trade.
        sell_volume = 50000
        sell_limit_price = 0
        sell_timeinforce = 0
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
            'timeinforce': sell_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XLT': 50000,
                                      'XLT-fee': 49750,
                                      'XTN': 357,
                                      'XTN-fee': 356},
                  'funds': {'available': 9991072,
                            'balance_of_trades_in': 0,
                            'balance_of_trades_out': 8928,
                            'blockchain': {'balance': 10000000,
                                           'error_count': 0,
                                           'errors': []},
                            'currency': 'XTN'},
                  'order': {'base_currency': 'XTN',
                            'canceled': False,
                            'cryptopair': 'XTN-XLT',
                            'description': 'offer XTN for XLT',
                            'fee': 250,
                            'filled': 1,
                            'label': '',
                            'limit_price': 0,
                            'open': False,
                            'original_volume': 50000,
                            'quote_currency': 'XLT',
                            'side': 'sell',
                            'timeinforce': 0,
                            'volume': 50000,
                            'wallet': '07ed891c-7110-4598-9a63-e4d66f5089e1'},
                  'trades': [{'base_volume': 357,
                              'buy_fee': 250,
                              'buy_order': 'df43368e-221d-4cca-bbce-f4fe016a82bf',
                              'cryptopair': 'XTN-XLT',
                              'description': None,
                              'id': 3,
                              'label': '',
                              'price': 14000000000,
                              'sell_fee': 250,
                              'sell_order': 'a20d071c-b74f-484f-bc5e-272899bec27c',
                              'settled': False,
                              'volume': 50000}]},
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'limit_price': 0,
                               'side': 'sell',
                               'timeinforce': 0,
                               'volume': 50000}},
         'status': 'order accepted'}
        '''
        # The sell order was matched with a buy order on the books. The buy order had more volume, so this sell volume
        # was filled and closed.
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "offer XTN for XLT")
        self.assertEqual(content['data']['order']['cryptopair'], cryptopair)
        self.assertEqual(content['data']['order']['volume'], sell_volume)
        self.assertEqual(content['data']['order']['original_volume'], sell_volume)
        self.assertEqual(content['data']['order']['fee'], int(sell_volume * .005))
        self.assertEqual(content['data']['order']['side'], 'sell')
        # The trade is for a market sell and a market buy, therefor the price is set according to the previous trade.
        self.assertEqual(content['data']['order']['limit_price'], sell_limit_price)
        # Order was fully filled, so it's closed.
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertEqual(content['data']['order']['canceled'], False)
        self.assertEqual(content['data']['estimated_value']['XLT'], sell_volume)
        # Now that there's an order on the books, the XLT:XTN ratio is real.
        self.assertEqual(content['data']['estimated_value']['XTN'], int(sell_volume / previous_trade_price * 100000000))
        # A single sell matched a single buy, creating a single trade:
        self.assertEqual(len(content['data']['trades']), 1)
        for new_trade in content['data']['trades']:
            self.assertEqual(new_trade['cryptopair'], cryptopair)
            self.assertEqual(new_trade['price'], previous_trade_price)
            self.assertEqual(new_trade['volume'], sell_volume)
            self.assertEqual(new_trade['buy_fee'], int(sell_volume * .005))
            self.assertEqual(new_trade['sell_fee'], int(sell_volume * .005))
            self.assertEqual(new_trade['buy_order_settled_in'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['buy_order_settled_out'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['sell_order_settled_in'], trade.models.SETTLED_NONE)
            self.assertEqual(new_trade['sell_order_settled_out'], trade.models.SETTLED_NONE)
        # There was a previous trade out of this wallet, which was correctly subtracted from available funds (meaning
        # balance_of_trades_out is non-zero).
        self.assertGreater(content['data']['funds']['balance_of_trades_out'], 0)

        # The new market order was only partially filled, but again as it's a market order it doesn't show up in the
        # orderbook.
        # /api/public/<cryptopair>/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair=cryptopair)
        content = response.data
        self.assertEqual(content['data']['bids'],
                         [])
        self.assertEqual(content['data']['asks'],
                         # The market sell order was only partially filled, but as it's a market order it does not show
                         # up in the orderbook.
                         [])

        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        content = response.data
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'amount': 50000,
                   'date': 1547024249.633375,
                   'id': 2,
                   'price': 14000000000},
                  {'amount': 1250000,
                   'date': 1547024249.328768,
                   'id': 1,
                   'price': 14000000000}],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orders'}
        '''
        # Both trades show up in the trade history. See reporting.tests for trade history documentation.
        self.assertEqual(len(content['data']), 2)

        # /api/public/<cryptopair>/ticker/
        response = reporting.utils.view_ticker(self, cryptopair=cryptopair)
        content = response.data
        #pprint(content)
        '''
        {'code': 200,
         'data': {'base': {'24h_volume': 9285, 'symbol': 'XTN', 'volume': 357},
                  'last_timestamp': 1547024319.440791,
                  'quote': {'24h_high': 14000000000,
                            '24h_low': 14000000000,
                            '24h_volume': 1300000,
                            'ask': None,
                            'bid': None,
                            'difference': 0,
                            'price': 14000000000,
                            'symbol': 'XLT',
                            'volume': 50000},
                  'symbol': 'XTN-XLT'},
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT ticker'}
        '''
        # The ticker offers real-time insight into the last trade, along with some other detail. See reporting.tests for
        # trade ticket documentation.

        # Currently there are no limit sell orders open in the orderbook
        self.assertEqual(content['data']['quote']['ask'], None)
        # Currently there are no limit buy orders open in the orderbook
        self.assertEqual(content['data']['quote']['bid'], None)

    def test_user_trade_history(self):
        """
        Verify a user can review their trade history.

        Endpoint:
            POST `/api/trade/history/`

        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self,
                                                                                                add_valid_xlt=True,
                                                                                                add_valid_xtn=True,
                                                                                                add_valid_xdt=True)

        # Create a buy order.
        cryptopair = 'XTN-XLT'
        buy_volume1 = 5000
        buy_limit_price1 = 13800000000
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume1,
            'limit_price': buy_limit_price1,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(len(content['data']['trades']), 0)

        # Create a sell market order, subtracting XTN and adding XLT.
        cryptopair = 'XTN-XLT'
        sell_volume1 = 50000
        # /api/order/create/
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume1,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']['trades']), 1)

        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'base_volume': 36,
                   'buy_fee': 25,
                   'buy_order': '8d76f4f9-3b30-4344-b096-aac1b40466b9',
                   'cryptopair': 'XTN-XLT',
                   'description': None,
                   'label': '',
                   'price': 13800000000,
                   'sell_fee': 25,
                   'sell_order': '80059961-f92e-43cf-a42f-dfc4604eb14f',
                   'settled': False,
                   'volume': 5000}],
         'debug': {'request': {'cryptopair': 'XTN-XLT'}},
         'status': 'XTN-XLT history'}
        '''
        # We've only had one trade so far.
        self.assertEqual(len(content['data']), 1)

        # Create a buy order in a different currency pair.
        cryptopair2 = 'XTN-XDT'
        buy_volume2 = 1000000
        buy_limit_price2 = 19293343200000
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair2,
            'volume': buy_volume2,
            'limit_price': buy_limit_price2,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']['trades']), 0)

        # User two creates a sell market order in the new pair, subtracting XTN and adding XDT.
        sell_volume2 = 22000000
        # /api/order/create/
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair2,
            'volume': sell_volume2,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(len(content['data']['trades']), 1)

        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        # We've only had one trade of THIS cryptopair
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['status'], '%s history' % cryptopair)
        # The returned trade is the correct cryptopair
        self.assertEqual(content['data'][0]['cryptopair'], cryptopair)

        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({
            'cryptopair': cryptopair2,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)

        # We've only had one trade of THIS cryptopair
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['status'], '%s history' % cryptopair2)
        # The returned trade is the correct cryptopair
        self.assertEqual(content['data'][0]['cryptopair'], cryptopair2)

        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'base_volume': 5,
                   'buy_fee': 5000,
                   'buy_order': 'acdb5c2e-d34f-4df6-aaef-602f31170d6f',
                   'created': 1550937077,
                   'cryptopair': 'XTN-XDT',
                   'description': None,
                   'id': 9,
                   'label': '',
                   'modified': 1550937077,
                   'price': 19293343200000,
                   'sell_fee': 5000,
                   'sell_order': '41262ab7-2f8c-47f4-a6b0-b27111367231',
                   'settled': False,
                   'volume': 1000000},
                  {'base_volume': 36,
                   'buy_fee': 25,
                   'buy_order': 'e37a2d06-b7e7-4243-9e01-23576b104eb0',
                   'created': 1550937076,
                   'cryptopair': 'XTN-XLT',
                   'description': None,
                   'id': 8,
                   'label': '',
                   'modified': 1550937076,
                   'price': 13800000000,
                   'sell_fee': 25,
                   'sell_order': 'f16d1925-d6dd-4fa5-b09f-4d78ee7d5c21',
                   'settled': False,
                   'volume': 5000}],
         'debug': {'request': {}},
         'pager': {'count': 2, 'next': None, 'previous': None},
         'status': 'all history'}
        '''
        # Finally, we see both trades if we include all cryptopairs
        self.assertEqual(len(content['data']), 2)
        self.assertEqual(content['status'], 'all history')

        # Create 30 more tiny orders, each of which will match against the existing sell order.
        for _ in range(0,30):
            # Create a buy order.
            cryptopair = 'XTN-XLT'
            buyN_volume = 1000
            buyN_limit_price = 14000000000
        # /api/order/create/
            response = order.utils.place_order(self, token=token1, data=({
                'side': 'buy',
                'cryptopair': cryptopair,
                'volume': buyN_volume,
                'limit_price': buyN_limit_price,
            }))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = json.loads(response.content)
            self.assertEqual(len(content['data']['trades']), 1)

        # Confirm the trade history has a pager
        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['pager'])
        '''
        {'count': 31,
         'next': 'http://testserver/api/trade/history/?limit=25&offset=25',
         'previous': None}
         '''
        # There is another page of results
        self.assertNotEqual(content['pager']['next'], None)
        # This is the first page, there is not a previous page of results
        self.assertEqual(content['pager']['previous'], None)

        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }), offset=25)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['pager'])
        '''
        {'count': 31,
         'next': None,
         'previous': 'http://testserver/api/trade/history/?limit=25'}
        '''
        # This is the last page of results, there's no next page
        self.assertEqual(content['pager']['next'], None)
        # This is the last page of results, there is a previous page
        self.assertNotEqual(content['pager']['previous'], None)

        # Override default page size, show only 5 results per page
        # /api/public/<cryptopair>/trades/
        response = trade.utils.trade_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }), offset=15, limit=5)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['pager'])
        '''
        {'count': 31,
         'next': 'http://testserver/api/trade/history/?limit=5&offset=20',
         'previous': 'http://testserver/api/trade/history/?limit=5&offset=10'}
        '''
        # This is in the middle of the results, there's a next page
        self.assertNotEqual(content['pager']['next'], None)
        # This is in the middle of the results, there's a previous page
        self.assertNotEqual(content['pager']['previous'], None)

    def test_trade_accounting(self):
        """
        Verify that trades out subtract from the wallet's balance, and trades in add to the wallet's available balance.

        Endpoint:
            POST `/api/order/create/`

        The exchange calculate's a user's available funds based on their blockchain balance - open orders - unsettled
        trades out + unsettled trades in. Verify that this is working as expected.
        """
        user1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        user2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = \
            order.utils.create_test_trading_wallets(self, add_valid_xlt=True, add_valid_xtn=True)

        # User1 places a limit buy order:
        #  - offer to trade quote currency (XLT) for base currency (XTN)
        #  - filling this order means subtracting XLT and adding XTN
        cryptopair = "XTN-XLT"
        user1_buy1_volume = 40000
        user1_buy1_limit_price = 14000000000
        # /api/order/create/
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': user1_buy1_volume,
            'limit_price': user1_buy1_limit_price,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 0)

        # User2 places a market sell order:
        #  - ask for quote currency (XLT) with base currency (XTN)
        #  - filling this order means subtracting XTN and adding XLT
        user2_sell1_volume = 25000
        # /api/order/create/
        response = order.utils.place_order(self, token=user2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user2_sell1_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 1)
        #pprint(content['data']['funds'])
        '''
        {'available': 10000000,
         'balance_of_trades_in': 0,
         'balance_of_trades_out': 0,
         'blockchain': {'balance': 10000000, 'error_count': 0, 'errors': []},
         'currency': 'XTN'}
        '''
        # As the first sell order and first trade, there's no funds coming in or out of this wallet yet.
        self.assertEqual(content['data']['funds']['balance_of_trades_in'], 0)
        self.assertEqual(content['data']['funds']['balance_of_trades_out'], 0)
        # Selling a pair means trading the base currency (XTN) for the quote currency (XLT), so we're looking at
        # available XTN funds.
        self.assertEqual(content['data']['funds']['currency'], 'XTN')

        # Use the following details in confirming our accounting is working.
        trade1_price = content['data']['trades'][0]['price']
        trade1_base_volume = content['data']['trades'][0]['base_volume']
        trade1_base_fee = content['data']['trades'][0]['sell_fee']
        trade1_quote_volume = content['data']['trades'][0]['volume']
        trade1_quote_fee = content['data']['trades'][0]['buy_fee']

        # User2 places a market sell order, again this means:
        #  - ask for quote currency (XLT) with base currency (XTN)
        #  - filling this order means subtracting XTN and adding XLT
        user2_sell2_volume = 15000
        # /api/order/create/
        response = order.utils.place_order(self, token=user2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user2_sell2_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 1)

        # Use the following details in confirming our accounting is working.
        trade2_price = content['data']['trades'][0]['price']
        trade2_base_volume = content['data']['trades'][0]['base_volume']
        trade2_base_fee = content['data']['trades'][0]['sell_fee']
        trade2_quote_volume = content['data']['trades'][0]['volume']
        trade2_quote_fee = content['data']['trades'][0]['buy_fee']
        #pprint(content['data']['funds'])
        '''
        {'available': 30882946,
         'balance_of_trades_in': 0,
         'balance_of_trades_out': 178,
         'blockchain': {'balance': 30883124, 'error_count': 0, 'errors': []},
         'currency': 'XTN'}
        '''
        # Selling a pair means trading the base currency (XTN) for the quote currency (XLT), so we're looking at
        # available XTN funds
        self.assertEqual(content['data']['funds']['currency'], 'XTN')
        # We subtract the first trade from our available base currency value:
        self.assertEqual(content['data']['funds']['balance_of_trades_out'], trade1_base_volume)

        # User1 places a market buy order, again this means:
        #  - offer to trade quote currency (XLT) for base currency (XTN)
        #  - filling this order means subtracting XLT and adding XTN
        user1_buy2_volume = 10000
        # /api/order/create/
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': user1_buy2_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")

        #pprint(content['data']['funds'])

        # Buying a pair means trading the quote currency (XLT) for the base currency (XTN), so we're looking at
        # available XLT funds
        self.assertEqual(content['data']['funds']['currency'], 'XLT')
        # We subtract the first trade from our available base currency value:
        self.assertEqual(content['data']['funds']['balance_of_trades_out'], trade1_quote_volume + trade2_quote_volume)
        # There's nothing to match this order against, so there's no trade
        self.assertEqual(len(content['data']['trades']), 0)

        # Now User1 places a limit sell order, switching sides of the currency pair. This means:
        #  - ask for quote currency (XLT) with base currency (XTN)
        #  - filling this order means subtracting XTN and adding XLT
        user1_sell1_volume = 12300
        user1_sell1_limit_price = 14100000000
        # /api/order/create/
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sell1_volume,
            'limit_price': user1_sell1_limit_price,
        }))
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content['status'], "order accepted")
        # There's nothing to match this order against, so there's no trade
        self.assertEqual(len(content['data']['trades']), 0)

        #pprint(content['data']['funds'])
        '''
        {'available': 10000285,
         'balance_of_trades_in': 285,
         'balance_of_trades_out': 0,
         'blockchain': {'balance': 10000000, 'error_count': 0, 'errors': []},
         'currency': 'XTN'}
        '''
        # Selling a pair means trading the base currency (XTN) for the quote currency (XLT), so we're looking at
        # available XTN funds
        self.assertEqual(content['data']['funds']['currency'], 'XTN')
        # We add our first trades into our available base currency value:
        self.assertEqual(content['data']['funds']['balance_of_trades_in'],
                         trade1_base_volume - trade.utils.convert_quote_to_base(volume=trade1_base_fee, price=trade1_price) \
                         + trade2_base_volume - trade.utils.convert_quote_to_base(volume=trade2_base_fee, price=trade2_price))

        # Set an impossible volume, this will fail
        user1_sellN_volume = 50000000000000
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sellN_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "insufficient funds")
        #pprint(content['data']['funds'])
        '''
        {'available': 9987985,
         'balance_of_trades_in': 285,
         'balance_of_trades_out': 12300,
         'blockchain': {'balance': 10000000, 'error_count': 0, 'errors': []},
         'currency': 'XTN'}
         '''
        available_for_trading = content['data']['funds']['available']
        calculated_available = content['data']['funds']['blockchain']['balance'] \
            - content['data']['funds']['balance_of_trades_out'] \
            + content['data']['funds']['balance_of_trades_in']
        # Basic sanity test that the backend is correctly calculating available funds field
        self.assertEqual(available_for_trading, calculated_available)

        # Try and place an order for available funds + 1, it must fail
        user1_sellN_volume = available_for_trading + 1
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sellN_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "insufficient funds")

        # Try and place an order for available funds, it will succeed
        user1_sellN_volume = available_for_trading
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sellN_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], "order accepted")
        user1_sellN_order_id = content['data']['order']['id']

        # Try and place a small order, we have 0 available funds however so it must fail
        user1_sellO_volume = 1000
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sellO_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], "insufficient funds")

        # Cancel the large order so we can confirm that the funds free up for a new trade.
        response = order.utils.cancel_order(self, token=user1, data=({
            'id': user1_sellN_order_id,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], "order canceled")

        # Try and place a small order again, we now have plenty available again, so it succeeds
        user1_sellO_volume = 100000
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sellO_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(available_for_trading, content['data']['funds']['available'])
        self.assertEqual(content['status'], "order accepted")

        # User 2 buys the sell order
        user2_buyO_volume = 100000
        response = order.utils.place_order(self, token=user2, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': user1_sellO_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(len(content['data']['trades']), 1)

        # User 2 turns around and sells it back again
        user2_sellP_volume = 100000
        response = order.utils.place_order(self, token=user2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user2_sellP_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        self.assertEqual(content['status'], "order accepted")
        # User 1 already has an open order, filling this
        self.assertEqual(len(content['data']['trades']), 1)

        # Set an impossible volume, this will fail
        user1_sellN_volume = 50000000000000
        response = order.utils.place_order(self, token=user1, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': user1_sellN_volume,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "insufficient funds")
        #pprint(content['data'])
        # A trade out and then back in results in less available funds, because the exchange took fees.
        self.assertLess(content['data']['funds']['available'], available_for_trading)

    def test_trade_timeinforce(self):
        """
        Verify order expires after timeinforce passes

        Endpoint:
            POST `/api/order/create/`

        Place an order, then confirm it expires after the timeinforce passes.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)

        # Add a buy order to the orderbook. Buying a cryptopair means buying the base currency. So, this is a trade of
        # XLT for XTN.
        cryptopair = 'XTN-XLT'
        buy_volume = 1200000
        buy_limit_price = 13800000000
        buy_timeinforce = 2
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume,
            'limit_price': buy_limit_price,
            'timeinforce': buy_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data']['order'])
        '''
        {'base_currency': 'XTN',
         'canceled': False,
         'cryptopair': 'XTN-XLT',
         'description': 'ask XTN for XLT',
         'fee': 6000,
         'filled': False,
         'id': 'd0557c36-56e4-4d5b-bb4f-64f80c1bd7e3',
         'label': '',
         'limit_price': 13800000000,
         'open': True,
         'original_volume': 1200000,
         'quote_currency': 'XLT',
         'side': 'buy',
         'timeinforce': '2019-02-05T07:46:09.306726',
         'volume': 1200000,
         'wallet': 'b5c0e449-89fa-4d5f-bc03-5d78e121d0ae'}
        '''
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['description'], "ask XTN for XLT")
        self.assertEqual(content['data']['order']['volume'], buy_volume)
        self.assertEqual(content['data']['order']['open'], True)
        # Importantly, no trades are made when the order is placed. This is a given, as this is the first trade in an
        # otherwise empty trading engine.
        self.assertEqual(content['data']['trades'], [])

        # No orders have been filled, so our bid shows up in the orderbook.
        # /api/public/XTN-XLT/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair=cryptopair)
        content = response.data
        #pprint(content)
        '''
        {'code': 200,
         'data': {'asks': [], 'bids': [[13800000000, 1200000]]},
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orderbook'}
        '''
        # There's currently on open order.
        self.assertEqual(len(content['data']['bids']), 1)

        # Confirm that our order shows up in our order history
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data'])
        '''
        [{'base_currency': 'XTN',
          'canceled': False,
          'created': '2019-02-05T07:53:03.503272Z',
          'cryptopair': 'XTN-XLT',
          'description': 'ask XTN for XLT',
          'fee': 6000,
          'filled': 0,
          'id': '717cb854-712b-4a30-891a-c6c3fa0c3036',
          'label': '',
          'limit_price': 13800000000,
          'modified': '2019-02-05T07:53:03.503308Z',
          'open': True,
          'original_volume': 1200000,
          'quote_currency': 'XLT',
          'side': True,
          'timeinforce': '2019-02-05T07:53:05.497074Z',
          'volume': 1200000,
          'wallet': 'Wallet object (1ea8bc83-a60b-425b-b0ad-2112fffe1e2a)'}]
        '''
        # There's currently one trade in our history.
        self.assertEqual(len(content['data']), 1)
        # The order is still open, and has not been canceled
        self.assertEqual(content['data'][0]['open'], True)
        self.assertEqual(content['data'][0]['canceled'], False)

        # Invoke timeinforce admin command to expire orders
        out = StringIO()
        call_command('timeinforce', stdout=out)
        #pprint(out.getvalue())
        # No orders are expired, timeinforce has not yet elapsed
        self.assertIn('expired 0 orders', out.getvalue())

        # Our order is not yet expired, and still shows up in the orderbook.
        # /api/public/XTN-XLT/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair=cryptopair)
        content = response.data
        #pprint(content)
        self.assertEqual(len(content['data']['bids']), 1)

        # Wait timeinforce seconds so we can expire the order
        time.sleep(buy_timeinforce)

        # Invoke timeinforce admin command to expire orders
        out = StringIO()
        call_command('timeinforce', stdout=out)
        #pprint(out.getvalue())
        # No orders are expired, timeinforce has not yet elapsed
        self.assertIn('expired 1 orders', out.getvalue())

        # Our order has expired, it is no longer in the orderbook
        # /api/public/XTN-XLT/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair=cryptopair)
        content = response.data
        #pprint(content)
        '''
        {'code': 200,
         'data': {'asks': [], 'bids': []},
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orderbook'}
        '''
        self.assertEqual(len(content['data']['bids']), 0)

        # Confirm that our order shows up as closed and expired in our order history
        response = order.utils.order_history(self, token=token1, data=({
            'cryptopair': cryptopair,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data'])
        '''
        [{'base_currency': 'XTN',
          'canceled': True,
          'created': '2019-02-05T08:16:14.252664Z',
          'cryptopair': 'XTN-XLT',
          'description': 'ask XTN for XLT',
          'fee': 6000,
          'filled': 0,
          'id': '6cf24145-e134-4022-a83e-c6d4c394d6ec',
          'label': '',
          'limit_price': 13800000000,
          'modified': '2019-02-05T08:16:16.381491Z',
          'open': False,
          'original_volume': 1200000,
          'quote_currency': 'XLT',
          'side': True,
          'timeinforce': '2019-02-05T08:16:16.246264Z',
          'volume': 1200000,
          'wallet': 'Wallet object (eee3f440-e3f0-4114-afd2-f2e1bddb8b3a)'}]
        '''
        # There's currently one trade in our history.
        self.assertEqual(len(content['data']), 1)
        # The order is still open, and has not been canceled
        self.assertEqual(content['data'][0]['open'], False)
        self.assertEqual(content['data'][0]['canceled'], True)

    def test_trade_settle(self):
        """
        Verify we can settle trades.

        Initiate a trade with two orders, then settle the trade.
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(
            self, add_valid_xlt=True, add_valid_xtn=True, add_valid_xdt=True)

        token3, xtn_wallet_id3, xlt_wallet_id3, xdt_wallet_id3, \
        token4, xtn_wallet_id4, xlt_wallet_id4, xdt_wallet_id4 = order.utils.create_test_trading_wallets(
            self, add_valid_xlt=True, add_valid_xtn=True, add_valid_xdt=True,
            email1="c@example.com", email2="d@example.com")

        # Add a buy order to the orderbook. Buying a cryptopair means buying the base currency. So, this is a trade of
        # XLT for XTN.
        cryptopair1 = 'XTN-XLT'
        buy_volume1 = 1200000
        buy_limit_price1 = 13800000000
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair1,
            'volume': buy_volume1,
            'limit_price': buy_limit_price1,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data']['order'])
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Add another buy order to the orderbook. Buying the base currency (XLT)
        # with the quote currency (DOGE).
        cryptopair2 = 'XLT-XDT'
        buy_volume2 = 30000000
        buy_limit_price2 = 2951686000000
        # /api/order/create/
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair2,
            'volume': buy_volume2,
            'limit_price': buy_limit_price2,
        }))
        content = json.loads(response.content)
        #pprint(content['data']['order'])
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Add another buy order to the orderbook. Buying the base currency (XLT)
        # with the quote currency (DOGE) from another user
        buy_volume3 = 45000000
        buy_limit_price3 = 3009555000000
        # /api/order/create/
        response = order.utils.place_order(self, token=token3, data=({
            'side': 'buy',
            'cryptopair': cryptopair2,
            'volume': buy_volume3,
            'limit_price': buy_limit_price3,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data']['order'])
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Add a matching sell order for the first buy bid, from user 2
        sell_volume1 = 200000
        # /api/order/create/
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair1,
            'volume': sell_volume1,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data'])

        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertEqual(len(content['data']['trades']), 1)

        # Add a matching sell order for the second buy bid, from user 3
        sell_volume2 = 200000000
        # /api/order/create/
        response = order.utils.place_order(self, token=token4, data=({
            'side': 'sell',
            'cryptopair': cryptopair2,
            'volume': sell_volume2,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['data'])

        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['order']['filled'], 2)
        self.assertEqual(len(content['data']['trades']), 2)

        # Invoke settle admin command to settle trades.
        out = StringIO()
        call_command('settle', stdout=out)
        pprint(out.getvalue())
        self.assertIn('settled 6 orders', out.getvalue())

        # Invoke the settle admin command again, as currently we're failing to
        # settle this results in attempting to re-settle all 6 orders again.
        out = StringIO()
        call_command('settle', stdout=out)
        pprint(out.getvalue())
        self.assertIn('settled 6 orders', out.getvalue())
