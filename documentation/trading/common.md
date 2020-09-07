The follow API endpoints are common among all exchanges, according to
the ccxt library:
https://github.com/ccxt/ccxt/wiki/Manual#unified-api


```Unified API

The unified ccxt API is a subset of methods common among the
exchanges. It currently contains the following methods:
```

 - fetchMarkets (): Fetches a list of all available markets from an exchange and returns an array of markets (objects with properties such as symbol, base, quote etc.). Some exchanges do not have means for obtaining a list of markets via their online API. For those, the list of markets is hardcoded.
 - loadMarkets ([reload]): Returns the list of markets as an object indexed by symbol and caches it with the exchange instance. Returns cached markets if loaded already, unless the reload = true flag is forced.
 - fetchOrderBook (symbol[, limit = undefined[, params = {}]]): Fetch L2/L3 order book for a particular market trading symbol.
 - fetchL2OrderBook (symbol[, limit = undefined[, params]]): Level 2 (price-aggregated) order book for a particular symbol.
 - fetchTrades (symbol[, since[, [limit, [params]]]]): Fetch recent trades for a particular trading symbol.
 - fetchTicker (symbol): Fetch latest ticker data by trading symbol.
 - fetchBalance (): Fetch Balance.
 - createOrder (symbol, type, side, amount[, price[, params]])
 - createLimitBuyOrder (symbol, amount, price[, params])
 - createLimitSellOrder (symbol, amount, price[, params])
 - createMarketBuyOrder (symbol, amount[, params])
 - createMarketSellOrder (symbol, amount[, params])
 - cancelOrder (id[, symbol[, params]])
 - fetchOrder (id[, symbol[, params]])
 - fetchOrders ([symbol[, since[, limit[, params]]]])
 - fetchOpenOrders ([symbol[, since, limit, params]]]])
 - fetchClosedOrders ([symbol[, since[, limit[, params]]]])
 - fetchMyTrades ([symbol[, since[, limit[, params]]]])


## Order books
Order books should support 2 or 3 levels of detail (market depth):

 - L1: less detail for quickly obtaining very basic info, namely, the market price only. It appears to look like just one order in the order book.
 - L2: most common level of aggregation where order volumes are grouped by price. If two orders have the same price, they appear as one single order for a volume equal to their total sum. This is most likely the level of aggregation you need for the majority of purposes.
 - L3: most detailed level with no aggregation where each order is separate from other orders. This LOD naturally contains duplicates in the output. So, if two orders have equal prices they are not merged together and it's up to the exchange's matching engine to decide on their priority in the stack. You don't really need L3 detail for successful trading. In fact, you most probably don't need it at all. Therefore some exchanges don't support it and always return aggregated order books.



## Price ticker
A price ticker contains statistics for a particular market/symbol for some period of time in recent past, usually last 24 hours. The structure of a ticker is as follows:

 - 'symbol':        string symbol of the market ('BTC/USD', 'ETH/BTC', ...)
 - 'info':        { the original non-modified unparsed reply from exchange API },
 - 'timestamp':     int (64-bit Unix Timestamp in milliseconds since Epoch 1 Jan 1970)
 - 'datetime':      ISO8601 datetime string with milliseconds
 - 'high':          float, // highest price
 - 'low':           float, // lowest price
 - 'bid':           float, // current best bid (buy) price
 - 'bidVolume':     float, // current best bid (buy) amount (may be missing or undefined)
 - 'ask':           float, // current best ask (sell) price
 - 'askVolume':     float, // current best ask (sell) amount (may be missing or undefined)
 - 'vwap':          float, // volume weighed average price
 - 'open':          float, // opening price
 - 'close':         float, // price of last trade (closing price for current period)
 - 'last':          float, // same as `close`, duplicated for convenience
 - 'previousClose': float, // closing price for the previous period
 - 'change':        float, // absolute change, `last - open`
 - 'percentage':    float, // relative change, `(change/open) * 100`
 - 'average':       float, // average price, `(last + open) / 2`
 - 'baseVolume':    float, // volume of base currency traded for last 24 hours
 - 'quoteVolume':   float, // volume of quote currency traded for last 24 hours
 
