import datetime

from django.core.management.base import BaseCommand, CommandError
from order.models import Order
from django.utils import timezone


class Command(BaseCommand):
    help = 'Expire orders whose timeinforce has passed'

    def handle(self, *args, **options):
        expire_count = 0
        # Find open orders with expired timeinforce
        for order in Order.objects.filter(open=True, timeinforce__lte=timezone.now()):
            order.open = False
            order.canceled = True
            order.save()
            expire_count += 1

        self.stdout.write(self.style.SUCCESS('Successfully expired %d orders' % expire_count))
