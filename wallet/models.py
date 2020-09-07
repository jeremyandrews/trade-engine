import uuid

from django.db import models

from spauser.models import SpaUser


class Wallet(models.Model):
    '''
    A wallet is a container attached to a user and holding any number of
    addresses for a specific currency.

    We set up a many to many relation between the user table and the wallet to allow for future features:
      - a user having multiple wallets
      - multiple users sharing a wallet
    '''
    # User is blank when a wallet is first created, before it's associated with a user.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ManyToManyField(SpaUser, blank=True)
    label = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    currencycode = models.CharField(max_length=12)
    public_key = models.CharField(max_length=128, blank=True)
    private_key = models.CharField(max_length=128, blank=True)
    last_external_index = models.IntegerField(default=0)
    last_change_index = models.IntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    modified = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __unicode__(self):
        return u'Wallet: %s of user %s' % (self.label, self.user.email)