```
    The bidVolume is the volume (amount) of current best bid in the
     orderbook.
    The askVolume is the volume (amount) of current best ask in the
     orderbook.
    The baseVolume is the amount of base currency traded (bought or
     sold) in last 24 hours.
    The quoteVolume is the amount of quote currency traded (bought
     or sold) in last 24 hours.
```

```
prices in ticker structure are in quote currency
```

## OHLCV Charts
 - OHLCV Candlestick Charts
 - https://en.wikipedia.org/wiki/Open-high-low-close_chart
 - open-high-low-close chart
 
> There's a limit on how far back in time your requests can go. Most of exchanges will not allow
> to query detailed candlestick history (like those for 1-minute and 5-minute timeframes) too far
> in the past. They usually keep a reasonable amount of most recent candles, like 1000 last
> candles for any timeframe is more than enough for most of needs. You can work around that
> limitation by continuously fetching (aka REST polling) latest OHLCVs and storing them in a CSV
> file or in a database.

## Trades

```
[
    {
        'info':       { ... },                  // the original decoded JSON as is
        'id':        '12345-67890:09876/54321', // string trade id
        'timestamp':  1502962946216,            // Unix timestamp in milliseconds
        'datetime':  '2017-08-17 12:42:48.000', // ISO8601 datetime with milliseconds
        'symbol':    'ETH/BTC',                 // symbol
        'order':     '12345-67890:09876/54321', // string order id or undefined/None/null
        'type':      'limit',                   // order type, 'market', 'limit' or undefined/None/null
        'side':      'buy',                     // direction of the trade, 'buy' or 'sell'
        'price':      0.06917684,               // float price in quote currency
        'amount':     1.5,                      // amount of base currency
    },
    ...
]

Most exchanges return most of the above fields for each trade, though there are exchanges that
don't return the type, the side, the trade id or the order id of the trade. Most of the time you
are guaranteed to have the timestamp, the datetime, the symbol, the price and the amount of each
trade.
```

Some behind the scenes discussion of how trades work and are matched to orders is documented here:
https://github.com/ccxt/ccxt/wiki/Manual#how-orders-are-related-to-trades

## Orders

```
{
    'id':                '12345-67890:09876/54321', // string
    'datetime':          '2017-08-17 12:42:48.000', // ISO8601 datetime of 'timestamp' with milliseconds
    'timestamp':          1502962946216, // order placing/opening Unix timestamp in milliseconds
    'lastTradeTimestamp': 1502962956216, // Unix timestamp of the most recent trade on this order
    'status':     'open',         // 'open', 'closed', 'canceled'
    'symbol':     'ETH/BTC',      // symbol
    'type':       'limit',        // 'market', 'limit'
    'side':       'buy',          // 'buy', 'sell'
    'price':       0.06917684,    // float price in quote currency
    'amount':      1.5,           // ordered amount of base currency
    'filled':      1.1,           // filled amount of base currency
    'remaining':   0.4,           // remaining amount to fill
    'cost':        0.076094524,   // 'filled' * 'price' (filling price used where available)
    'trades':    [ ... ],         // a list of order trades/executions
    'fee': {                      // fee info, if available
        'currency': 'BTC',        // which currency the fee is (usually quote)
        'cost': 0.0009,           // the fee amount in that currency
        'rate': 0.002,            // the fee rate (if available)
    },
    'info': { ... },              // the original unparsed order structure as is
}

    The work on 'fee' info is still in progress, fee info may be missing partially or entirely, depending on the exchange capabilities.
    The fee currency may be different from both traded currencies (for example, an ETH/BTC order with fees in USD).
    The lastTradeTimestamp timestamp may have no value and may be undefined/None/null where not supported by the exchange or in case of an open order (an order that has not been filled nor partially filled yet).
    The lastTradeTimestamp, if any, designates the timestamp of the last trade, in case the order is filled fully or partially, otherwise lastTradeTimestamp is undefined/None/null.
    Order status prevails or has precedence over the lastTradeTimestamp.
    The cost of an order is: { filled * price }
    The cost of an order means the total quote volume of the order (whereas the amount is the base volume). The value of cost should be as close to the actual most recent known order cost as possible. The cost field itself is there mostly for convenience and can be deduced from other fields.
```


