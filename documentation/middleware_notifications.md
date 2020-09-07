Collects all the places the backend sends a notification to the middleware.

In all cases, the code invokes `reporting.utils.notify_middleware`:

--

In reporting.views, we notify the middleware of a 'new block' (added to the blockchain) or of an 'orphan block'
(removed from the blockchain).

```
  data = {
      'recipient': None,
      # 'new block' or 'orphan block'
      'type': content['event'],
      'data': {
          'type': content['type'],
          'symbol': content['symbol'],
          'height': content['height'],
          'hash': content['hash'],
          'timestamp': content['timestamp'],
      },
      'timestamp': time.time(),
  }
  reporting.utils.notify_middleware(data)
```

--

In reporting.views, we notify the middleware of 'wallet activity' (there has been a transaction associated with the
specified user id):

```
  data = {
      'recipient': str(spauser_id),
      'type': 'wallet activity',
      'data': {
          'event': content['event'],
          'type': content['type'],
          'symbol': content['symbol'],
          'height': content['height'],
          'hash': content['hash'],
          'timestamp': content['timestamp'],
          'address': address,
          'wallet': wallet_detail,
      },
      'timestamp': time.time(),
  }
  reporting.utils.notify_middleware(data)
```

--

In `trade.utils`, we notify the middleware when a trade happens. This is currently done globally.

```
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
```
