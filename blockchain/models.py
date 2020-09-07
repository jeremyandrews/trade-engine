import uuid

from django.db import models

from wallet.models import Wallet
from address.models import Address


class Transaction(models.Model):
    '''
    Cache blockchain activity.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    address = models.ForeignKey(Address, on_delete=models.PROTECT, db_index=True)
    # Information tracked about each transaction
    txid = models.CharField(max_length=128)
    height = models.BigIntegerField(default=0)
    timestamp = models.PositiveIntegerField(default=0)
    value_in = models.BigIntegerField(default=0)
    from_object = models.TextField(null=True, blank=True)
    value_out = models.BigIntegerField(default=0)
    to_object = models.TextField(null=True, blank=True)
    fee = models.BigIntegerField(default=0)
    # Tracks how many unspent remain in a given txid
    value_unspent = models.BigIntegerField(default=0)
    # Metadata
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True, editable=False)
    modified = models.DateTimeField(auto_now=True, null=True, blank=True, editable=False)
