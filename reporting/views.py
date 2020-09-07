import time
import json
import re
import datetime

from django.conf import settings
from rest_framework import views, permissions, status, generics
from rest_framework.response import Response
from django.db import connection
import requests
from django.db.models import Sum, Max, Min

from address.models import Address
from order.models import Order
from trade.models import Trade
import reporting.utils
from trade.serializers import ReportingTradeSerializer
import app.pagination


def split_pair(cryptopair):
    cryptopairs = settings.CRYPTOPAIRS.keys()
    if cryptopair not in cryptopairs:
        status_code = status.HTTP_400_BAD_REQUEST
        data = {
            "status": "cryptopair parameter must be set to one of: %s" % ", ".join(cryptopairs),
            "code": status_code,
            "debug": {
                "invalid cryptopair": cryptopair,
            },
            "data": {},
        }
        return data, None, status_code

    try:
        match = re.search(r'([A-Z]{1,16})-([A-Z]{1,16})', cryptopair)
        base_currency = match.group(1)
        quote_currency = match.group(2)
    except Exception as e:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        data = {
            "status": "regex failed on cryptopair",
            "code": status_code,
            "debug": {
                "cryptopair": cryptopair,
                "error": e,
            },
            "data": {},
        }
        return data, None, status_code

    return base_currency, quote_currency, True

class ReportingBlockView(views.APIView):
    """
    This endpoint is for reporting new block statistics
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        content = request.data

        # Broadcast new blocks
        try:
            data = {
                'recipient': None,
                # 'new block' or 'orphan block'
                'type': content['event'],
                'data': {
                    'type': content['type'],
                    'symbol': content['symbol'],
                    'height': content['height'],
                    'hash': content['hash'],
                    'timestamp': content['timestamp'],
                },
                'timestamp': time.time(),
            }
            reporting.utils.notify_middleware(data)

        except Exception as e:
            print("Failed to broadcast new block: %s" % e)

        # Notify users if their wallets had activity
        addresses = content['addresses'].split(',')
        for address in addresses:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT wwu.spauser_id, aa.wallet_id FROM address_address AS aa LEFT JOIN wallet_wallet_user AS wwu"
                    " ON aa.wallet_id = wwu.wallet_id WHERE %s IN (aa.p2pkh, aa.p2sh_p2wpkh, aa.bech32)", [address])
                try:
                    spauser_id, wallet_id = cursor.fetchone()

                    wallet_detail = {
                        'id': str(wallet_id),
                        'currencycode': content['symbol'],
                        'balance': 0,
                        'address_count': 0,
                        '404_count': 0,
                        'error': [],
                        'error_count': 0,
                    }

                    for address_in_wallet in Address.objects.filter(wallet=wallet_id).order_by('created'):
                        for an_address in [address_in_wallet.p2pkh, address_in_wallet.p2sh_p2wpkh,
                                           address_in_wallet.bech32]:
                            if an_address:
                                wallet_detail['address_count'] += 1
                                url = '%s://%s:%d/api/address/%s/%s/unspent' % (settings.ADDRESSAPI['protocol'],
                                                                                settings.ADDRESSAPI['domain'],
                                                                                settings.ADDRESSAPI['port'],
                                                                                content['type'],
                                                                                an_address)
                                try:
                                    response = requests.get(url)
                                    addressapi = json.loads(response.content)
                                    if response.status_code == status.HTTP_404_NOT_FOUND:
                                        wallet_detail['404_count'] += 1
                                    else:
                                        wallet_detail['balance'] += addressapi['data']['balance']
                                except Exception as e:
                                    wallet_detail['error_count'] += 1
                                    wallet_detail['error'].append({
                                        'url': url,
                                        'code': response.status_code,
                                    })
                                    print("request to %s failed" % url)

                    data = {
                        'recipient': str(spauser_id),
                        'type': 'wallet activity',
                        'data': {
                            'event': content['event'],
                            'type': content['type'],
                            'symbol': content['symbol'],
                            'height': content['height'],
                            'hash': content['hash'],
                            'timestamp': content['timestamp'],
                            'address': address,
                            'wallet': wallet_detail,
                        },
                        'timestamp': time.time(),
                    }
                    reporting.utils.notify_middleware(data)

                except Exception as e:
                    # Address not in any of our wallets, continue to next
                    #print("Error: %s" % e)
                    pass

        status_code = status.HTTP_200_OK
        data = {
            "status": "block event received",
            "code": status_code,
            "debug": {
                "request": content,
            },
            "data": {},
        }
        return Response(data, status=status_code)

class ReportingMarketsView(views.APIView):
    """
    This endpoint is for viewing the orderbook for a given currency pair.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        markets = []
        debug = {
            'delisted': [],
        }
        cryptopairs = settings.CRYPTOPAIRS.keys()
        for cryptopair in cryptopairs:
            base_currency, quote_currency, valid = split_pair(cryptopair=cryptopair)
            if settings.CRYPTOPAIRS[cryptopair]["listed"]:
                markets.append({
                    'symbol': cryptopair,
                    'base': base_currency,
                    'quote': quote_currency,
                })
            else:
                debug['delisted'].append({
                    'symbol': cryptopair,
                    'base': base_currency,
                    'quote': quote_currency,
                })

        status_code = status.HTTP_200_OK
        data = {
            "status": "cryptopair markets",
            "code": status_code,
            "debug": debug,
            "data": {
                'markets': markets,
            },
        }
        return Response(data, status=status_code)


