import datetime
from pprint import pprint

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.db import models, connection
from django.forms.models import model_to_dict
from django.utils import timezone
from pycoin.key.BIP32Node import BIP32Node

import address.utils
import order.utils
import trade.models
import reporting.utils
import wallet.models
import wallet.utils
from address.models import Address


class TempTrades(models.Model):
    id = models.BigAutoField(primary_key=True, editable=False)
    currency = models.CharField(max_length=16, default='')
    # volume and fee are always in the specified currency
    volume = models.BigIntegerField(default=0)
    fee = models.BigIntegerField(default=0)
    wallet = models.ForeignKey(wallet.models.Wallet, on_delete=models.PROTECT)
    trade = models.ForeignKey(trade.models.Trade, on_delete=models.PROTECT)
    # true if this is a buy order, false if this is a sell order
    side = models.BooleanField(default=False)

    class Meta:
        app_label = "settle"

class Command(BaseCommand):
    help = 'Settle trades'

    # Mark trade valid if not already marked with an error
    def mark_as_valid(self, identifiers, unsettled_trade, order_side, order_direction):
        if order_side == True:
            order_side = 'buy'
        elif order_side == False:
            order_side = 'sell'

        if order_side == 'buy':
            if order_direction == 'in':
                if unsettled_trade.buy_order_settled_in is trade.models.SETTLED_NONE:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_VALID" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.buy_order.id))
                    unsettled_trade.buy_order_settled_in = trade.models.SETTLED_VALID
                    unsettled_trade.save()
            else:
                assert(order_direction == 'out')
                if unsettled_trade.buy_order_settled_out is trade.models.SETTLED_NONE:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_VALID" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.buy_order.id))
                    unsettled_trade.buy_order_settled_out = trade.models.SETTLED_VALID
                    unsettled_trade.save()
        else:
            assert(order_side == 'sell')
            if order_direction == 'in':
                if unsettled_trade.sell_order_settled_in is trade.models.SETTLED_NONE:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_VALID" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.sell_order.id))
                    unsettled_trade.sell_order_settled_in = trade.models.SETTLED_VALID
                    unsettled_trade.save()
            else:
                assert(order_direction == 'out')
                if unsettled_trade.sell_order_settled_out is trade.models.SETTLED_NONE:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_VALID" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.sell_order.id))
                    unsettled_trade.sell_order_settled_out = trade.models.SETTLED_VALID
                    unsettled_trade.save()

        reporting.utils.audit(message="settling order marked valid", details={
            'identifiers': identifiers,
            'trade': model_to_dict(unsettled_trade),
            'side': order_side,
        })

        return unsettled_trade

    def mark_as_pending(self, identifiers, unsettled_trade, order_side, order_direction):
        if order_side == True:
            order_side = 'buy'
        elif order_side == False:
            order_side = 'sell'

        if order_side == 'buy':
            if order_direction == 'in':
                if unsettled_trade.buy_order_settled_in is trade.models.SETTLED_VALID:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.buy_order.id))
                    unsettled_trade.buy_order_settled_in = trade.models.SETTLED_PENDING
                    unsettled_trade.save()
                else:
                    print(" !! failed to mark %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.buy_order.id))
                    self.mark_as_error(identifiers, unsettled_trade, order_side)
            else:
                assert(order_direction == 'out')
                if unsettled_trade.buy_order_settled_out is trade.models.SETTLED_VALID:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.buy_order.id))
                    unsettled_trade.buy_order_settled_out = trade.models.SETTLED_PENDING
                    unsettled_trade.save()
                else:
                    print(" !! failed to mark %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.buy_order.id))
                    self.mark_as_error(identifiers, unsettled_trade, order_side)
        else:
            assert(order_side == 'sell')
            if order_direction == 'in':
                if unsettled_trade.sell_order_settled_in is trade.models.SETTLED_VALID:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.sell_order.id))
                    unsettled_trade.sell_order_settled = trade.models.SETTLED_PENDING
                    unsettled_trade.save()
                else:
                    print(" !! failed to mark %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.sell_order.id))
                    self.mark_as_error(identifiers, unsettled_trade, order_side)
            else:
                if unsettled_trade.sell_order_settled_out is trade.models.SETTLED_VALID:
                    print(" - marking %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.sell_order.id))
                    unsettled_trade.sell_order_settled = trade.models.SETTLED_PENDING
                    unsettled_trade.save()
                else:
                    print(" !! failed to mark %s %s order %s (%d:%s) SETTLED_PENDING" % (unsettled_trade.cryptopair, order_side, order_direction, unsettled_trade.id, unsettled_trade.sell_order.id))
                    self.mark_as_error(identifiers, unsettled_trade, order_side)

        reporting.utils.audit(message="settling order marked pending", details={
            'identifiers': identifiers,
            'trade': model_to_dict(unsettled_trade),
            'side': order_side,
        })

        return unsettled_trade

    # Mark trade error if not already marked with an error
    def mark_as_error(self, identifiers, unsettled_trade=None, order_side=None):
        if order_side == True:
            order_side = 'buy'
        elif order_side == False:
            order_side = 'sell'

        if order_side == 'buy':
            if unsettled_trade.buy_order_settled is not trade.models.SETTLED_ERROR:
                print(" - marking %s %s order (%d:%s) SETTLED_ERROR" % (unsettled_trade.cryptopair, order_side, unsettled_trade.id, unsettled_trade.buy_order.id))
                unsettled_trade.buy_order_settled = trade.models.SETTLED_ERROR
                unsettled_trade.save()
        else:
            assert(order_side == 'sell')
            if unsettled_trade.sell_order_settled is not trade.models.SETTLED_ERROR:
                print(" - marking %s %s order (%d:%s) SETTLED_ERROR" % (unsettled_trade.cryptopair, order_side, unsettled_trade.id, unsettled_trade.sell_order.id))
                unsettled_trade.sell_order_settled = trade.models.SETTLED_ERROR
                unsettled_trade.save()

        reporting.utils.audit(message="settling order marked error", details={
            'identifiers': identifiers,
            'trade': model_to_dict(unsettled_trade),
            'side': order_side,
        })

        return unsettled_trade

    def validate_timestamps(self, identifiers, now, unsettled_trade, errors):
        # @TODO: time-drift between servers could trigger one or more of these
        # errors. Consider rounding timestamps up.

        # Orders can't be placed in the future
        if unsettled_trade.sell_order.created > now:
            self.mark_as_error(
                identifiers=identifiers,
                unsettled_trade=unsettled_trade,
                order_side='sell'
            )
            errors.append("sell order created in future (%s), now %s" % (unsettled_trade.sell_order.created, now))
            print("ERROR: order created in the future")
        if unsettled_trade.buy_order.created > now:
            self.mark_as_error(
                identifiers=identifiers,
                unsettled_trade=unsettled_trade,
                order_side='buy'
            )
            errors.append("buy order created in future (%s), now %s" % (unsettled_trade.buy_order.created, now))
            print("ERROR: buy order created in the future")

        # Trades can't happen in the future
        if unsettled_trade.created > now:
            self.mark_as_error(
                identifiers=identifiers,
                unsettled_trade=unsettled_trade,
                order_side='sell'
            )
            errors.append("trade created in future (%s), now %s" % (unsettled_trade.created, now))
            print("ERROR: sell trade created in the future")

        # Trades can't happen before the order is placed
        if unsettled_trade.sell_order.created > unsettled_trade.created:
            self.mark_as_error(
                identifiers=identifiers,
                unsettled_trade=unsettled_trade,
                order_side='sell'
            )
            errors.append("trade created (%s) before sell order created (%s)" % (unsettled_trade.created, unsettled_trade.sell_order.created))
            print("ERROR: trade created before sell order created")
        if unsettled_trade.buy_order.created > unsettled_trade.created:
            self.mark_as_error(
                identifiers=identifiers,
                unsettled_trade=unsettled_trade,
                order_side='buy'
            )
            errors.append("trade created (%s) before buy order created (%s)" % (unsettled_trade.created, unsettled_trade.buy_order.created))
            print("ERROR: trade created before buy order created")

        return errors

    def get_trades_from_wallet(self, user_wallet):
        return TempTrades.objects.filter(wallet_id=user_wallet.id)

    def handle(self, *args, **options):

        # Maintain global metadata about the orders being settled
        global_settled_order_count = 0
        now = datetime.datetime.now(datetime.timezone.utc)

        # Add a unique id allowing us to trace through this pass at settling
        identifiers = {
            'trace_id': reporting.utils.generate_trace_id(),
        }

        errors = []

        # @TODO: grab a lock to ensure only one process can settle at a time
        # https://github.com/ .. /issues/134

        with connection.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS settle_temptrades')
            cursor.execute('''
                CREATE TABLE settle_temptrades (
                    id BIGSERIAL PRIMARY KEY NOT NULL,
                    currency CHARACTER VARYING(16),
                    volume BIGINT,
                    fee BIGINT,
                    wallet_id UUID REFERENCES wallet_wallet (id),
                    trade_id BIGINT REFERENCES trade_trade (id),
                    side BOOLEAN
                );''')

            # Step 1:
            # Loop through each coin type, settle money out:
            for coin_type in settings.COINS.keys():
                print("Settling %s (%s)..." % (settings.COINS[coin_type]['name'], coin_type))
                coin_details = {
                    'type': coin_type,
                    'name': settings.COINS[coin_type]['name'],
                }
                reporting.utils.audit(message="initiating settling", details={
                    'identifiers': identifiers,
                    'coin_details': coin_details,
                })

                # Start by finding trades where the base currency for the sell
                # order side has an appropriate base currency.
                # @TODO: do we need to review sell_order_settled_in trades too?
                trades_out_sells = trade.models.Trade.objects.filter(sell_order__base_currency=coin_type) \
                    .filter(models.Q(sell_order_settled_out=trade.models.SETTLED_NONE) | models.Q(sell_order_settled_out=trade.models.SETTLED_VALID)) \
                    .order_by('created')

                for unsettled_trade in trades_out_sells:
                    global_settled_order_count += 1
                    from_user = unsettled_trade.sell_order.wallet.user.get()
                    order_fee = order.utils.get_fee(
                        order=unsettled_trade.sell_order,
                        volume=unsettled_trade.base_volume
                    )

                    # Collect the temporary data we build for settling, and
                    # write it to the audit logs.
                    to_settle = []

                    # Record the money-out (sell) from this trade
                    new_settle = TempTrades(
                        currency=coin_type,
                        volume=unsettled_trade.base_volume * -1,
                        fee=0, # no fee for money-out
                        side=False, # sell order
                        wallet=unsettled_trade.sell_order.wallet,
                        trade=unsettled_trade,
                    )
                    new_settle.save()
                    to_settle.append(model_to_dict(new_settle))

                    # Record the money-in (buy) from this trade
                    to_user = unsettled_trade.buy_order.wallet.user.get()
                    money_in_wallet = wallet.models.Wallet.objects.get(
                        user=to_user,
                        currencycode=coin_type,
                    )
                    new_settle = TempTrades(
                        currency=coin_type,
                        volume=unsettled_trade.base_volume - order_fee,
                        fee=order_fee,
                        side=True, # buy order
                        wallet=money_in_wallet,
                        trade=unsettled_trade,
                    )
                    new_settle.save()
                    to_settle.append(model_to_dict(new_settle))

                    # Be sure order and trade have sane timestamps
                    errors = self.validate_timestamps(
                        identifiers=identifiers,
                        now=now,
                        unsettled_trade=unsettled_trade,
                        errors=errors)

                    from_details = {
                        'user_id': from_user.id,
                        'wallet_id': unsettled_trade.sell_order.wallet.id,
                        'order_id': unsettled_trade.sell_order.id,
                        'trade_id': unsettled_trade.id,
                        'order_type': 'sell',
                        'cryptopair': unsettled_trade.cryptopair,
                        'pair_side': 'base',
                        'volume': unsettled_trade.base_volume,
                        'fee': order_fee,
                        'order_created': unsettled_trade.sell_order.created,
                        'trade_created': unsettled_trade.created,
                        'now': now,
                    }
                    to_details = {
                        'user_id': to_user.id,
                        'wallet_id': unsettled_trade.buy_order.wallet.id,
                        'order_id': unsettled_trade.buy_order.id,
                        'trade_id': unsettled_trade.id,
                        'order_type': 'buy',
                        'cryptopair': unsettled_trade.cryptopair,
                        'pair_side': 'base',
                        'volume': unsettled_trade.base_volume - order_fee,
                        'order_created': unsettled_trade.buy_order.created,
                        'trade_created': unsettled_trade.created,
                        'now': now,
                    }

                    reporting.utils.audit(message="settling details", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'from_details': from_details,
                        'to_details': to_details,
                        'to_settle': to_settle,
                        'errors': errors,
                    })


                # Next, find trades where the base currency for the buy order side
                # has an appropriate quote currency.
                # @TODO do we need to review buy_order_settled_in trades too?
                trades_out_buys = trade.models.Trade.objects.filter(buy_order__quote_currency=coin_type) \
                    .filter(models.Q(buy_order_settled_out=trade.models.SETTLED_NONE) | models.Q(buy_order_settled_out=trade.models.SETTLED_VALID)) \
                    .order_by('created')

                for unsettled_trade in trades_out_buys:
                    global_settled_order_count += 1
                    from_user = unsettled_trade.buy_order.wallet.user.get()
                    order_fee = order.utils.get_fee(
                        order=unsettled_trade.buy_order,
                        volume=unsettled_trade.volume,
                    )

                    # Collect the temporary data we build for settling, and
                    # write it to the audit logs.
                    to_settle = []

                    # Record the money-out (buy) from this trade
                    new_settle = TempTrades(
                        currency=coin_type,
                        volume=unsettled_trade.volume * -1,
                        fee=0, # no fee for money-out
                        side=True, # buy order
                        wallet=unsettled_trade.buy_order.wallet,
                        trade=unsettled_trade,
                    )
                    new_settle.save()
                    to_settle.append(model_to_dict(new_settle))

                    # Record the money-in (sell) from this trade
                    to_user = unsettled_trade.sell_order.wallet.user.get()
                    money_in_wallet = wallet.models.Wallet.objects.get(
                        user=to_user,
                        currencycode=coin_type,
                    )
                    new_settle = TempTrades(
                        currency=coin_type,
                        volume=unsettled_trade.volume - order_fee,
                        fee=order_fee,
                        side=False, # sell order
                        wallet=money_in_wallet,
                        trade=unsettled_trade,
                    )
                    new_settle.save()
                    to_settle.append(model_to_dict(new_settle))

                    # Be sure order and trade have sane timestamps
                    errors = self.validate_timestamps(
                        identifiers=identifiers,
                        now=now,
                        unsettled_trade=unsettled_trade,
                        errors=errors)

                    from_details = {
                        'user_id': from_user.id,
                        'wallet_id': unsettled_trade.buy_order.wallet.id,
                        'order_id': unsettled_trade.buy_order.id,
                        'trade_id': unsettled_trade.id,
                        'order_type': 'buy',
                        'cryptopair': unsettled_trade.cryptopair,
                        'pair_side': 'quote',
                        'volume': unsettled_trade.volume,
                        'fee': order_fee,
                        'order_created': unsettled_trade.buy_order.created,
                        'trade_created': unsettled_trade.created,
                        'now': now,
                    }
                    to_details = {
                        'user_id': to_user.id,
                        'wallet_id': unsettled_trade.sell_order.wallet.id,
                        'order_id': unsettled_trade.sell_order.id,
                        'trade_id': unsettled_trade.id,
                        'order_type': 'sell',
                        'pair_side': 'quote',
                        'volume': unsettled_trade.volume - order_fee,
                    }
                    reporting.utils.audit(message="settling details", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'from_details': from_details,
                        'to_details': to_details,
                        'to_settle': to_settle,
                        'errors': errors,
                    })

                tmp_trades = TempTrades.objects.values('wallet') \
                    .filter(currency=coin_type) \
                    .annotate(total_volume=models.Sum('volume'), total_fee=models.Sum('fee'))

                for tmp_trade in tmp_trades:
                    user_wallet = wallet.models.Wallet.objects.get(id=tmp_trade['wallet'])
                    balances = wallet.utils.get_balances(
                        identifiers=identifiers,
                        user_wallet=user_wallet,
                    )
                    # Confirm there's sufficient funds for this trade.
                    if tmp_trade['total_volume'] < 0:
                        balance_in = 0
                        balance_out = tmp_trade['total_volume'] * -1
                        #print("validating transfer of {} {} out of wallet {}".format(balance_out, user_wallet.currencycode, user_wallet.id))
                        if balances['blockchain'] < balance_out:
                            trades = self.get_trades_from_wallet(user_wallet=user_wallet)
                            for error_trade in trades:
                                self.mark_as_error(
                                    identifiers=identifiers,
                                    unsettled_trade=error_trade.trade,
                                    order_side=error_trade.side,
                                )
                            errors.append("%d balance insufficient for %d trades" % (balances['blockchain'], balance_out))
                            print("ERROR: insufficient funds")
                        #if tmp_trade['total_fee'] > 0:
                            #print("validating transfer of {} {} fee to exchange".format(tmp_trade['total_fee'], user_wallet.currencycode))
                    else:
                        balance_out = 0
                        balance_in = tmp_trade['total_volume']
                        #print("validating transfer of {} {} into wallet {}".format(balance_in, user_wallet.currencycode, user_wallet.id))
                        #print("validating transfer of {} {} fee to exchange".format(tmp_trade['total_fee'], user_wallet.currencycode))

                    coin_details = {
                        'type': user_wallet.currencycode,
                        'name': settings.COINS[user_wallet.currencycode]['name'],
                    }
                    reporting.utils.audit(message="settling balance confirmation", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'aggregate_settle': tmp_trade,
                        'funds_out': {
                            'currency_code': user_wallet.currencycode,
                            'volume': balance_out,
                        },
                        'funds_in': {
                            'currency_code': user_wallet.currencycode,
                            'volume': balance_in,
                        },
                        'balances': balances,
                        'errors': errors,
                    })

            # Auditing completed, mark trades as pending indicating we're ready
            # to actually settle. Any trades that have previously been marked
            # with an error will stay as an error.
            all_trades_to_settle = TempTrades.objects.filter()
            for trade_to_settle in all_trades_to_settle:
                # This only succeeds if the trade doesn't have an error
                if trade_to_settle.volume > 0:
                    order_direction = 'in'
                else:
                    order_direction = 'out'
                self.mark_as_valid(
                    identifiers=identifiers,
                    unsettled_trade=trade_to_settle.trade,
                    order_side=trade_to_settle.side,
                    order_direction=order_direction)

            # Be sure there are no trades in an ERROR state.
            error_trades = trade.models.Trade.objects.filter(
                models.Q(buy_order_settled_in=trade.models.SETTLED_ERROR) |
                models.Q(buy_order_settled_out=trade.models.SETTLED_ERROR) |
                models.Q(sell_order_settled_in=trade.models.SETTLED_ERROR) |
                models.Q(sell_order_settled_out=trade.models.SETTLED_ERROR)
            )
            error_count = 0
            for error_trade in error_trades:
                error_count += 1
            if error_count > 0:
                print("ERROR: aborting settling due to errors (%d)".format(error_count))
                return(-1)
            else:
                print("no errors detected: creating blockchain transactions.")

            # Finally, create the actual blockchain transactions
            for coin_type in settings.COINS.keys():
                trades_to_settle = TempTrades.objects \
                    .filter(currency=coin_type)
                if len(trades_to_settle):
                    print("\nGenerating {} transaction(s)...".format(coin_type))
                    # @TODO: keep track of transaction size, split into multiple
                    # transactions if necessary.

                    validation = {
                        'exchange': 0,
                    }
                    audit_validation = {
                        'exchange': 0,
                    }
                    total = 0
                    for trade_to_settle in trades_to_settle:
                        if trade_to_settle.wallet.id in validation:
                            validation[trade_to_settle.wallet.id] += trade_to_settle.volume
                            audit_validation[trade_to_settle.wallet.id.hex] += trade_to_settle.volume
                        else:
                            validation[trade_to_settle.wallet.id] = trade_to_settle.volume
                            audit_validation[trade_to_settle.wallet.id.hex] = trade_to_settle.volume
                        validation['exchange'] += trade_to_settle.fee
                        audit_validation['exchange'] += trade_to_settle.fee

                        total += trade_to_settle.volume + trade_to_settle.fee
                    # funds in plus funds out must be zero
                    assert(total == 0)

                    reporting.utils.audit(message="settling trades balance validation", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'validation': audit_validation,
                        'validation_total': total,
                        'errors': errors,
                    })

                    # The funds going into blockchain wallets:
                    vin = {}
                    # The funds coming out of blockchain wallets:
                    vout = []

                    addresses_with_unspent = {}

                    funds_in = 0
                    funds_out = 0

                    #pprint(validation)
                    for wallet_id in validation:
                        # @TODO: use a valid address
                        if wallet_id == 'exchange':
                            exchange_address = address.utils.get_new_exchange_address(self, currencycode=coin_type)
                            vin[exchange_address] = validation[wallet_id]
                            continue

                        user_wallet = wallet.models.Wallet.objects.get(id=wallet_id)

                        # Handle funds-in
                        if validation[wallet_id] > 0:
                            # Generate a new address from this user's wallet
                            new_address, index = address.utils.get_new_address(user_wallet=user_wallet, is_change=False)
                            # @TODO: make it configurable which address gets used -- for now, we use p2pkh
                            vin[new_address['p2pkh']] = validation[wallet_id]
                            reporting.utils.audit(message="settling funds in new address", details={
                                'identifiers': identifiers,
                                'coin_details': coin_details,
                                'wallet_id': wallet_id,
                                'wallet_funds_in': validation[wallet_id],
                                'address': new_address['p2pkh'],
                            })

                        else:
                            value = validation[wallet_id] * -1
                            unspent, addresses, subtotal, success = wallet.utils.get_unspent_equal_or_greater(user_wallet, value)
                            if (success == False):
                                # @TODO
                                # Something has gone terribly wrong: we already validated we had sufficient funds
                                print("ERROR: ALERT ALERT")
                                return -1
                            funds_out += subtotal
                            # We'll use this when we sign the transaction
                            addresses_with_unspent[wallet_id] = addresses
                            reporting.utils.audit(message="settling funds out loading unspent", details={
                                'identifiers': identifiers,
                                'coin_details': coin_details,
                                'wallet_id': wallet_id,
                                'wallet_funds_out': value,
                                'unspent': {
                                    'vout': unspent,
                                    'addresses': list(addresses),
                                    'value': subtotal,
                                }
                            })

                            # Assemble the vout array
                            for detail in unspent:
                                vout.append(detail)
                            # If the unspent has more funds than needed, send the change back to the user's wallet
                            if subtotal > value:
                                new_address, index = address.utils.get_new_address(user_wallet=user_wallet, is_change=True)
                                vin[new_address['p2pkh']] = subtotal - value
                                #print(" + CHANGE: {}".format(subtotal - value))
                                reporting.utils.audit(message="settling returning change to user", details={
                                    'identifiers': identifiers,
                                    'coin_details': coin_details,
                                    'wallet_id': wallet_id,
                                    'wallet_id': wallet_id,
                                    'wallet_funds_out': value,
                                    'unspent': {
                                        'vout': unspent,
                                        'addresses': list(addresses),
                                        'value': subtotal,
                                    },
                                    'change': {
                                        'address': new_address['p2pkh'],
                                        'value': subtotal - value,
                                    }
                                })

                    # Validate our vin and vout
                    for receive_address in vin:
                        assert(vin[receive_address] > 0)
                        funds_in += vin[receive_address]

                    assert(funds_in == funds_out)

                    #print(" o vin: {}".format(vin))
                    #print(" o vout: {}".format(vout))

                    # @TODO: exchange configuration for how quickly we settle
                    # @TODO: exchange configuratoin for how we settle
                    fee, valid = wallet.utils.calculate_fee(wallet=user_wallet, vout=vout, vin=vin,
                                                            number_of_blocks=18, estimate_mode='CONSERVATIVE')

                    reporting.utils.audit(message="settling calculating fees", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'funds_in': funds_in,
                        'funds_out': funds_out,
                        'vin': vin,
                        'vout': vout,
                        'exchange_fee': validation['exchange'],
                        'network_fee': fee,
                        'errors': errors,
                    })

                    if fee > validation['exchange']:
                        print(" ! ERROR: Unable to settle {}, our fee of {} is less than network fee of {} ... skipping" \
                            .format(coin_type, validation['exchange'], fee))
                        # @TODO don't record this as settled, next time we try
                        # to settle it should still need to be settled
                        reporting.utils.audit(message="settling insufficient exchange fee", details={
                            'identifiers': identifiers,
                            'coin_details': coin_details,
                            'funds_in': funds_in,
                            'funds_out': funds_out,
                            'vin': vin,
                            'vout': vout,
                            'exchange_fee': validation['exchange'],
                            'network_fee': fee,
                            'errors': errors,
                        })
                        continue

                    # Subtract network fee from our profits
                    vin[exchange_address] -= fee
                    #print(" - subtracting network fee of {}, leaving {} for exchange fee".format(fee, vin[exchange_address]))

                    # Create actual transaction
                    final_vin = {}
                    for to_address in vin:
                        final_vin[to_address] = wallet.utils.convert_to_decimal(vin[to_address])
                    #print("final_vin: {}".format(final_vin))

                    reporting.utils.audit(message="settling finalizing transaction", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'final_vin': final_vin,
                        'vout': vout,
                        'final_exchange_fee': validation['exchange'],
                        'network_fee': fee,
                        'errors': errors,
                    })

                    raw_tx = wallet.utils.create_raw_transaction(currencycode=coin_type, input=vout, output=final_vin)
                    #print("raw_tx: {}".format(raw_tx))
                    reporting.utils.audit(message="settling raw transaction", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'vin': final_vin,
                        'vout': vout,
                        'exchange_fee': validation['exchange'],
                        'network_fee': fee,
                        'raw_transaction': raw_tx,
                        'errors': errors,
                    })

                    # @TODO Sign the raw transaction
                    private_keys = []
                    # Load wallet's private key, effectively unlocking it

                    #print("addresses_with_unspent: {}".format(addresses_with_unspent))

                    for wallet_id in validation:
                        # exchange only receives money, skip
                        if wallet_id == 'exchange':
                            continue

                        # Only get private keys if the user is sending funds
                        if validation[wallet_id] < 0:
                            # @TODO use remote secrets database for storing private keys
                            user_wallet = wallet.models.Wallet.objects.get(id=wallet_id)
                            unlocked_account = BIP32Node.from_hwif(user_wallet.private_key)

                            # Get WIF for all addresses we're sending from
                            for source_address in addresses_with_unspent[wallet_id]:
                                #print("to_address: %s" % to_address)
                                address_object = Address.objects.get(wallet=wallet_id, p2pkh=source_address)
                                #print("source_address({}) index({}) is_change({})".format(source_address, address_object.index, address_object.is_change))
                                if address_object.is_change:
                                    is_change = 1
                                else:
                                    is_change = 0
                                unlocked_address = unlocked_account.subkey_for_path("%d/%s" % (is_change, address_object.index))
                                private_keys.append(unlocked_address.wif())

                    #print(private_keys)

                    if coin_type in ['BTC', 'XTN']:
                        # Starting with 0.17, bitcoind replaces the old sign RPC with a new one
                        signed_tx = wallet.utils.sign_raw_transaction_with_key(currencycode=coin_type, raw_tx=raw_tx, private_keys=private_keys)
                    else:
                        signed_tx = wallet.utils.sign_raw_transaction(currencycode=coin_type, raw_tx=raw_tx, output=[], private_keys=private_keys)

                    #print("signed_tx: {}".format(signed_tx))
                    reporting.utils.audit(message="settling signed transaction", details={
                        'identifiers': identifiers,
                        'coin_details': coin_details,
                        'vin': final_vin,
                        'vout': vout,
                        'exchange_fee': validation['exchange'],
                        'network_fee': fee,
                        'raw_transaction': raw_tx,
                        'signed_transaction': signed_tx,
                        'errors': errors,
                    })

                    try:
                        if signed_tx['complete'] is False:
                            print("ERROR: failed to sign transaction")
                            print(signed_tx)
                        else:
                            # @TODO Send the transaction to the blockchain:
                            #  - submit tx to blockchain, audit resulting txid

                            # Update database: these trades are now pending inclusion on
                            # the blockchain.
                            for trade_to_settle in trades_to_settle:
                                if trade_to_settle.volume > 0:
                                    order_direction = 'in'
                                else:
                                    order_direction = 'out'
                                self.mark_as_pending(
                                    identifiers=identifiers,
                                    unsettled_trade=trade_to_settle.trade,
                                    order_side=trade_to_settle.side,
                                    order_direction=order_direction)
                    except:
                        print("ERROR: failed to sign transaction - no response from RPC call")

            cursor.execute('DROP TABLE settle_temptrades')

        self.stdout.write(self.style.SUCCESS('Successfully settled %d orders' % global_settled_order_count))

        reporting.utils.audit(message="completed settling all coins", details={
            'identifiers': identifiers,
            'global_settled_order_count': global_settled_order_count,
        })
