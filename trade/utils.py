import datetime
import time

from django.forms.models import model_to_dict
from django.urls import reverse
from django.utils import timezone

import trade.models
from order.models import Order
import order.utils
import reporting.utils
import spauser.utils


def convert_quote_to_base(volume, price):
    return int(volume / price * 100000000)

# The matching engine, look for another existing order that matches with this order to fulfill a trade.
def match_order(identifiers, order_to_match):
    trades = []

    # Match the opposite side of the order:
    to_match_side = not order_to_match.side

    # Start by matching Market orders.
    reporting.utils.audit(message="matching with market orders", details={
        'identifiers': identifiers,
        'order': order_to_match,
        'to_match_side': to_match_side,
        'trades': trades,
        'matching_algorithm': 'basic FIFO',
    })

    # https://www.investopedia.com/terms/m/matchingorders.asp
    # "Under a basic FIFO algorithm, or price-time-priority algorithm, the earliest active buy order at the highest
    # price takes priority over any subsequent order at that price, which in turn takes priority over any active buy
    # order at a lower price. For example, if a buy order for 200 shares of stock at $90 per share precedes an order for
    # 50 shares of the same stock at the same price, the system must match the entire 200-share order to one or more
    # sell orders before beginning to match any portion of the 50-share order."

    # We match with a basic price-time-priority (FIFO) algorithm, staring with oldest orders first. In this case, we're
    # matching against open market orders (those with a limit_price of 0) on the other side, so we only sort by the
    # created timestamp.
    for market_order in Order.objects.filter(side=to_match_side, cryptopair=order_to_match.cryptopair, open=True,
                                             limit_price=0).order_by('created'):
        trade, done, valid = make_trade(identifiers=identifiers, order1=order_to_match, order2=market_order)
        if valid:
            trades.append(trade)
            reporting.utils.audit(message="matched with existing market order", details={
                'identifiers': identifiers,
                'trade': trade,
            })
        if done:
            return trades

    reporting.utils.audit(message="matching with limit orders", details={
        'identifiers': identifiers,
        'order': order_to_match,
        'to_match_side': to_match_side,
        'trades': trades,
        'matching_algorithm': 'basic FIFO',
    })

    # There are no more market orders to match, now we move on to limit orders. We continue using a basic price-time-
    # priority (FIFO) algorithm. For sells, we match the highest buys first. For buys, we match the lowest sells first.
    # If there are multiple matches at the same price, we match the oldest order first.
    if order_to_match.side is not True:
        # A sell order (side == False) specifies the minimum accepted price, match against the highest buy orders that
        # are equal to or greater than this minimum price. (In the case of a market order, the order.limit_price will
        # be 0, and will therfore match _ALL_ open sell orders.)
        for buy_order in Order.objects.filter(side=to_match_side, cryptopair=order_to_match.cryptopair, open=True,
                                              limit_price__gte=order_to_match.limit_price).order_by('-limit_price',
                                                                                                    'created'):
            # to_match_side is True (we're matching buys), and the bid must be greater or equal to our minimum
            # accepted price. Sort by limit_price descending, so we match the highest buy bids first.
            trade, done, valid = make_trade(identifiers=identifiers, order1=order_to_match, order2=buy_order)
            if valid:
                trades.append(trade)
                reporting.utils.audit(message="sell matched with limit buy order", details={
                    'identifiers': identifiers,
                    'order': order_to_match,
                    'trade': trade,
                })
            if done:
                return trades
    else:
        assert(order_to_match.side is True)
        # A buy order (side is True) limit_price specifies the maximum price willing to pay, match against the lowest
        # sell orders that are equal to or less than this maximum price.
        if order_to_match.limit_price:
            for sell_order in Order.objects.filter(side=to_match_side, cryptopair=order_to_match.cryptopair, open=True,
                                                   limit_price__lte=order_to_match.limit_price) \
                    .order_by('-limit_price', 'created'):
                # to_match_side is False (we're matching sells), and the bid must be less than or equal to our minimum
                # accepted price. Sort by limit_price ascending so we match the lowest sell bids first.
                trade, done, valid = make_trade(identifiers=identifiers, order1=order_to_match, order2=sell_order)
                if valid:
                    trades.append(trade)
                    reporting.utils.audit(message="limit buy matched with limit sell order", details={
                        'identifiers': identifiers,
                        'order': order_to_match,
                        'trade': trade,
                    })
                if done:
                    return trades
        else:
            # This order has no limit_price, so it is a market order. There is no maximum price willing to pay, match
            # against all sell orders.
            for sell_order in Order.objects.filter(side=to_match_side, cryptopair=order_to_match.cryptopair,
                                                   open=True).order_by('-limit_price', 'created'):
                # to_match_side is False (we're matching sells). Sort by limit_price ascending so we match the lowest
                # sell bids first.
                trade, done, valid = make_trade(identifiers=identifiers, order1=order_to_match, order2=sell_order)
                if valid:
                    trades.append(trade)
                    reporting.utils.audit(message="marke buy matched with limit sell order", details={
                        'identifiers': identifiers,
                        'order': order_to_match,
                        'trade': trade,
                    })
                if done:
                    return trades
    return trades

