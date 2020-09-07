import uuid

from django.db import models

from wallet.models import Wallet


class Address(models.Model):
    '''
    An address is an identifier representing a possible destination for payment.
    '''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, db_index=True)
    label = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    p2pkh = models.CharField(max_length=200, editable=False, db_index=True)
    p2sh_p2wpkh = models.CharField(max_length=200, null=True, blank=True, editable=False, db_index=True)
    bech32 = models.CharField(max_length=2048, null=True, blank=True, editable=False, db_index=True)
    index = models.PositiveIntegerField(default=0)
    is_change = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True, editable=False)
    modified = models.DateTimeField(auto_now=True, null=True, blank=True, editable=False)

    def __unicode__(self):
        return u'Address: %s' % self.public
