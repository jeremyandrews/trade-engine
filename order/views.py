import time
import uuid
import datetime

from django.conf import settings
from django.forms.models import model_to_dict
from rest_framework import views, permissions, status, generics
from rest_framework.response import Response

import order.utils
from .serializers import OrderSerializer
from .models import Order
import blockchain.utils
import wallet.utils
from wallet.models import Wallet
import trade.utils
from trade.models import Trade
from otp import permissions as totp_permissions
import reporting.utils
import app.pagination


class OrderCreateView(views.APIView):
    """
    Use this endpoint to place a new buy or sell order:
     - A buy is a trade of Quote currency for Base currency.
     - A sell is a trade of Base currency for Quote currency.

    Required parameters:
     - side ("buy" or "sell")
     - cryptopair (defined in app.settings, such as "BTC-LTC" or "LTC-DOGE")
     - volume (in satoshi, integer)

    Optional parameters:
     - limit_price (in satoshi, integer; if blank or 0 this is a market order)
     - timeinforce (in seconds, integer; if blank or 0 this order is good until canceled)
    """
    model = Order
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    # Orders can be placed with a POST to this API endpoint.
    def post(self, request, format=None):
        # Step 1: determine wallet from user + cryptopair + side
        user_id = request.user.id
        assert(user_id is not None)

        side, valid = order.utils.get_side(request)
        if valid is not True:
            # If status code is not True, side is a JSON-formatted error: abort!
            return Response(side, status=valid)

        cryptopair, valid = order.utils.get_cryptopair(request)
        if valid is not True:
            # If status code is not True, cryptopair is a JSON-formatted error: abort!
            return Response(cryptopair, status=valid)

        # Volume is always specified in Quote currency
        volume, valid = order.utils.get_volume(request)
        if valid is not True:
            # If status code is not True, volume is a JSON-formatted error: abort!
            return Response(volume, status=valid)

        # Limit_price is always specified in Quote currency
        limit_price, valid = order.utils.get_limit_price(request)
        if valid is not True:
            # If status code is not True, limit_price is a JSON-formatted error: abort!
            return Response(limit_price, status=valid)
        if not limit_price:
            market = True
        else:
            market = False

        timeinforce, valid = order.utils.get_timeinforce(request)
        if valid is not True:
            # If status code is not True, timeinforce is a JSON-formatted error: abort!
            return Response(timeinforce, status=valid)

        base_currency = settings.CRYPTOPAIRS[cryptopair]['base']
        quote_currency = settings.CRYPTOPAIRS[cryptopair]['quote']
        if side == 'buy':
            # A cryptopair buy is an ask for base currency, implicitly selling quote currency. Load user's quote
            # currency wallet to confirm it has sufficient funds to make this trade. (We assume one wallet per currency
            # per user.)
            description = 'ask %s for %s' % (base_currency, quote_currency)
            user_wallet = Wallet.objects.get(user=user_id, currencycode=quote_currency)
        else:
            # If not a buy, this has to be a sell.
            assert(side == 'sell')
            # A cryptopair sell is an offer for base currency, implicitly buying quote currency. Load user's base
            # currency wallet to confirm it has sufficient funds to make this trade. (Again, we assume one wallet per
            # currency per user.)
            description = 'offer %s for %s' % (base_currency, quote_currency)
            user_wallet = Wallet.objects.get(user=user_id, currencycode=base_currency)

        order_details = {
            'side': side,
            'cryptopair': cryptopair,
            'description': description,
            'base_currency': base_currency,
            'quote_currency': quote_currency,
            'volume': volume,
            'limit_price': limit_price,
            'market': market,
            'timeinforce': timeinforce,
            'timestamp': time.time(),
        }
        identifiers = {
            'trace_id': reporting.utils.generate_trace_id(),
            'user': user_id,
            'wallet': user_wallet.id,
            'wallet_symbol': user_wallet.currencycode,
        }

        reporting.utils.audit(message="order formatted correctly", details={
            'identifiers': identifiers,
            'order': order_details,
        })

        # Step 2: calculate fee
        fee_percent = order.utils.get_user_fee_percent(identifiers, request, user_id)
        fee_estimate = int(volume * fee_percent / 100)
        fee = {
            'percent': fee_percent,
            'estimate': fee_estimate,
            'symbol': quote_currency,
        }
        reporting.utils.audit(message="estimated fee for order", details={
            'identifiers': identifiers,
            'order': order_details,
            'fee': fee,
        })

        # @TODO: Wrap this all in a per-user lock: to avoid potential race conditions each user should only be able to
        # perform one trade-related operation at a time. __ suggests this should instead be solved with a
        # transaction.

        # Step 3: calculate users available balance for trading
        # 2a) We start with the balance on the block chain
        blockchain_balance, pending_balance, pending_details = \
            blockchain.utils.get_balance(identifiers=identifiers, user_wallet=user_wallet)
        funds = {
            'blockchain': {
                'balance': blockchain_balance,
                'pending': pending_balance,
                'pending_details': pending_details,
            }

        }
        reporting.utils.audit(message="loaded blockchain balance", details={
            'identifiers': identifiers,
            'order': order_details,
            'fee': fee,
            'funds': funds,
        })

        # 2b) Subtract any unsettled open orders or trades out of this wallet
        out_trades_balance = wallet.utils.get_unsettled_open_orders_or_filled_trades_out(identifiers=identifiers,
                                                                                        wallet=user_wallet)
        funds['balance_of_trades_out'] = out_trades_balance

        # 2c) Credit any unsettled trades into this wallet
        in_trades_balance = wallet.utils.get_unsettled_trades_in(identifiers=identifiers, wallet=user_wallet,
                                                                user_id=self.request.user.id)
        funds['balance_of_trades_in'] = in_trades_balance

        available_balance = blockchain_balance - out_trades_balance + in_trades_balance
        funds['available'] = available_balance
        funds['currency'] = user_wallet.currencycode
        reporting.utils.audit(message="calculated unsettled balance adjustments", details={
            'identifiers': identifiers,
            'order': order_details,
            'fee': fee,
            'funds': funds,
        })

        if market:
            try:
                last_trade, = Trade.objects.filter(cryptopair=cryptopair).order_by('-id')[:1]
                ratio = last_trade.price
            except:
                # There's no market price until there's been at least one trade. Until then, we blindly assume the
                # ration is 1:1.
                ratio = 100000000
        else:
            ratio = limit_price

        # Step 4: confirm user has value available for trade (fee is subtracted from traded volume, not additional)
        quote_minus_fee_currency = "%s-fee" % quote_currency
        base_currency_value = int(volume / ratio * 100000000)
        base_minus_fee_currency = "%s-fee" % base_currency
        estimated_value = {
            quote_currency: volume,
            quote_minus_fee_currency: volume - fee_estimate,
            base_currency: base_currency_value,
            base_minus_fee_currency: base_currency_value - int(fee_estimate / ratio * 100000000),
        }

        if volume > available_balance:
            status_code = status.HTTP_200_OK
            reporting.utils.audit(message="insufficient funds", details={
                'identifiers': identifiers,
                'order': order_details,
                'fee': fee,
                'funds': funds,
                'estimated_value': estimated_value,
            })
            data = {
                "status": "insufficient funds",
                "code": status_code,
                "debug": {
                    'identifiers': identifiers,
                },
                "data": {
                    'order': order_details,
                    'fee': fee,
                    'funds': funds,
                    'estimated_value': estimated_value,
                },
            }
            return Response(data, status=status_code)
        else:
            reporting.utils.audit(message="sufficient funds", details={
                'identifiers': identifiers,
                'order': order_details,
                'fee': fee,
                'funds': funds,
                'estimated_value': estimated_value,
            })

        # See order.models for boolean definition of side variable.
        if side == 'buy':
            side_boolean = True
        else:
            assert(side == 'sell')
            side_boolean = False

        reporting.utils.audit(message="placing order", details={
            'identifiers': identifiers,
            'order': order_details,
            'fee': fee,
            'funds': funds,
            'estimated_value': estimated_value,
            'details': {
                'wallet': user_wallet.id,
                'cryptopair': cryptopair,
                'side': side_boolean,
                'limit_price': limit_price,
                'volume': volume,
                'original_volume': volume,
                'fee': fee_estimate,
                'timeinforce': timeinforce,
                'open': True,
                'canceled': False,
                'filled': False,
            }
        })

        if timeinforce:
            timeinforce_datetime = datetime.datetime.now() + datetime.timedelta(seconds=timeinforce)
        else:
            timeinforce_datetime = None

        # Step 5: place the order
        new_order = Order(
            wallet=user_wallet,
            description=description,
            cryptopair=cryptopair,
            base_currency=base_currency,
            quote_currency=quote_currency,
            side=side_boolean,
            limit_price=limit_price,
            volume=volume,
            original_volume=volume,
            fee=fee_estimate,
            timeinforce=timeinforce_datetime,
            open=True,
            canceled=False,
            filled=False,
        )
        # .save() has no return value, so we run it after creating a new order
        new_order.save()
        new_order_dict = model_to_dict(new_order)
        new_order_dict['id'] = new_order.id
        # We store side as a boolean, but display as a string
        new_order_dict['side'] = side

        reporting.utils.audit(message="order placed", details={
            'identifiers': identifiers,
            'order': order_details,
            'fee': fee,
            'funds': funds,
            'estimated_value': estimated_value,
            'confirmation': new_order_dict,
        })

        # Step 6: find matching orders, if anyway, and process fulfillment immediately
        trades = trade.utils.match_order(identifiers=identifiers, order_to_match=new_order)
        if len(trades):
            # The order was at least partially filled: reload from the database
            new_order = Order.objects.get(id=new_order.id)
            new_order_dict = model_to_dict(new_order)
            # Restore boolean to string value
            new_order_dict['side'] = side

        status_code = status.HTTP_200_OK
        data = {
            "status": "order accepted",
            "code": status_code,
            "debug": {
                "request": self.request.data,
            },
            "data": {
                'order': new_order_dict,
                'funds': funds,
                'estimated_value': estimated_value,
                'trades': trades,
            }
        }
        return Response(data, status=status_code)

