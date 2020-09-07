import uuid
from django.db import models

from wallet.models import Wallet


class Order(models.Model):
    '''
    An order is an offer to buy or sell currency.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT)
    # User and Currency can be found through the link to the wallet.
    label = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    # The crypto pair being traded
    cryptopair = models.CharField(max_length=33, default='')
    base_currency = models.CharField(max_length=16, default='')
    quote_currency = models.CharField(max_length=16, default='')
    # true is a bid/buy order, false is an ask/sell order
    side = models.BooleanField(default=False)
    # limit orders, whether buy or sell, must specify the limit
    limit_price = models.BigIntegerField(default=0)
    # total currency, in satoshi, willing to trade
    volume = models.BigIntegerField(default=0)
    # if an order is partially fulfilled or fulfilled with multiple trades, the available volume reduces
    original_volume = models.BigIntegerField(default=0)
    # percentage fee, where percentage is the value of fee / 100, so 500 = 5%, 50 = .5%, 5 = .05%
    fee = models.PositiveIntegerField(default=0)
    # time in force, DateTime of when order expires
    timeinforce = models.DateTimeField(null=True, blank=True)
    # Status flags
    # An open order may still be waiting for funds.
    open = models.BooleanField(default=False)
    canceled = models.BooleanField(default=False)
    # counter of how many trades are filling this order
    filled = models.PositiveIntegerField(default=0)
    # Metadata
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True, editable=False)
    modified = models.DateTimeField(auto_now=True, null=True, blank=True, editable=False)
