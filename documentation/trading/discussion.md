# Discussion points

## Fees
 - "normally charged in quote currency"
 - maybe better for us to charge in BTC always?
 - some exchanges always charge in USD, for example
```
    o is there a buy and sell fee?
    o this is something we can change later
    o right now, do the most simple thing / or the most common thing
```
 - what about canceled orders? do we strip away network fees?
```
    o don't make money on them, but don't lose many either
```
 
## Architecture
 - tend to give it a try and tweak
 - better to whiteboard it out? is there a good virtual whiteboard?
```
    o white board's for slack
    o can move to something else
    o can find another way
```

## Public API
 - it looks like all (?) exchanges have public APIs
 - can it be exposed through the middleware?
 - where do we rate limit? (what control do we have, ie another exchange would get different rates)
 - how much API do we expose for MVP?
```
    o yes, middleware will expose and rate-limit; perfect for this
    o don't rate-limit on backend, minimize complexity
```
 
## Crypto pairs
 - as few as possible? ie, BTC/LTC and BTC/DOGE?
 - as many as possible? ie, also LTC/DOGE?
 - few requires more exchanges to navigate between lesser coins (more fees for us)
 - more exchanges is also better for the market in general: lots of lightly traded markets less good
 - more maybe is interesting to people playing with altcoins
 - I'd be more likely to spend LTC on DOGE than BTC, psychologically it means less to me
```
    o to be decided on a per-coin basis
    o bigger markets should have pairs
    o my gut feeling is we should avoid lots of delistings: avoid adding pairs unless it's likely to
      be traded
```
 
## Decimal versus float versus two numbers
 - there's not actually two numbers
 - for example: BTC/LTC has a single price: how many LTC can I buy with my BTC?
 - so the number for BTC (the base currency: the first in the pair) is always 1
 - whereas the number for LTC fluctuates, currently something like 127.67
 
## Value
 - altcoin value is generally defined by what you can trade it for
 - do we display value as a fraction of BTC?
 - do we use a third-party API to display value in USD?  EUR?
 - do we make this configurable to the end-user?
 - MVP: BTC is currently the main crypto currency, IMO we should launch w/ value-per-BTC
 - (we'd even show this for a LTC/DOGE pair, in addition to the # of Doge you can buy with 1 LTC)
```
    o coinbase does show value in USD
    o for someone not very familiar with crypto currency, having in own value helps a lot
    o third-party service would provide all currencies
    o = instead of =
    o MVP
    o BTC is an option, not just USD/Eur/Yen, etc: three is confusing
```
 
## Primitive versus Modern
 - do we want to release a "primitive" exchange as MVP?
 - I worry that we'll be judged based on our launch, and it will be an uphill battle to get people
   to retest
```
    o doesn't know how exchanges grow, but there are many exchanges in the world
    o start at the bottom of the list of exchanges, and our goal should be to go up that list
    o we will never get to Coinbase or Kraken: but if #20 that's awesome
    o how would it happen? 
    o word of mouth
    o strengths: 
      o security, implicit security in the model of the exchange
      o scalabilty: never fail, at worst just slow
      o simple: try and make as simple as possible; coinbase is already quite easy to use, maybe
      o transparency: implicit in the model, when people give us their model, have ways to make sure
        they can see that their money is still there (for money they're not trading)
    o launch as testnet exchange? and/or closed beta? can be primitive as a testnet exchange
    o get feedback/ideas of what's important
    o open apis on testnet, let people design software for free
```
    
 - for MVP we may need a fully implemented "hot wallet"
 - people can chose to move their money into a hot trading account at which time trades can happen
   in near-real-time (because we handle ownership in the exchange, not with the blockchain)
 - what we've been building is more like a walletless exchange: they're not a good fit for
   big traders and automation as you've gotta move coins multiple times for each exchange: this is
   very slow
 - for MVP we may want the above PLUS off-blockchain trading: the latter can be automated and
   allows for very high volumes of trading: the money sits in an exchange account instead of in
   individual user's accounts (but in their wallets they'll see it as their money: ie "available
   money" and "trading money" or something like that)
 - my biggest fear is security: how do we securely manage a large wallet auto-managed by the
   exchange? how do we detect hacks/bugs quickly and shut things down? Can we even shut it down,
   perhaps what would be stolen would be the HD key then all is lost ...?
 - we could modify HD wallets to add some obsfucation: ie, a hacker wouldn't know how to derive our
   keys from the private keys if we don't follow the BIP without reading our code
 - we can also auto-rotate exchange wallets: so only a % are "hot", and the rest are "cold" -- but
   the formula for hot versus cold is critical, if we run out of hot money everything grinds to
   a halt
 - hot money is money the live exchange can spend (ie the keys are stored in the server)
 - cold money is money the live exchange can not spend (ie the keys are not stored in the server)
```
     o two strategies (find way tot do w/o, check and verify as much as possible)
        - find a way to do that without / somewhere the key to the wallet needs to be there
        - scheduled payouts: accounting only in the exchange, not on the blockchain
          (allows performance and security)
     o hot wallets are post-MVP if at all: they are dangerous
```

## Security solutions for the exchange wallet:
 - Utilize HD wallet, autogenerating new addresses for receiving money and change
 - For our user's HD wallets we only use 1 account per coin: for the exchange we should rotate the
   account regularly (either daily or every N bitcoins) so when we schedule payments we're only
   unlocking a fraction of the coins we manage
 - Consider modifying the HD wallet algorithm to NOT be BIP compatible: so if someone steals the
   keys it's not enough to derive all addresses and keys: be careful to not add a weakness to the
   algorithm in the process
 - The exchange _never_ has the private keys: it only can receive money
 - Trades are done through accounting
 - Audit-Audit-Audit: any/all changes should generate an audit log entry, allowing us to reply
   all trades, etc
 - Users can have funds in their private, secure wallet, or in the an active wallet: in the latter
   case they do not see the actual bitcoins, they only see our accounting of what they own
 - Requests to cash out of their active wallet (whether to their secure wallet, or to a remotely
   hosted wallet/address) are told "please allow 1 business day" or whatever time period we can
   reliably accomplish
 - Cashing out will require multiple people to enter a correct private key: the combination together
   of which will unlock the necessary HD wallet(s) and send the funds
 - The private keys for the exchange HD wallets must be different than the private keys used to
   unlock our user's private keys when they lose their passphrase
 - A full automated audit should happen before any funds are sent: it should validate all totals
   and confirm we're not trying to send more than we have (or a wrong amount in any way) - if
   inconsistencies are detected we'd need to dig into audit logs and figure out what happened
 - We should have logic to replay audit logs allowing us to regenerate expected balances/trades
   automatically: if/when we need the logs the quicker we can review the better