def make_trade(identifiers, order1, order2):
    assert(order1.side != order2.side)

    if order1.side is True:
        buy_order = order1
        sell_order = order2
    else:
        buy_order = order2
        sell_order = order1

    orders = {
        'buy': buy_order,
        'sell': sell_order,
    }

    # Be sure the orders aren't owned by the same users.
    order1_user = order1.wallet.user.get()
    order2_user = order2.wallet.user.get()
    if order1_user.id == order2_user.id:
        # this is a buy and a sell by the same user, do not make the trade
        reporting.utils.audit(message="buy and sell are from same wallet", details={
            'identifiers': identifiers,
            'orders': orders,
        })
        return False, False, False

    # Be sure order2 hasn't expired.
    if order2.timeinforce:
        if (order2.timeinforce <= timezone.now()):
            # this order has expired, do not make the trade
            reporting.utils.audit(message="matched order expired", details={
                'identifiers': identifiers,
                'orders': orders,
            })
            return False, False, False

    # Order1 is an active order, Order2 is from the orderbook. If order2 has a limit price, we use it:
    if order2.limit_price:
        price = order2.limit_price
        price_match = 'a'
    # Otherwise order2 is a market order, so we use order1's limit price:
    elif order1.limit_price:
        price = order1.limit_price
        price_match = 'b'
    # Otherwise both sides of the order are market orders, so we use use the price of the last trade:
    else:
        try:
            last_trade, = trade.models.Trade.objects.filter(cryptopair=order1.cryptopair).order_by('-id')[:1]
            price = last_trade.price
            price_match = 'c'

            # Sanity test: be sure we didn't match a buy with too expensive a sell order.
            if order1.side is True:
                if order1.limit_price and order1.limit_price > price:
                    reporting.utils.audit(message="invalid match, price higher than buy limit: @FIXME",
                                          details={
                                              'identifiers': identifiers,
                                              'orders': orders,
                                              'price': price,
                                          })
                    return False, False, False
            # Sanity test: be sure we didn't match a sell with too low a buy order.
            if order2.side is False:
                if order1.limit_price and order1.limit_price < price:
                    reporting.utils.audit(message="invalid match, price lower than sell limit: @FIXME",
                                          details={
                                              'identifiers': identifiers,
                                              'orders': orders,
                                              'price': price,
                                          })
                    return False, False, False
        except:
            # We've never had a trade, we can't match a market order with a market order as we have no price!
            reporting.utils.audit(message="can't match two market orders in cryptotpair with no previous trades",
                                  details={
                                      'identifiers': identifiers,
                                      'orders': orders,
                                  })
            return False, False, False

    orders['price'] = price
    reporting.utils.audit(message="determined price of trade", details={
        'identifiers': identifiers,
        'orders': orders,
        'price': price,
        'price_match': price_match,
    })

    # Determine which of the orders are completely fulfilled by this trade:
    if order1.volume > order2.volume:
        volume = order2.volume
        completely_filled1 = False
        completely_filled2 = True
    elif order2.volume > order1.volume:
        volume = order1.volume
        completely_filled1 = True
        completely_filled2 = False
    else:
        volume = order1.volume
        completely_filled1 = True
        completely_filled2 = True

    base_volume = convert_quote_to_base(volume=volume, price=price)
    if base_volume <= 0:
        reporting.utils.audit(message="failed match, base_volume must be greater than 0",
                              details={
                                  'identifiers': identifiers,
                                  'orders': orders,
                                  'volume': volume,
                                  'price': price,
                                  'base_volume': base_volume,
                              })
        return False, False, False

    # Calculate fee based on actual volume traded
    buy_order_fee = order.utils.get_fee(order=buy_order, volume=volume)
    sell_order_fee = order.utils.get_fee(order=sell_order, volume=volume)

    # @TODO: Grab the per-user lock for the matched trade

    new_trade = trade.models.Trade(
        buy_order=buy_order,
        buy_order_settled_in=trade.models.SETTLED_NONE,
        buy_order_settled_out=trade.models.SETTLED_NONE,
        sell_order=sell_order,
        sell_order_settled_in=trade.models.SETTLED_NONE,
        sell_order_settled_out=trade.models.SETTLED_NONE,
        cryptopair=buy_order.cryptopair,
        price=price,
        volume=volume,
        base_volume=base_volume,
        buy_fee=buy_order_fee,
        sell_fee=sell_order_fee,
    )
    # .save() has no return value, so we run it after creating a new trade
    new_trade.save()
    new_trade_dict = model_to_dict(new_trade)
    new_trade_dict['id'] = new_trade.id

    reporting.utils.audit(message="created trade", details={
        'identifiers': identifiers,
        'orders': orders,
        'new_trade_dict': new_trade_dict,
    })

    data = {
        'recipient': None,
        'type': 'trade',
        'data': {
            'symbol': new_trade.cryptopair,
            'timestamp': new_trade.buy_order.created.replace(tzinfo=datetime.timezone.utc).timestamp(),
            'base': {
                'symbol': new_trade.sell_order.base_currency,
                'volume': new_trade.base_volume,
            },
            'quote': {
                'symbol': new_trade.sell_order.quote_currency,
                'price': new_trade.price,
                'volume': new_trade.volume,
            },
        },
        'timestamp': time.time(),
    }
    reporting.utils.notify_middleware(data)

    order1.filled += 1
    if completely_filled1:
        order1.open = False
        done = True
    else:
        order1.volume -= volume
        done = False
    order1.save()

    order2.filled += 1
    if completely_filled2:
        order2.open = False
    else:
        order2.volume -= volume
    order2.save()

    order1_dict = model_to_dict(order1)
    order2_dict = model_to_dict(order2)
    reporting.utils.audit(message="updated traded orders", details={
        'identifiers': identifiers,
        'orders': orders,
        'new_trade_dict': new_trade_dict,
        'new_order': order1_dict,
        'matched_order': order2_dict,
    })

    return new_trade_dict, done, True

# Helper to invoke /api/trade/history/ endpoint from a test.
def trade_history(self, token=None, data={}, offset=None, limit=None):
    url = reverse('trade:trade-history')

    if offset is not None:
        try:
            url += "?offset=%d" % offset
        except:
            print("invalid offset (%s), must be integer: %s" % (offset, str(e)))

    if limit is not None:
        try:
            if offset is not None:
                url += "&limit=%d" % limit
            else:
                url += "?limit=%d" % limit
        except Exception as e:
            print("invalid limit (%s), must be integer: %s" % (limit, str(e)))

    return spauser.utils.client_post_optional_jwt(self, url=url, token=token, data=data)
