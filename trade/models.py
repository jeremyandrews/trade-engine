from django.db import models

from order.models import Order


# When a buy and a sell order are matched, this creates a trade. A trade may
# only partially fulfill one of the orders involved. Once an order is completely
# filled, it gets closed.

# Not yet settled:
SETTLED_NONE            = 0
# The trade has been validated (sufficient balance, etc):
SETTLED_VALID           = 1
# We were unable to validate the trade, manual reviw required:
SETTLED_ERROR           = 2
# The trade has been sent to the blockchain:
SETTLED_PENDING         = 3
# The trade has sufficient confirmations on the blockchain:
SETTLED_COMPLETE        = 4

class Trade(models.Model):
    '''
    A trade is a (partially or completely) fulfilled order.
    '''
    id = models.BigAutoField(primary_key=True, editable=False)
    # A trade is comprised of an Buy (ask) and a Sell (offer)
    buy_order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="buy_order")
    buy_order_settled_in = models.PositiveSmallIntegerField(default=SETTLED_NONE)
    buy_order_settled_out = models.PositiveSmallIntegerField(default=SETTLED_NONE)
    sell_order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name="sell_order")
    sell_order_settled_in = models.PositiveSmallIntegerField(default=SETTLED_NONE)
    sell_order_settled_out = models.PositiveSmallIntegerField(default=SETTLED_NONE)
    cryptopair = models.CharField(max_length=33, default='')
    label = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    # The price of the trade in quote currency
    price = models.BigIntegerField(default=0)
    # How much quote currency, in satoshi, was traded
    volume = models.BigIntegerField(default=0)
    # How much base currency, in satoshi, was traded
    base_volume = models.BigIntegerField(default=0)
    # The fee charged, in quote currency.
    buy_fee = models.PositiveIntegerField(default=0)
    sell_fee = models.PositiveIntegerField(default=0)
    # Metadata
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True, editable=False)
    modified = models.DateTimeField(auto_now=True, null=True, blank=True, editable=False)
