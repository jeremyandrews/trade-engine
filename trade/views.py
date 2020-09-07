from django.forms.models import model_to_dict
from django.db.models import Q
from rest_framework import permissions, status, generics
from rest_framework.response import Response

from django.conf import settings
from trade.models import Trade
from trade.serializers import TradeSerializer
from order.models import Order
from wallet.models import Wallet
from otp import permissions as totp_permissions
import order.utils
import web.pagination


class TradeHistoryView(generics.GenericAPIView):
    """
    Use this endpoint to view all a user's trades.

    Required parameters:
     - cryptopair (defined in web.settings, such as "BTC-LTC" or "LTC-DOGE")
    """
    model = Trade
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated, totp_permissions.IsOtpVerified]
    pagination_class = web.pagination.Pagination

    def post(self, request, format=None):
        cryptopair, valid = order.utils.get_cryptopair(request, is_required=False)
        if valid is not True:
            # If valid is not True, cryptopair is a JSON-formatted error: abort!
            return Response(cryptopair, status=valid)

        user_trades = Trade.objects.filter(
            Q(buy_order__wallet__user=request.user.id, buy_order__filled__gt=0) |
            Q(sell_order__wallet__user=request.user.id, sell_order__filled__gt=0))

        if cryptopair:
            data_status = "%s history" % cryptopair
            user_trades = user_trades.filter(cryptopair=cryptopair)
        else:
            data_status = "all history"

        # Sort by id DESC, newest first, as trades are an autoincrementing integer.
        user_trades = user_trades.order_by('-id')

        # Find all of a user's trades.
        page = self.paginate_queryset(user_trades)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            #next_page = web.pagination.Pagination.get_next_link(serializer)
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
            serializer = self.get_serializer(user_trades, many=True)
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