class OrderCancelView(views.APIView):
    """
    Use this endpoint to cancel an order (if not yet filled).

    Required parameters:
     - id: the unique identifier for the order to cancel
    """
    model = Order
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]

    def post(self, request, format=None):
        # @TODO: Wrap this all in a per-user lock: to avoid potential race conditions each user should only be able to
        # perform one trade-related operation at a time. __ suggests this should instead be solved with a
        # transaction.

        # Get validated UUID4 id from request
        order_id, valid = order.utils.get_order_id(request)
        if valid is not True:
            # If status code is not True, id is a JSON-formatted error: abort!
            return Response(order_id, status=valid)

        # Confirm order exists
        user_order = Order.objects.get(id=order_id)

        # Load the current user's wallet.
        if user_order.side is True:
            user_wallet = Wallet.objects.get(user=request.user.id, currencycode=user_order.quote_currency)
        elif user_order.side is False:
            user_wallet = Wallet.objects.get(user=request.user.id, currencycode=user_order.base_currency)

        # Verify that the order is from the current user's wallet.
        if user_order.wallet != user_wallet:
            status_code = status.HTTP_401_UNAUTHORIZED
            data = {
                "status": "access denied",
                "code": status_code,
                "debug": {
                    "request": self.request.data,
                },
                "data": {
                },
            }
            return Response(data, status=status_code)

        # Verify that the order is still open, and therefor can be canceled.
        if user_order.open is not True:
            if user_order.canceled is True:
                status_text = "order already canceled"
            else:
                assert(user_order.filled > 0)
                status_text = "order fully filled, unable to cancel"

            status_code = status.HTTP_200_OK
            order_dict = model_to_dict(user_order)
            data = {
                "status": status_text,
                "code": status_code,
                "debug": {
                    "request": self.request.data,
                },
                "data": {
                    "order": order_dict,
                },
            }
            return Response(data, status=status_code)

        # Cancel the order.
        user_order.open = False
        user_order.canceled = True
        user_order.save()

        # Determine if order was already partially filled.
        if user_order.filled > 0:
            status_text = "order partially filled, unfilled portion canceled"
        else:
            status_text = "order canceled"

        status_code = status.HTTP_200_OK
        order_dict = model_to_dict(user_order)
        data = {
            "status": status_text,
            "code": status_code,
            "debug": {
                "request": self.request.data,
            },
            "data": {
                "order": order_dict,
            },
        }
        return Response(data, status=status_code)

