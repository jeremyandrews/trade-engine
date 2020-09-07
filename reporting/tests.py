import json
from pprint import pprint
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from reporting.views import ReportingOrderbookView, ReportingTradesView, ReportingTickerView
import reporting.utils
import order.utils


class TradeTest(APITestCase):
    def setUp(self):
        """
        Clear cache so we don't have issues with throttling.
        """
        cache.clear()

    def test_ticker(self):
        """
        Test ticker output

        Endpoint:
            GET /api/public/<cryptopair>/ticker/

        The ticket shows realtime changes in the market, including:
         - details about the last trade
         - difference between the previous trade
         - aggregated details about the past 24 hours
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)
        # Create a buy order for XTN, selling XLT:
        cryptopair = 'XTN-XLT'
        buy_volume = 300000  # volume is specified in XLT, so this is an offer for 0.03 XLT
        buy_limit_price = 14200000000
        buy_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy_volume,
            'limit_price': buy_limit_price,
            'timeinforce': buy_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a buy order for XTN, selling XLT:
        buy2_volume = 10000  # volume is specified in XLT, so this is an offer for 0.000003 XLT
        buy2_limit_price = 14100000000
        buy2_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy2_volume,
            'limit_price': buy2_limit_price,
            'timeinforce': buy2_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a buy order for XTN, selling XLT:
        cryptopair = 'XTN-XLT'
        buy3_volume = 10000  # volume is specified in XLT, so this is an offer for 0.000003 XLT
        buy3_limit_price = 14000000000
        buy3_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy3_volume,
            'limit_price': buy3_limit_price,
            'timeinforce': buy3_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a buy order for XTN, selling XLT:
        cryptopair = 'XTN-XLT'
        buy4_volume = 12000
        buy4_limit_price = 14195000000
        buy4_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy4_volume,
            'limit_price': buy4_limit_price,
            'timeinforce': buy4_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a sell order for XTN, buying XLT:
        cryptopair = 'XTN-XLT'
        sell_volume = 5000000  # volume is specified in XLT, so this is a an ask for 0.0005 XDT
        sell_limit_price = 14150000000  # willing to trade 1 XTN for at least 141.5 XLT
        sell_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
            'timeinforce': sell_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        # Our Sell matches two buys.
        #
        # We use a basic FIFO (price-time-priority) matching algorithm: so matches are against the highest orders first.
        # In the case of multiple orders at the same price, the oldest order is matched first.
        #
        # From https://www.investopedia.com/terms/m/matchingorders.asp:
        #   "Under a basic FIFO algorithm, or price-time-priority algorithm, the earliest active buy order at the
        #   highest price takes priority over any subsequent order at that price, which in turn takes priority over any
        #   active buy order at a lower price. For example, if a buy order for 200 shares of stock at $90 per share
        #   precedes an order for 50 shares of the same stock at the same price, the system must match the entire
        #   200-share order to one or more sell orders before beginning to match any portion of the 50-share order."
        #
        # We match the highest buy order first, which is buy1 with a limit price of 142.0. The trade is for all 300000
        # XLT available in the matched buy order (as our sell is much larger). Each sides of the trade see the same fee,
        # as both sides have to trade the same amount of cryptopair.
        #
        # The second match is highest remaining buy order, which is buy4, with a limit price of 141.95. Again we trade
        # the entire 0.00012 XLT that's available.
        #
        # There are no more buys with high enough prices to match, so the remainder of our Sell order sits on the books
        # waiting to be fulfilled.
        #pprint(content)
        '''
        {'code': 200,
         'data': {'estimated_value': {'XLT': 5000000,
                                      'XLT-fee': 4975000,
                                      'XTN': 35335,
                                      'XTN-fee': 35159},
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
                            'fee': 25000,
                            'filled': 2,
                            'label': '',
                            'limit_price': 14150000000,
                            'open': True,
                            'original_volume': 5000000,
                            'quote_currency': 'XLT',
                            'settled': False,
                            'side': 'sell',
                            'timeinforce': 86400,
                            'volume': 4688000,
                            'wallet': '948ac713-a338-442c-9c08-faede1e157f5'},
                  'trades': [{'base_volume': 2112,
                              'buy_fee': 1500,
                              'buy_order': '4b68eabe-3aa7-461d-a713-142f70d3ec6e',
                              'cryptopair': 'XTN-XLT',
                              'description': None,
                              'id': 1,
                              'label': '',
                              'price': 14200000000,
                              'sell_fee': 1500,
                              'sell_order': 'e8de08c7-7f14-4fe4-be60-ba142359058e',
                              'settled': False,
                              'volume': 300000},
                             {'base_volume': 84,
                              'buy_fee': 60,
                              'buy_order': '3d333210-998a-4d22-9421-8ad69194c78f',
                              'cryptopair': 'XTN-XLT',
                              'description': None,
                              'id': 2,
                              'label': '',
                              'price': 14195000000,
                              'sell_fee': 60,
                              'sell_order': 'e8de08c7-7f14-4fe4-be60-ba142359058e',
                              'settled': False,
                              'volume': 12000}]},
         'debug': {'request': {'cryptopair': 'XTN-XLT',
                               'limit_price': 14150000000,
                               'side': 'sell',
                               'timeinforce': 86400,
                               'volume': 5000000}},
         'status': 'order accepted'}
        '''
        self.assertEqual(len(content['data']['trades']), 2)
        self.assertEqual(content['data']['trades'][0]['volume'], buy_volume)
        self.assertEqual(content['data']['trades'][1]['volume'], buy4_volume)
        # Our order has been partially filled twice: it remains open, but the filled counter has been properly
        # incremented. The volume of our order was appropriately reduced by the volume of the filled trades, but the
        # original_volume still reflects our original order.
        self.assertEqual(content['data']['order']['open'], True)
        self.assertEqual(content['data']['order']['filled'], 2)
        self.assertEqual(content['data']['order']['volume'], sell_volume - buy_volume - buy4_volume)
        self.assertEqual(content['data']['order']['original_volume'], sell_volume)

        # Now that we've confirmed our orders were matched as we expected, let's confirm that the ticker properly
        # reflects the trade activity.
        # /api/public/<cryptopair>/ticker/
        response = reporting.utils.view_ticker(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        # Details are broken down between the Base currency and the Quote currency. The base currency values are
        # recorded with each trade, and are therefore pulled directly out of the database. Volume traded is determined
        # at trade time based on the conversion rate used for that specific trace (the "price").
        #
        # In the quote section are the values we send to the API. The ticker "price" is the price of the last trade of
        # the specified cryptopair. For us, that's the price of our first buy order, which was our last matching trade
        # so far. Difference is the price difference between the last trade, and the trade before it: in our case, the
        # price is increasing so this is a positive number. So far we've only had two trades ever in this cryptopair,
        # so our 24 hour high is the price of the last trade, and our 24 hour low is the price of the first trade.
        # Volume is the size of the last trade, whereas 24 hour volume is currently the size of both trades combined.
        # Finally, ask represents the lowest Buy on the books, while bid represents the highest Sell on the books.
        #pprint(content)
        '''
        {'code': 200,
         'data': {'base': {'24h_volume': 2196, 'symbol': 'XTN', 'volume': 84},
                  'last_timestamp': 1546958581.260417,
                  'quote': {'24h_high': 14200000000,
                            '24h_low': 14195000000,
                            '24h_volume': 312000,
                            'ask': 14150000000,
                            'bid': 14100000000,
                            'difference': -5000000,
                            'price': 14195000000,
                            'symbol': 'XLT',
                            'volume': 12000},
                  'symbol': 'XTN-XLT'},
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT ticker'}
        '''
        self.assertEqual(content['data']['quote']['price'], buy4_limit_price)
        self.assertEqual(content['data']['quote']['difference'], buy4_limit_price - buy_limit_price)
        self.assertEqual(content['data']['quote']['24h_high'], buy_limit_price)
        self.assertEqual(content['data']['quote']['24h_low'], buy4_limit_price)
        self.assertEqual(content['data']['quote']['volume'], buy4_volume)
        self.assertEqual(content['data']['quote']['24h_volume'], buy_volume + buy4_volume)
        # The current ask is the lowest sell price
        self.assertEqual(content['data']['quote']['ask'], sell_limit_price)
        # The current bid is the highest buy price
        self.assertEqual(content['data']['quote']['bid'], buy2_limit_price)

        buy4_base_volume = int(buy4_volume / buy4_limit_price * 100000000)
        self.assertEqual(content['data']['base']['volume'], buy4_base_volume)
        base_volume = buy4_base_volume + int(buy_volume / buy_limit_price * 100000000)
        self.assertEqual(content['data']['base']['24h_volume'], base_volume)

        # Create another sell order for XTN, buying XLT.
        cryptopair = 'XTN-XLT'
        sell2_volume = 12000
        sell2_limit_price = 14149995000
        sell2_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell2_volume,
            'limit_price': sell2_limit_price,
            'timeinforce': sell2_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        # No trades are made, as our asking price is higher than the lowest bid.
        self.assertEqual(len(content['data']['trades']), 0)

        # /api/public/<cryptopair>/ticker/
        response = reporting.utils.view_ticker(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        # However, we do affect the ticker as we now have the lowest ask price. Nothing else should change on the
        # ticker.
        #pprint(content['data'])
        '''
        {'base': {'24h_volume': 2196, 'symbol': 'XTN', 'volume': 84},
         'last_timestamp': 1546958960.216057,
         'quote': {'24h_high': 14200000000,
                   '24h_low': 14195000000,
                   '24h_volume': 312000,
                   'ask': 14149995000,
                   'bid': 14100000000,
                   'difference': -5000000,
                   'price': 14195000000,
                   'symbol': 'XLT',
                   'volume': 12000},
         'symbol': 'XTN-XLT'}
        '''
        #
        # This changes:
        self.assertEqual(content['data']['quote']['ask'], sell2_limit_price)
        # This stays the same:
        self.assertEqual(content['data']['quote']['price'], buy4_limit_price)
        self.assertEqual(content['data']['quote']['difference'], buy4_limit_price - buy_limit_price)
        self.assertEqual(content['data']['quote']['24h_high'], buy_limit_price)
        self.assertEqual(content['data']['quote']['24h_low'], buy4_limit_price)
        self.assertEqual(content['data']['quote']['volume'], buy4_volume)
        self.assertEqual(content['data']['quote']['24h_volume'], buy_volume + buy4_volume)
        self.assertEqual(content['data']['quote']['bid'], buy2_limit_price)

        # Create a market sell order for XTN, buying XLT:
        cryptopair = 'XTN-XLT'
        sell3_volume = 300
        sell3_limit_price = 0
        sell3_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell3_volume,
            'limit_price': sell3_limit_price,
            'timeinforce': sell3_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        #pprint(content['data']['order'])
        '''
            {'base_currency': 'XTN',
             'canceled': False,
             'cryptopair': 'XTN-XLT',
             'description': 'offer XTN for XLT',
             'fee': 1,
             'filled': 1,
             'label': '',
             'limit_price': 0,
             'open': False,
             'original_volume': 300,
             'quote_currency': 'XLT',
             'settled': False,
             'side': 'sell',
             'timeinforce': 86400,
             'volume': 300,
             'wallet': '49bcf6de-8b2f-4cc9-bd30-a6209d7ae476'}
         '''
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['filled'], 1)
        #pprint(content['data']['trades'])
        '''
        [{'base_volume': 2,
          'buy_fee': 1,
          'buy_order': 'b8c72c72-ae97-4917-8329-7f152d903f9f',
          'cryptopair': 'XTN-XLT',
          'description': None,
          'id': 3,
          'label': '',
          'price': 14100000000,
          'sell_fee': 1,
          'sell_order': '20da5a75-aad1-4013-8c2f-e3d2657be51c',
          'settled': False,
          'volume': 300}]
        '''
        # As a market order against a non-empty orderbook, this trade is assured:
        self.assertEqual(len(content['data']['trades']), 1)
        self.assertEqual(content['data']['trades'][0]['volume'], sell3_volume)

        # /api/public/<cryptopair>/ticker/
        response = reporting.utils.view_ticker(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content['data'])
        '''
        {'base': {'24h_volume': 2198, 'symbol': 'XTN', 'volume': 2},
         'last_timestamp': 1546959137.88693,
         'quote': {'24h_high': 14200000000,
                   '24h_low': 14100000000,
                   '24h_volume': 312300,
                   'ask': 14149995000,
                   'bid': 14100000000,
                   'difference': -95000000,
                   'price': 14100000000,
                   'symbol': 'XLT',
                   'volume': 300},
         'symbol': 'XTN-XLT'}
        '''
        # Our trade made several changes visible in the ticker:
        #  - our trade's volume of 300 shows up
        #  - the 24 hour volume increased by 300
        #  - our market trade matched the highest open buy order, which is buy2 (at 141.0)
        #  - our market trade caused a downward trend in the market, difference is negative
        #  - our market trade was the lowest of the past 24 hours (24h_low)

        # This changed:
        self.assertEqual(content['data']['quote']['volume'], sell3_volume)
        self.assertEqual(content['data']['quote']['24h_volume'], buy_volume + buy4_volume + sell3_volume)
        self.assertEqual(content['data']['quote']['price'], buy2_limit_price)
        self.assertEqual(content['data']['quote']['difference'], buy2_limit_price - buy4_limit_price)
        self.assertEqual(content['data']['quote']['24h_low'], buy2_limit_price)
        # This stayed the same:
        self.assertEqual(content['data']['quote']['24h_high'], buy_limit_price)
        self.assertEqual(content['data']['quote']['ask'], sell2_limit_price)
        self.assertEqual(content['data']['quote']['bid'], buy2_limit_price)

        # Create a market buy order for XTN, buying XLT:
        cryptopair = 'XTN-XLT'
        buy5_volume = 25000
        buy5_limit_price = 0
        buy5_timeinforce = 0
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy5_volume,
            'limit_price': buy5_limit_price,
            'timeinforce': buy5_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        #pprint(content['data']['order'])
        '''
        {'base_currency': 'XTN',
         'canceled': False,
         'cryptopair': 'XTN-XLT',
         'description': 'ask XTN for XLT',
         'fee': 125,
         'filled': 1,
         'label': '',
         'limit_price': 0,
         'open': False,
         'original_volume': 25000,
         'quote_currency': 'XLT',
         'settled': False,
         'side': 'buy',
         'timeinforce': 0,
         'volume': 25000,
         'wallet': '8f64ce66-5583-4243-afb2-56912202af67'}
        '''
        # Market buy matches the open sell order which has enough volume to fulfill the buy.
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['filled'], 1)
        self.assertEqual(content['data']['order']['volume'], buy5_volume)
        #pprint(content['data']['trades'])
        '''
        [{'base_volume': 176,
          'buy_fee': 125,
          'buy_order': 'd742cacd-7beb-4333-a14f-5b5847799775',
          'cryptopair': 'XTN-XLT',
          'description': None,
          'id': 4,
          'label': '',
          'price': 14150000000,
          'sell_fee': 125,
          'sell_order': '9c4548c4-322b-4ed1-8372-3dc4f1fa788f',
          'settled': False,
          'volume': 25000}]
        '''
        self.assertEqual(len(content['data']['trades']), 1)
        self.assertEqual(content['data']['trades'][0]['price'], sell_limit_price)

        # /api/public/<cryptopair>/ticker/
        response = reporting.utils.view_ticker(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content['data'])
        '''
        {'base': {'24h_volume': 2374, 'symbol': 'XTN', 'volume': 176},
         'last_timestamp': 1546959908.391108,
         'quote': {'24h_high': 14200000000,
                   '24h_low': 14100000000,
                   '24h_volume': 337300,
                   'ask': 14149995000,
                   'bid': 14100000000,
                   'difference': 50000000,
                   'price': 14150000000,
                   'symbol': 'XLT',
                   'volume': 25000},
         'symbol': 'XTN-XLT'}
        '''
        # Our trade made several changes visible in the ticker:
        #  - our trade's volume of 25000 shows up
        #  - the 24 hour volume increased by 25000
        #  - our market trade matched the highest open sell order, which is sell1 (at 141.5)
        #  - our market trade caused an upward trend in the market, difference is positive

        # This changed:
        self.assertEqual(content['data']['quote']['volume'], buy5_volume)
        self.assertEqual(content['data']['base']['volume'], int(buy5_volume / sell_limit_price * 100000000))
        self.assertEqual(content['data']['quote']['24h_volume'], buy_volume + buy4_volume + sell3_volume + buy5_volume)
        self.assertEqual(content['data']['quote']['price'], sell_limit_price)
        self.assertEqual(content['data']['quote']['difference'], sell_limit_price - buy2_limit_price)
        # This stayed the same:
        self.assertEqual(content['data']['quote']['24h_low'], buy2_limit_price)
        self.assertEqual(content['data']['quote']['24h_high'], buy_limit_price)
        self.assertEqual(content['data']['quote']['ask'], sell2_limit_price)
        self.assertEqual(content['data']['quote']['bid'], buy2_limit_price)

        # Create another sell order for XTN, buying XLT.
        cryptopair = 'XTN-XLT'
        sell4_volume = 12345
        sell4_limit_price = 13000000000
        sell4_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell4_volume,
            'limit_price': sell4_limit_price,
            'timeinforce': sell4_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        #pprint(content['data']['order'])
        '''
        {'base_currency': 'XTN',
         'canceled': False,
         'cryptopair': 'XTN-XLT',
         'description': 'offer XTN for XLT',
         'fee': 61,
         'filled': 2,
         'label': '',
         'limit_price': 13000000000,
         'open': False,
         'original_volume': 12345,
         'quote_currency': 'XLT',
         'settled': False,
         'side': 'sell',
         'timeinforce': 86400,
         'volume': 2645,
         'wallet': 'b9ac8a95-a8ac-42b1-b49a-01fbb294ed5e'}
        '''
        # Our offer is very low so it's completely filled and it is ordered. The order volume was reduced after the
        # first trade, so it does not equal the original volume.
        self.assertEqual(content['data']['order']['open'], False)
        self.assertEqual(content['data']['order']['filled'], 2)
        self.assertNotEqual(content['data']['order']['volume'], content['data']['order']['original_volume'])
        #pprint(content['data']['trades'])
        '''
        [{'base_volume': 68,
          'buy_fee': 48,
          'buy_order': 'e14e9604-e936-4c54-ab47-5ba09ea1e8c0',
          'cryptopair': 'XTN-XLT',
          'description': None,
          'id': 5,
          'label': '',
          'price': 14100000000,
          'sell_fee': 48,
          'sell_order': '47221300-1dc1-4392-8ae3-a94ce75758f0',
          'settled': False,
          'volume': 9700},
         {'base_volume': 18,
          'buy_fee': 13,
          'buy_order': '541972f0-4d9c-46ac-807b-8f1820104ed7',
          'cryptopair': 'XTN-XLT',
          'description': None,
          'id': 6,
          'label': '',
          'price': 14000000000,
          'sell_fee': 13,
          'sell_order': '47221300-1dc1-4392-8ae3-a94ce75758f0',
          'settled': False,
          'volume': 2645}]
        '''
        # We match the highest bid first. The two trades together match the volume of our order.
        self.assertEqual(len(content['data']['trades']), 2)
        self.assertNotEqual(content['data']['trades'][0]['volume'] + content['data']['trades'][1]['volume'],
                            content['data']['order']['volume'])
        trade2_volume = content['data']['trades'][1]['volume']

        # /api/public/<cryptopair>/ticker/
        response = reporting.utils.view_ticker(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        # We also affect the ticker.
        #pprint(content['data'])
        '''
        {'base': {'24h_volume': 2460, 'symbol': 'XTN', 'volume': 18},
         'last_timestamp': 1546960636.968485,
         'quote': {'24h_high': 14200000000,
                   '24h_low': 14000000000,
                   '24h_volume': 349645,
                   'ask': 14149995000,
                   'bid': 14000000000,
                   'difference': -100000000,
                   'price': 14000000000,
                   'symbol': 'XLT',
                   'volume': 2645},
         'symbol': 'XTN-XLT'}
        '''
        # Our trade made several visible changes in the ticker:
        #  - our trade's volume shows up
        #  - the 24 hour volume increases
        #  - our trade matched the highest open sell order (140.0)
        #  - our trade caused a downward trend in the market, difference is negative
        #  - our trade caused the market to hit a new 24 hour low (140.0)
        #  - our trade filled the previous highest bid, so a new lower bid shows up in the ticker

        # This changed:
        self.assertEqual(content['data']['quote']['volume'], trade2_volume)
        self.assertEqual(content['data']['base']['volume'], int(trade2_volume / buy3_limit_price * 100000000))
        self.assertEqual(content['data']['quote']['24h_volume'], buy_volume + buy4_volume + sell3_volume + buy5_volume
                         + sell4_volume)
        self.assertEqual(content['data']['quote']['price'], buy3_limit_price)
        self.assertEqual(content['data']['quote']['difference'], buy3_limit_price - buy2_limit_price)
        self.assertEqual(content['data']['quote']['24h_low'], buy3_limit_price)
        self.assertEqual(content['data']['quote']['bid'], buy3_limit_price)
        # This stayed the same:
        self.assertEqual(content['data']['quote']['24h_high'], buy_limit_price)
        self.assertEqual(content['data']['quote']['ask'], sell2_limit_price)

    def test_orderbook(self):
        """
        Verify orderbook endpoint.

        Endpoint:
            GET /api/public/<cryptopair>/orderbook/

        Each currency pair will expose all currently active orders through this endpoint. The data will be returned as
        two arrays named “bids” and “asks”. Each is an array of arrays in which the first element is the currency pair
        price (in quote currency), and the second element is the quantity (again, in quote currency).

        This is based on the requirements defined on this website:
          https://bitcoincharts.com/about/exchanges/

        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)

        # Create a buy order for XTN, selling XLT:
        buy_cryptopair = 'XTN-XLT'
        buy_volume = 300000  # volume is specified in XLT, so this is an offer for 0.03 XLT
        buy_limit_price = 13900000000  # willing to trade up to 139.0 XLT per XTN
        buy_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': buy_cryptopair,
            'volume': buy_volume,
            'limit_price': buy_limit_price,
            'timeinforce': buy_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a buy order for XTN, selling XLT:
        buy2_cryptopair = 'XTN-XLT'
        buy2_volume = 300  # volume is specified in XLT, so this is an offer for 0.000003 XLT
        buy2_limit_price = 14075000000  # willing to trade up to 140.75 per XTN
        buy2_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': buy2_cryptopair,
            'volume': buy2_volume,
            'limit_price': buy2_limit_price,
            'timeinforce': buy2_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a sell order for XTN, buying XLT:
        sell_cryptopair = 'XTN-XLT'
        sell_volume = 50000  # volume is specified in XLT, so this is a an ask for 0.0005 XDT
        sell_limit_price = 14150000000  # willing to trade 1 XTN for at least 141.5 XLT
        sell_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': sell_cryptopair,
            'volume': sell_volume,
            'limit_price': sell_limit_price,
            'timeinforce': sell_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a sell order for XTN, buying XLT:
        sell2_cryptopair = 'XTN-XLT'
        sell2_volume = 12000  # volume is specified in XLT, so this is a an ask for 0.00012 XDT
        sell2_limit_price = 14189995000  # willing to trade 1 XTN for at least 140.89995 XLT
        sell2_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': sell2_cryptopair,
            'volume': sell2_volume,
            'limit_price': sell2_limit_price,
            'timeinforce': sell2_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Create a sell order for XTN, buying XLT:
        sell3_cryptopair = 'XTN-XLT'
        sell3_volume = 300  # volume is specified in XLT, so this is a an ask for 0.000003 XDT
        sell3_limit_price = 14078000000  # willing to trade 1 XTN for at least 140.78 XLT
        sell3_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': sell3_cryptopair,
            'volume': sell3_volume,
            'limit_price': sell3_limit_price,
            'timeinforce': sell3_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Start by making a bad request:
        # /api/public/<cryptopair>/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair="NONE-SUCH")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 400,
         'data': {},
         'debug': {'invalid cryptopair': 'NONE-SUCH'},
         'status': 'cryptopair parameter must be set to one of: XTN-XLT, XTN-XDT, '
                   'XLT-XDT, BTC-LTC, BTC-DOGE, LTC-DOGE'}
        '''
        self.assertEqual(content['status'][:42], "cryptopair parameter must be set to one of")

        # Now make a valid request:
        # /api/public/<cryptopair>/orderbook/
        response = reporting.utils.view_orderbook(self, cryptopair="XTN-XLT")
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': {'asks': [[14078000000, 300],
                           [14150000000, 50000],
                           [14189995000, 12000]],
                  'bids': [[14075000000, 300], [13900000000, 300000]]},
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orderbook'}
        '''
        # None of our orders have been matched as trades, so all are open and visible in the orderbook. Currently there
        # are two open buy orders (bids), and three open sell orders (asks). Bids are ordered by highest limit price to
        # lowest limit price. Asks are ordered by lowest limit price to highest limit price.
        self.assertEqual(content['data']['bids'],
                         [
                             [buy2_limit_price, buy2_volume],
                             [buy_limit_price, buy_volume],
                         ])
        self.assertEqual(content['data']['asks'],
                         [
                             [sell3_limit_price, sell3_volume],
                             [sell_limit_price, sell_volume],
                             [sell2_limit_price, sell2_volume],
                         ])

        # @TODO, is there anyway to cause this error?
        # - Invalid `cryptopair`: `500 Internal Server Error`: status: "`regex failed on cryptopair`"

    def test_trades(self):
        """
        Verify trades endpoint.

        Endpoint:
            GET /api/public/<cryptopair>/trades/

        The exchange maintains a complete history of all trades for each cryptopair. This is exposed publicly through
        the trades endpoint.

        The format of data exposed through this endpoint is based on the requirements defined on this website:
          https://bitcoincharts.com/about/exchanges/
        """
        token1, xtn_wallet_id1, xlt_wallet_id1, xdt_wallet_id1, \
        token2, xtn_wallet_id2, xlt_wallet_id2, xdt_wallet_id2 = order.utils.create_test_trading_wallets(self, add_valid_xlt=True,
                                                                                             add_valid_xtn=True)

        # Create a limit buy order for XTN, selling XLT:
        cryptopair = 'XTN-XLT'
        buy1_volume = 100000
        buy1_limit_price = 14100000000
        buy1_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy1_volume,
            'limit_price': buy1_limit_price,
            'timeinforce': buy1_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        self.assertEqual(content['data']['trades'], [])

        # Confirm that there currently is no trade history.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orders'}
        '''
        # Currently there is no trade history for this cryptopair.
        self.assertEqual(content['status'], "%s orders" % cryptopair)
        self.assertEqual(content['data'], [])

        # Create a sell order for XTN, buying XLT:
        sell1_volume = 50000
        sell1_limit_price = 13900000000
        sell1_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell1_volume,
            'limit_price': sell1_limit_price,
            'timeinforce': sell1_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        # The sell order was matched with the buy order on the books.
        self.assertEqual(len(content['data']['trades']), 1)

        # Confirm that the trade now shows up in the trade history.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'amount': 50000,
                   'date': 1547027603.042455,
                   'id': 7,
                   'price': 14100000000}],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orders'}
        '''
        # There is now a single trade in the trade history for this cryptopair:
        self.assertEqual(content['status'], "%s orders" % cryptopair)
        self.assertEqual(len(content['data']), 1)
        self.assertEqual(content['data'][0]['amount'], sell1_volume)
        self.assertEqual(content['data'][0]['price'], buy1_limit_price)

        # Create a sell order for XTN, buying XLT:
        sell2_volume = 40000
        sell2_limit_price = 13950000000
        sell2_timeinforce = 86400
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell2_volume,
            'limit_price': sell2_limit_price,
            'timeinforce': sell2_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        # The sell order was matched with the buy order on the books.
        self.assertEqual(len(content['data']['trades']), 1)

        # Confirm that both trades now show up in the trade history.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'amount': 40000,
                   'date': 1547028018.726524,
                   'id': 8,
                   'price': 14100000000},
                  {'amount': 50000,
                   'date': 1547028018.402694,
                   'id': 7,
                   'price': 14100000000}],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orders'}
        '''
        # There is now a single trade in the trade history for this cryptopair:
        self.assertEqual(content['status'], "%s orders" % cryptopair)
        self.assertEqual(len(content['data']), 2)
        # Newest trade first:
        self.assertEqual(content['data'][0]['amount'], sell2_volume)
        self.assertEqual(content['data'][0]['price'], buy1_limit_price)
        # Oldest trade last:
        self.assertEqual(content['data'][1]['amount'], sell1_volume)
        self.assertEqual(content['data'][1]['price'], buy1_limit_price)

        # Create a new limit buy order for XTN, selling XLT, to sit on the orderbook.
        cryptopair = 'XTN-XLT'
        buy2_volume = 500000
        buy2_limit_price = 13900000000
        buy2_timeinforce = 86400
        response = order.utils.place_order(self, token=token1, data=({
            'side': 'buy',
            'cryptopair': cryptopair,
            'volume': buy2_volume,
            'limit_price': buy2_limit_price,
            'timeinforce': buy2_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        # There are no sells to fill the order, so there are no trades made.
        self.assertEqual(content['data']['trades'], [])

        # Confirm that trade history is unchanged.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'amount': 40000,
                   'date': 1547028018.726524,
                   'id': 8,
                   'price': 14100000000},
                  {'amount': 50000,
                   'date': 1547028018.402694,
                   'id': 7,
                   'price': 14100000000}],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orders'}
        '''
        # There is now a single trade in the trade history for this cryptopair:
        self.assertEqual(content['status'], "%s orders" % cryptopair)
        self.assertEqual(len(content['data']), 2)
        self.assertEqual(content['data'][0]['amount'], sell2_volume)
        self.assertEqual(content['data'][0]['price'], buy1_limit_price)
        self.assertEqual(content['data'][1]['amount'], sell1_volume)
        self.assertEqual(content['data'][1]['price'], buy1_limit_price)

        # Create a market sell order for XTN, buying XLT:
        sell3_volume = 75000
        sell3_limit_price = 0  # market order
        sell3_timeinforce = 0
        response = order.utils.place_order(self, token=token2, data=({
            'side': 'sell',
            'cryptopair': cryptopair,
            'volume': sell3_volume,
            'limit_price': sell3_limit_price,
            'timeinforce': sell3_timeinforce,
        }))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        self.assertEqual(content['status'], "order accepted")
        # The market sell order was matched with two buy order on the books.
        self.assertEqual(len(content['data']['trades']), 2)
        #pprint(content['data']['trades'])
        '''
        [{'base_volume': 70,
          'buy_fee': 50,
          'buy_order': '6a6b6f24-2055-43ed-bd8f-cabb8e2dfc96',
          'cryptopair': 'XTN-XLT',
          'description': None,
          'id': 9,
          'label': '',
          'price': 14100000000,
          'sell_fee': 50,
          'sell_order': 'f9617dfe-2037-4cbe-b583-f5e462dac5f1',
          'settled': False,
          'volume': 10000},
         {'base_volume': 467,
          'buy_fee': 325,
          'buy_order': 'f5590d9e-9b10-4e7d-8343-a522ef7cfc18',
          'cryptopair': 'XTN-XLT',
          'description': None,
          'id': 10,
          'label': '',
          'price': 13900000000,
          'sell_fee': 325,
          'sell_order': 'f9617dfe-2037-4cbe-b583-f5e462dac5f1',
          'settled': False,
          'volume': 65000}]
        '''
        trade1_price = content['data']['trades'][0]['price']
        trade1_volume = content['data']['trades'][0]['volume']
        trade2_price = content['data']['trades'][1]['price']
        trade2_volume = content['data']['trades'][1]['volume']

        # Confirm that all four trades now show up in the trade history.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'amount': 65000,
                   'date': 1547028410.712682,
                   'id': 10,
                   'price': 13900000000},
                  {'amount': 10000,
                   'date': 1547028410.708437,
                   'id': 9,
                   'price': 14100000000},
                  {'amount': 40000,
                   'date': 1547028410.149816,
                   'id': 8,
                   'price': 14100000000},
                  {'amount': 50000,
                   'date': 1547028409.848811,
                   'id': 7,
                   'price': 14100000000}],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'status': 'XTN-XLT orders'}
        '''
        # There are now four trades in the trade history for this cryptopair:
        self.assertEqual(content['status'], "%s orders" % cryptopair)
        self.assertEqual(len(content['data']), 4)
        # Newest trade first:
        self.assertEqual(content['data'][0]['amount'], trade2_volume)
        self.assertEqual(content['data'][0]['price'], trade2_price)
        self.assertEqual(content['data'][1]['amount'], trade1_volume)
        self.assertEqual(content['data'][1]['price'], trade1_price)
        self.assertEqual(content['data'][2]['amount'], sell2_volume)
        self.assertEqual(content['data'][2]['price'], buy1_limit_price)
        # Oldest trade last:
        self.assertEqual(content['data'][3]['amount'], sell1_volume)
        self.assertEqual(content['data'][3]['price'], buy1_limit_price)

        # Create 30 tiny market sell orders, to match with the open buy and create trades.
        for _ in range(0,30):
            sellN_volume = 1200
            response = order.utils.place_order(self, token=token2, data=({
                'side': 'sell',
                'cryptopair': cryptopair,
                'volume': sellN_volume,
            }))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = json.loads(response.content)
            self.assertEqual(content['status'], "order accepted")
            self.assertEqual(len(content['data']['trades']), 1)

        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content['pager'])
        '''
        {'count': 34,
         'next': 'http://testserver/api/public/XTN-XLT/trades/?limit=25&offset=25',
         'previous': None}
         '''
        # There is another page of results
        self.assertNotEqual(content['pager']['next'], None)
        # This is the first page, there is not a previous page of results
        self.assertEqual(content['pager']['previous'], None)
        # Grab the second to last id, and confirm using since filters all but one trade
        since_id = content['data'][1]['id']

        # Confirm that since is working correctly.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair, since=since_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [{'amount': 1200, 'date': 1547965542, 'id': 40, 'price': 13900000000}],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'pager': {'count': 1, 'next': None, 'previous': None},
         'status': 'XTN-XLT orders'}
        '''
        # Confirm that there's only one result
        self.assertEqual(len(content['data']), 1)
        # There is only one result, so no pager
        self.assertEqual(content['pager']['next'], None)
        self.assertEqual(content['pager']['previous'], None)
        # Grab the id from the only result
        since_id = content['data'][0]['id']

        # Confirm that if there are no new trades, we return an empty list.
        # /api/public/<cryptopair>/trades/
        response = reporting.utils.view_trades(self, cryptopair=cryptopair, since=since_id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = json.loads(response.content)
        #pprint(content)
        '''
        {'code': 200,
         'data': [],
         'debug': {'base_currency': 'XTN',
                   'cryptopair': 'XTN-XLT',
                   'quote_currency': 'XLT'},
         'pager': {'count': 0, 'next': None, 'previous': None},
         'status': 'XTN-XLT orders'}
        '''
        # Confirm that there are no results.
        self.assertEqual(len(content['data']), 0)
        # There are no results, so no pager
        self.assertEqual(content['pager']['next'], None)
        self.assertEqual(content['pager']['previous'], None)