class ReportingOrderbookView(views.APIView):
    """
    This endpoint is for viewing the orderbook for a given currency pair.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pair, format=None):
        base_currency, quote_currency, valid = split_pair(cryptopair=pair)
        if valid is not True:
            # If valid is not True, base_currency is a JSON-formatted error: abort!
            return Response(base_currency, status=valid)

        bids = []
        # Look for open buy orders:
        for order in Order.objects.filter(base_currency=base_currency, quote_currency=quote_currency, side=True,
                                          open=True, limit_price__gt=0).order_by("-limit_price"):
            bids.append([
                order.limit_price, order.volume
            ])

        asks = []
        # Look for open sell orders:
        for order in Order.objects.filter(base_currency=base_currency, quote_currency=quote_currency, side=False,
                                          open=True, limit_price__gt=0).order_by("limit_price"):
            asks.append([
                order.limit_price, order.volume
            ])

        status_code = status.HTTP_200_OK
        data = {
            "status": "%s orderbook" % pair,
            "code": status_code,
            "debug": {
                "cryptopair": pair,
                "base_currency": base_currency,
                "quote_currency": quote_currency,
            },
            "data": {
                'bids': bids,
                'asks': asks,
            },
        }
        return Response(data, status=status_code)

class ReportingTradesView(generics.GenericAPIView):
    """
    This endpoint is for viewing all trades for a given currency pair.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ReportingTradeSerializer
    pagination_class = app.pagination.Pagination

    def get(self, request, pair, format=None):
        base_currency, quote_currency, valid = split_pair(cryptopair=pair)
        if valid is not True:
            # If valid is not True, base_currency is a JSON-formatted error: abort!
            return Response(base_currency, status=valid)

        since, valid = reporting.utils.get_since_parameter(request)
        if valid is not True:
            # If valid is not True, since is a JSON-formatted error: abort!
            return Response(since, status=valid)

        trades = Trade.objects.filter(cryptopair=pair)
        if since:
            trades = trades.filter(id__gt=since)

        ordered_trades = trades.order_by('-id')

        page = self.paginate_queryset(ordered_trades)

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
            serializer = self.get_serializer(ordered_trades, many=True)
            pager = {}

        status_code = status.HTTP_200_OK
        data = {
            "status": "%s orders" % pair,
            "code": status_code,
            "pager": pager,
            "debug": {
                "cryptopair": pair,
                "base_currency": base_currency,
                "quote_currency": quote_currency,
            },
            "data": serializer.data,
        }
        return Response(data, status=status_code)

class ReportingTickerView(views.APIView):
    """
    This endpoint is for viewing the ticker for a given currency pair.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pair, format=None):
        base_currency, quote_currency, valid = split_pair(cryptopair=pair)
        if valid is not True:
            # If valid is not True, base_currency is a JSON-formatted error: abort!
            return Response(base_currency, status=valid)

        trades = Trade.objects.filter(cryptopair=pair).order_by('-id')[0:2]
        last_trade = None
        previous_trade = None
        for counter, trade in enumerate(trades):
            if counter == 0:
                last_trade = trade
            else:
                assert(counter == 1)
                previous_trade = trade

        if last_trade:
            last_timestamp = last_trade.created.replace(tzinfo=datetime.timezone.utc).timestamp()
            last_quote_price = last_trade.price
            last_base_volume = int(last_trade.volume / last_trade.price * 100000000)
            aggregate_volume = Trade.objects \
                .filter(cryptopair=pair, created__lte=datetime.datetime.now() + datetime.timedelta(days=1))\
                .aggregate(Sum('volume'), Sum('base_volume'))
            quote_24h_volume = aggregate_volume['volume__sum']
            base_24h_volume = aggregate_volume['base_volume__sum']
            aggregate_price = Trade.objects \
                .filter(cryptopair=pair, created__lte=datetime.datetime.now() + datetime.timedelta(days=1)) \
                .aggregate(Min('price'), Max('price'))
            high = aggregate_price['price__max']
            low = aggregate_price['price__min']
            last_quote_volume = last_trade.volume

            ask_order = Order.objects.filter(side=False, cryptopair=pair, open=True,
                                             created__lte=datetime.datetime.now() + datetime.timedelta(days=1))\
                .aggregate(Min('limit_price'))
            bid_order = Order.objects.filter(side=True, cryptopair=pair, open=True,
                                             created__lte=datetime.datetime.now() + datetime.timedelta(days=1))\
                .aggregate(Max('limit_price'))
        else:
            last_timestamp = None
            last_base_volume = None
            last_quote_price = None
            base_24h_volume = None
            high = None
            low = None
            last_quote_volume = None
            quote_24h_volume = None

        if previous_trade:
            difference = last_trade.price - previous_trade.price
        else:
            difference = None

        try:
            ask = ask_order['limit_price__min']
        except:
            ask = None
        if ask == 0:
            ask = None

        try:
            bid = bid_order['limit_price__max']
        except:
            bid = None
        if bid == 0:
            bid = None

        status_code = status.HTTP_200_OK
        data = {
            "status": "%s ticker" % pair,
            "code": status_code,
            "debug": {
                "cryptopair": pair,
                "base_currency": base_currency,
                "quote_currency": quote_currency,
            },
            "data": {
                'symbol': pair,
                'last_timestamp': last_timestamp,
                'base': {
                    'symbol': base_currency,
                    'volume': last_base_volume,
                    '24h_volume': base_24h_volume,
                },
                'quote': {
                    'symbol': quote_currency,
                    'price': last_quote_price,
                    'difference': difference,
                    '24h_high': high,
                    '24h_low': low,
                    'ask': ask,
                    'bid': bid,
                    'volume': last_quote_volume,
                    '24h_volume': quote_24h_volume,
                },
            },
        }
        return Response(data, status=status_code)