class OrderHistoryView(generics.GenericAPIView):
    """
    Use this endpoint to view all a user's orders: open, canceled, and filled.

    Optional parameters:
     - cryptopair (defined in app.settings, such as "BTC-LTC" or "LTC-DOGE")
     - open_filter: filter by True or False
     - canceled_filter: filter by True or False
     - side_filter: filter by buy or sell
    """
    model = Order
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]
    pagination_class = app.pagination.Pagination

    def post(self, request, format=None):
        cryptopair, valid = order.utils.get_cryptopair(request, is_required=False)
        if valid is not True:
            # If valid is not True, cryptopair is a JSON-formatted error: abort!
            return Response(cryptopair, status=valid)

        filter_open, valid = order.utils.get_open_filter(request)
        if valid is not True:
            # If valid is not True, filter_open is a JSON-formatted error: abort!
            return Response(filter_open, status=valid)

        filter_canceled, valid = order.utils.get_canceled_filter(request)
        if valid is not True:
            # If valid is not True, filter_canceled is a JSON-formatted error: abort!
            return Response(filter_canceled, status=valid)

        filter_side, valid = order.utils.get_side_filter(request)
        if valid is not True:
            # If valid is not True, filter_side is a JSON-formatted error: abort!
            return Response(filter_side, status=valid)
        else:
            # Map buy/sell to True/False as used in the database
            if filter_side == 'buy':
                filter_side = True
            elif filter_side == 'sell':
                filter_side = False

        if cryptopair:
            base_currency = settings.CRYPTOPAIRS[cryptopair]['base']
            base_wallet = Wallet.objects.get(user=request.user.id, currencycode=base_currency)

            quote_currency = settings.CRYPTOPAIRS[cryptopair]['quote']
            quote_wallet = Wallet.objects.get(user=request.user.id, currencycode=quote_currency)

            orders = Order.objects.filter(cryptopair=cryptopair, wallet__in=[base_wallet, quote_wallet])
            data_status = "%s history" % cryptopair
        else:
            orders = Order.objects.filter(wallet__user=request.user.id)
            data_status = "all history"
        # Optionally filter by open status
        if filter_open is not None:
            orders = orders.filter(open=filter_open)
        # Optionally filter by canceled status
        if filter_canceled is not None:
            orders = orders.filter(canceled=filter_canceled)
        # Optionally filter by side
        if filter_side is not None:
            orders = orders.filter(side=filter_side)

        user_orders = orders.order_by('-created')
        page = self.paginate_queryset(user_orders)

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
            serializer = self.get_serializer(user_orders, many=True)
            pager = {}

        status_code = status.HTTP_200_OK
        data = {
            "status": data_status,
            "code": status_code,
            "pager": pager,
            "debug": {
                "request": self.request.data,
            },
            "data": serializer.data,
        }
        return Response(data, status=status_code)
