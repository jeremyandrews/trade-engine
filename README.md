# Overview

This is an old project that was never completed, but that I'm releasing as
open source for anyone who may be interested.

This codebase is released under the GPL v3. 
https://opensource.org/licenses/GPL-3.0

To request the codebase under a different license, please explain your
need and intent clearly.


## API

### Create user

Example:
```
$ curl -X POST http://localhost:8000/api/user/create/ --data 'email=joe@example.com&password=securepass'
{"email":"joe@example.com","id":"4c0a64ff-841b-4c58-a2cf-dc2a9521fa19"}
```

### Login

Example:
```
  $ curl -X POST http://localhost:8000/api/user/login/ --data 'email=joe@example.com&password=securepass'
  {"token":"eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImpvZUBleGFtcGxlLmNvbSIsImV4cCI6MTUzNzg2Nzg1MSwiZW1haWwiOiJqb2VAZXhhbXBsZS5jb20iLCJvcmlnX2lhdCI6MTUzNzg2Njk1MSwib3RwX2RldmljZV9pZCI6bnVsbH0.34Kzjj4iFedDshGg2K_ZezNEtJHQYEBz5VZnZShN7uU"}
```

### Create wallet seed

We create one wallet seed per user, and use it to generate all wallets, addresses, and private keys. The
seed is generated using cryptographically secure entropy, and then encrypted with the user's passphrase.

Example:
```
  $ curl -X POST http://localhost:8000/api/wallet/create-seed/ --data 'passphrase=thisISs3cured00d!'  -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImpvZUBleGFtcGxlLmNvbSIsImV4cCI6MTUzNzg2Nzg1MSwiZW1haWwiOiJqb2VAZXhhbXBsZS5jb20iLCJvcmlnX2lhdCI6MTUzNzg2Njk1MSwib3RwX2RldmljZV9pZCI6bnVsbH0.34Kzjj4iFedDshGg2K_ZezNEtJHQYEBz5VZnZShN7uU'
  {'status': 'seed created', 'code': 200, 'debug': {}, 'data': {}}
```

#### Responses
 - 200 OK `seed created` (successfully created)
 - 200 OK `seed already created` (failed to create as it's already created)
 - 400 Bad Request `passphrase is required` (failed to provide a passphrase):
```
 {'status': 'passphrase is required', 'code': 400, 'debug': {'exception': "'passphrase'"}, 'data': {}}
```

#### Debug
In debug mode, the internal secrets are exposed. These could be used to move the entire wallet into another
HD wallet supporting the same BIPs we've embraced, exposing all public AND private keys.
```
{'status': 'seed created', 'code': 200, 'debug': {'mnemonic': 'wish skate cart prison divorce garbage cycle produce choice peasant margin above coast uphold october bridge daring knock credit student smile document crush element', 'salt': '7dogRIQZ3YAYHRDSPGb-EQEQhzX1bKCPbRm9hTtWlxzRa50_fGI0ly0kpYkPU0wd', 'passphrase': 'thisISs3cured00d!'}, 'data': {}}
```


### Create wallet
We currently only allow the creation of one wallet per coin-type per-user (with a label of "default"). The
same passphrase used to create the wallet seed must be used when creating a wallet, to unlock the seed.

Example:
```
  $ curl -X POST http://localhost:8000/api/wallet/create/ --data 'label=default&currencycode=BTC&passphrase=thisISs3cured00d!' -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImpvZUBleGFtcGxlLmNvbSIsImV4cCI6MTUzNzg2Nzg1MSwiZW1haWwiOiJqb2VAZXhhbXBsZS5jb20iLCJvcmlnX2lhdCI6MTUzNzg2Njk1MSwib3RwX2RldmljZV9pZCI6bnVsbH0.34Kzjj4iFedDshGg2K_ZezNEtJHQYEBz5VZnZShN7uU'
  {'status': 'wallet created', 'code': 200, 'debug': {}, 'data': {'id': 'a21d3457-530a-4182-8abc-f2131c3f7d1c', 'label': 'default', 'description': None, 'coin': 'bitcoin', 'symbol': 'BTC'}}
```

#### Responses
 - 200 OK `wallet created` (successfully created)
 - 200 OK `seed already created` (failed to create as it's already created)
 - 200 OK `wallet already exists` (wallet for this currency already exists)
``` {'status': 'wallet already exists', 'code': 200, 'debug': {'request': {'label': 'default', 'currencycode': 'BTC', 'passphrase': 'thisISs3cured00d!'}}, 'data': {}} ```
 - 400 Bad Request `passphrase is required` (failed to provide a passphrase):
``` {'status': 'passphrase is required', 'code': 400, 'debug': {'exception': "'passphrase'", 'request': {'label': 'default', 'currencycode': 'BTC'}}, 'data': {}} ```
 - 400 Bad Request `currencycode is required` (failed to provide a passphrase):
``` {'status': 'currencycode is required', 'code': 400, 'debug': {'exception': "'currencycode'", 'request': {}}, 'data': {}} ```
 - 400 Bad Request `invalid passphrase` (using the wrong passphrase)
``` {'status': 'invalid passphrase', 'code': 400, 'debug': {'passphrase': 'thisISs3cured00d!', 'request': {'label': 'default', 'currencycode': 'BTC', 'passphrase': 'sillyANDwrong'}}, 'data': {}} ```
 - 400 Bad Request `invalid data` (set label to something other than 'default')
``` {'status': 'invalid data', 'code': 400, 'debug': {'request': {'label': 'something random', 'currencycode': 'BTC', 'passphrase': 'thisISs3cured00d!'}, 'errors': {'label': ["Label must be 'default'"]}}, 'data': {}} ```
 - 400 Bad Request `invalid data` (set currencycode to unsupported symbol)
``` {'status': 'invalid data', 'code': 400, 'debug': {'request': {'label': 'default', 'currencycode': 'NONE', 'passphrase': 'thisISs3cured00d!'}, 'errors': {'currencycode': ['Unrecognized currency code']}}, 'data': {}} ```

#### Debug
In debug mode, the public and private keys are exposed, from which all addresses can be found and any
funds in those coins can be spent. We also expose other internal information like when the wallet was
created, last updated, and HD wallet details including the highest index used for external and changed
addresses.
```
{'status': 'wallet created', 'code': 200, 'debug': {'created': '2018-11-13T11:56:08.423469Z', 'modified': '2018-11-13T11:56:08.596277Z', 'last_external_index': 0, 'last_change_index': 0, 'private_key': 'xprv9xiP4rWWvSrETwPG1TnzXKy43VvfBDzJWh3NhLto7s5xo9GWUr8p1XKHvq6Cs5eZgPZ5myMwFUdZh22QiRwm1x82gGBu32sH7cFrAhGTzBd', 'public_key': 'xpub6BhjUN3QkpQXgRTj7VKztTunbXm9agi9suxyVjJQgCcwfwbf2PT4ZKdmn7h6E55DPhNpVG8J6abFF5DPLfeLMBLoHXDsKpgHVksJNqzPCnJ'}, 'data': {'id': 'a21d3457-530a-4182-8abc-f2131c3f7d1c', 'label': 'default', 'description': None, 'coin': 'bitcoin', 'symbol': 'BTC'}}
```


### List wallets (and their balances)
This endpoint lists some information about all a user's wallets, including: wallet id (uuid); wallet label (always default);
wallet description (optionally set during creation); wallet currency code; wallet balance (total unspent for all coins
in the wallet); address count (how many addresses are in the wallet, including external and change addresses); 404 count
(how many addresses in the wallet don't yet show up on the blockchain); how many errors there were, and what
the errors were. If there are errors, something is wrong and the wallet listing isn't accurate -- re-request.

No parameters are required, just user authentication.

Example:
```
  $ curl -X POST http://localhost:8000/api/wallet/list/ -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6ImpvZUBleGFtcGxlLmNvbSIsImV4cCI6MTUzNzg2Nzg1MSwiZW1haWwiOiJqb2VAZXhhbXBsZS5jb20iLCJvcmlnX2lhdCI6MTUzNzg2Njk1MSwib3RwX2RldmljZV9pZCI6bnVsbH0.34Kzjj4iFedDshGg2K_ZezNEtJHQYEBz5VZnZShN7uU'
  {'status': '1 wallet found', 'code': 200, 'debug': {}, 'data': [{'id': '9cc6d181-7c59-4887-9675-51974cc7936c', 'label': 'default', '~ription': None, 'currencycode': 'BTC', 'balance': 0, 'address_count': 0, '404_count': 0, 'error': [], 'error_count': 0}]}
```

#### Responses
 - 200 OK `1 wallet found` (lists one or more wallets, if more than one: `n wallets found`)
 - 200 OK `no wallets found` (no wallets created yet)

#### Debug
Displays exception information if an exception happens while listing wallets.


### Create address
Generates an "external address" from the wallet's public key. This means the address does not have an
associated WIF so money at that address can't be spent. (In order to spend it, you have to use a different
endpoint which decrypts the private key with the user's passphrase, and from that re-generates from the
wallet's private key, so there's an associated WIF)

@TODO: Currently we only return 1 unused address at a time. We eventually will support a gap-limit of 20,
whereby we can create up to 20 unused addresses. An unused address is one that doesn't (yet) show up on the
blockchain. Therefor, currently if you call this endpoint repeatedly you'll keep getting the same address
back.

Example:
```
  $ curl -X POST 127.0.0.1:8000/api/address/create/ --data 'wallet_id=f43f094e-f2d1-4ecc-a13d-1573c78ca171&label=test' -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6Im1lQGV4YW1wbGUuY29tIiwiZXhwIjoxNTM3OTk2NTk5LCJlbWFpbCI6Im1lQGV4YW1wbGUuY29tIiwib3JpZ19pYXQiOjE1Mzc5OTU2OTksIm90cF9kZXZpY2VfaWQiOm51bGx9.U8XPcB6B4dZMllFvhw3NdSXelk3lEUVzJlhIAg477ps'
  {'status': 'address created', 'code': 200, 'debug': {}, 'data': {'id': 'c58d78f3-8c93-45e3-922c-06ab0cfefb12', 'label': 'test', 'description': None, 'p2pkh': '12H8X5xEHRhPsYicGRfAZovrxHuKQo8xSH', 'index': 0, 'is_change': False, 'wallet_id': 'f43f094e-f2d1-4ecc-a13d-1573c78ca171', 'coin': 'bitcoin', 'symbol': 'BTC'}}
```

#### Parameters
 - wallet_id: a uuid unique to that wallet
 - label: an optional label for the address

#### Responses
 - 200 OK `address created` (new address created and added to wallet)
 - 200 OK `address already exists` (returned an address that was previously created and already in wallet):
``` {'status': 'address already exists', 'code': 200, 'debug': {}, 'data': {'id': 'c58d78f3-8c93-45e3-922c-06ab0cfefb12', 'label': 'test', 'description': None, 'p2pkh': '12H8X5xEHRhPsYicGRfAZovrxHuKQo8xSH', 'index': 0, 'is_change': False, 'wallet_id': 'f43f094e-f2d1-4ecc-a13d-1573c78ca171', 'coin': 'bitcoin', 'symbol': 'BTC'}} ```
 - 200 OK `wallet not found` (no address created, specified wallet does not exist)
``` {'status': 'wallet not found', 'code': 200, 'debug': {'user_id': '5e0e5389-ed55-4893-ae5e-7a104ad77a32', 'wallet_id': 'no-such-wallet', 'exception': '["\'no-such-wallet\' is not a valid UUID."]'}, 'data': {}} ```
 - 400 Bad Request `wallet_id is required` (failed to provide a wallet id):
 - 400 Bad Request `invalid data` (set currencycode to unsupported symbol)
 - 500 Internal Server Error `wallet missing private key` (@TODO: remove, this shouldn't be a thing)
 - 502 Bad Gateway `request to blockchain daemon failed` (unexpected error with blockchain backend)


### List addresses
Lists all addresses in a wallet, and all available information about those addresses. It's important to
review the `error_count`, as if it's non-zero then something is wrong and the provided information very
likely is incomplete. The `404_count` is not particularly important, this is from addresses being added
to the wallet that have not yet made it into the blockchain (ie, you've not yet received funds at the
address).

Within the `addressapi` you can find the current `balance` (ie, the unspent value). Inside
the `total` structure you can get details on how many satoshi have been `received` versus
`sent`. You can also refer to `blockcount` to see how many blocks are currently on the
blockchain.

Also within the `addressapi` dictionary is a breakdown of all `transactions` associated
with the address. Of particular interest is the `confirmations` field, as this indicates
how long the transaction has been on the blockchain. From 1 to 6 confirmations we climb
from 20% to 100% confidence that the funds are permanent (ie, 1 confirmation is 20%
confidence, 2 confirmations is 40% confidence, etc). Transactions are either `received`
or `sent`. Most relevant to sent transactions, you can see the fee that was required to
send funds.

Example:
```
  $ curl -X POST 127.0.0.1:8000/api/address/list/ --data 'wallet_id=b3927246-e759-405e-a247-4b35a5ba7b6c' -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6Im1lQGV4YW1wbGUuY29tIiwiZXhwIjoxNTM3OTk2NTk5LCJlbWFpbCI6Im1lQGV4YW1wbGUuY29tIiwib3JpZ19pYXQiOjE1Mzc5OTU2OTksIm90cF9kZXZpY2VfaWQiOm51bGx9.U8XPcB6B4dZMllFvhw3NdSXelk3lEUVzJlhIAg477ps'
  {'status': 'OK', 'code': 200, 'debug': {}, 'data': {'wallet': {'id': '09c506e6-3d03-412e-aabb-ae0da8700c0f', 'label': 'default', 'balance': 40000000000, 'addresses': 2, '404': [{'id': '8d72257b-f19c-41b0-889c-555f1bead3df', 'address': 'mgd8cDwcd4NaJPBrA6aAf4WMbQg8RZQiSC'}], '404_count': 1, 'error_count': 0, 'description': None, 'currencycode': 'XLT'}, 'addresses': [{'id': '8d72257b-f19c-41b0-889c-555f1bead3df', 'label': 'testnet', 'description': None, 'p2pkh': 'mgd8cDwcd4NaJPBrA6aAf4WMbQg8RZQiSC', 'bech32': None, 'addressapi': {'status': 'ERROR', 'code': 404, 'error': 'not found', 'debug': [], 'data': {'coin': 'litecoin_testnet4', 'symbol': 'XLT', 'address': {'isvalid': True, 'address': 'mgd8cDwcd4NaJPBrA6aAf4WMbQg8RZQiSC', 'scriptPubKey': '76a9140c233b0b64c3399b57130f5ad83f5779beb390ed88ac', 'isscript': False, 'iswitness': False}}, 'url': 'http://exchange-web:8001/api/address/litecoin_testnet4/mgd8cDwcd4NaJPBrA6aAf4WMbQg8RZQiSC'}}, {'id': 'a759d8af-34a5-4e2f-9ddc-6d5bb6ff0972', 'label': 'manual', 'description': None, 'p2pkh': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'bech32': None, 'addressapi': {'status': 'OK', 'code': 200, 'debug': [], 'data': {'coin': 'litecoin_testnet4', 'symbol': 'XLT', 'address': {'isvalid': True, 'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'scriptPubKey': '76a914e1695f94761ea72282c04b7b5ea200ac0258cfd988ac', 'isscript': False, 'iswitness': False}, 'balance': 40000000000, 'total': {'received': 121000000000, 'sent': 81000000000, 'vin': 9, 'vout': 13, 'blockcount': 843237}, 'transactions': [{'txid': '1628711f407ce4b39523f713e9428cbdf4bc5a209e881ecb081973ae4261d3ff', 'block': 469869, 'confirmations': 373368, 'timestamp': 1521094942, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'aacda0826445a855364b151429742ea711605c4ed47c49f0aeb613baa2c48f4e', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'a34f94946394c82e07c1e9235d55404b32e3bf191d916330044397d8167313d7', 'vout': '0'}}, {'address': 'mjnHsCzRWjXfgRTu86Ny1AsDD2Qt92JfDt', 'value': 2136159800, 'spent': {'txid': 'f701fe5dcf9ad38c9673aa64050296508b423d8669b40f1be4752ca8f9c3a1ed', 'vout': '1'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'mzMQK8eirMbtLWt3TtPVbLbPCPYwaxg9Wb', 'vout': '1', 'value': 2126159800}], 'to_count': 2}, {'txid': '34bd0d542bf982c637582b78515adc1b5e5daa7e2f7e8bb4af9910c106e507ed', 'block': 410564, 'confirmations': 432673, 'timestamp': 1519137297, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '54766fe0f49c355f59d831bc6f72273c6f5511158000561b9bc2a20b02425506', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'bdda37779a7674ee4f2f79c11a92a93c0091c32b938833df2bc982e5a7be7a41', 'vout': '0'}}, {'address': 'mw5hk7QL4FjvFpN5XTqnQe7GyL9gA5QbLq', 'value': 1478000, 'spent': {'txid': '0d321dd4068e471925ca027bf548bdc02024eec09f1c17a6921164b901452f2f', 'vout': '1'}}], 'from_count': 3, 'fee': 52200, 'to': [{'address': 'mrZRg5dMRKQWegddkCaKxUDdUxsen5K23n', 'vout': '0', 'value': 1425800}, {'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '1', 'value': 10000000000}], 'to_count': 2}, {'txid': '41a749595a6d23f0e836345c3d04e6790a9ce6b77dd500dc9fda2c634700bde4', 'block': 428205, 'confirmations': 415032, 'timestamp': 1519620886, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '821b6a0019f0152a177f1bbfc1f2c7018f18ee40a31646ecfc45ca0826bfd261', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'e19f4b41499e2339e590dff99eb24bcafa0eae58ffb1966fa426abc5821dcec9', 'vout': '0'}}, {'address': 'mvY9y1UxsR23FwsPYy5A34usvmB6jZaXrJ', 'value': 955832200, 'spent': {'txid': 'c9b2c8fc7a0b2ee63a47b8745ca01b0db8a5524fa752fd191e2bf88bc9c03eb2', 'vout': '1'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'myFZhAK2v8baEfRJXRN2CXFTaWRXfhzqtK', 'vout': '1', 'value': 945832200}], 'to_count': 2}, {'txid': '4a80dc87f8a5f2e4f66bd17bdfcb87de45f64d0467814843964de2a9bfbf7615', 'block': 390496, 'confirmations': 452741, 'timestamp': 1518741431, 'type': 'received', 'from': [{'address': 'mzheTvcPBYkGxVGhXD1b83Kocn1xqB2bfe', 'value': 1441222600, 'spent': {'txid': '1af9aa9ed0bc9321d3bd60944936c609c0840bba9084786c28ead6a6091e2655', 'vout': '1'}}], 'from_count': 1, 'fee': 22600, 'to': [{'address': 'mpApeiGcJFZ9cGaS2c2msxpVECASLMMjq6', 'vout': '0', 'value': 441200000}, {'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '1', 'value': 1000000000}], 'to_count': 2}, {'txid': '5b71d0408d114bd04f2be5382c2780262af996ffe4827795845f101a7d4a1d6e', 'block': 465822, 'confirmations': 377415, 'timestamp': 1520777316, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'b19d22ff270a5194bc6a86841a06b31ddeee947445662cfaaa4fcf3722443e53', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '0c0fd67ff6182cf71785e2f56cb935cd6904cdf0c10888bdc2014982138ddc87', 'vout': '0'}}, {'address': 'mnHf2BgmVGmck43NDSw4NmmvCsRJrMukYm', 'value': 1843919800, 'spent': {'txid': 'e2f3d1f2d73daecab3648ff66dd52459e60089a4388e8c17ca03a5e1bac271e4', 'vout': '0'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'ms9Z1SD4Gu2yLbLL66fhFn7D7kRF7ZTWA1', 'vout': '0', 'value': 1833919800}, {'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '1', 'value': 10000000000}], 'to_count': 2}, {'txid': '848650bed53826dff7c6df21cc806200a4ad33e9428ec28b5883691c2c637285', 'block': 389474, 'confirmations': 453763, 'timestamp': 1518570362, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '8bbae70a0dd335b19c1beb0c7309c881440354bf6ac7238b35af10f76952f287', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'a37f8ad46f8255e630ab458b3e74bdca63b2bc7db8977aed79be53789c621c9b', 'vout': '0'}}, {'address': 'mzSfUjpyftcv9rPErgqWnJiwvEHfagmufL', 'value': 1923617, 'spent': {'txid': '8329c5eacf05535db9c5edfb75cb5958f3ff9c3172fa718c1f3c9ec1fbb36bed', 'vout': '1'}}], 'from_count': 3, 'fee': 52200, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'mtomATXmHV9SHanPjYWkMwXHmj5frVSE44', 'vout': '1', 'value': 1871417}], 'to_count': 2}, {'txid': '885f4c31f2577e93b393114d341a98fc019473b349a0a877483efe71ec1d7963', 'block': 427490, 'confirmations': 415747, 'timestamp': 1519534400, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'f28df1ec3a64721fa1b5246fdcec6519e3d223a8a4a341eb5e5ac4b1c7f0ba33', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '9f3eb96d090575531fb3a7670110ca1fafb6adcb94f3467e20dea76f4c43885a', 'vout': '0'}}, {'address': 'n1d32wL5chZ1MrgCdDU3tJVrgq1QCtkzUf', 'value': 47340000, 'spent': {'txid': '29529cea436477f86e490c429834e475af4ba5585411d106f0f812395a06151f', 'vout': '1'}}], 'from_count': 3, 'fee': 52200, 'to': [{'address': 'mu2Hkj98e3uD8qs82g9Q7NQ4g1scMpFyb5', 'vout': '0', 'value': 47287800}, {'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '1', 'value': 10000000000}], 'to_count': 2}, {'txid': 'a8c31123fc89b732bde3b886d63a73a53ccbb1e4e0a2a72c0e72198b9ef29626', 'block': 429047, 'confirmations': 414190, 'timestamp': 1519726475, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '4eb533046f17484bec7b226a9951f63d6d5cf25ddac1e6252dc6368f3872e37c', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '00f508c457fcdd6171b6bbfdbc811106fa741bbc65e6b4e85e13f2de51625dc5', 'vout': '0'}}, {'address': 'n26qF2CcvXJYV6GRN2TEwnneSGWYsPYZks', 'value': 197583097, 'spent': {'txid': '09f33eaf54e283f8d910b7ded851eb2035b5cf6af90a87ee8217c85709bdf93b', 'vout': '0'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'mxf5wxHrH7q17dTYFLDiCzWfQVb544Kmuz', 'vout': '1', 'value': 187583097}], 'to_count': 2}, {'txid': 'b87b10a5a0388321a12b15e6d0779fe3a9e72fb0c03b3a91d7a773613f3b97af', 'block': 391050, 'confirmations': 452187, 'timestamp': 1518832807, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'a80b28922eabbf72e352d2237f3f08df270348c1fb0ff1b5dea30be7e40c2266', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '55d2b3374b7f3788af8e8db8c943433a5dfec95bee81bca6732b01dedda960f2', 'vout': '0'}}, {'address': 'my8Egk4DoJJhALEQnYoaCKbk8nJx6ryxiA', 'value': 357710400, 'spent': {'txid': 'd51e055f3e7680e418827c7a0c8afa6a004c05b4ede5aba680b1f398e18079e7', 'vout': '0'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'mfZSfK6wZHwUrb85Mu1XcHnwL1d2rFkE4F', 'vout': '0', 'value': 347710400}, {'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '1', 'value': 10000000000}], 'to_count': 2}, {'txid': 'dd6f3416914f32539e7d923c81be83aa750259caef547337237660a493b0cb6c', 'block': 430905, 'confirmations': 412332, 'timestamp': 1519973187, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'e28ebd2ea98cde3fbacf7a62ea744a7a083e5b0ce30eaca2907086c362ed4c38', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'cc9b1e7ae919a5b355ae790c3cdeb617f76dcfc14f897fc82bfc8873a34d08ec', 'vout': '0'}}, {'address': 'mn98jrUAPMMSeCHX1xZ4U8nQiicdrWLtfn', 'value': 2877400775, 'spent': {'txid': '83d75c803f958dee91b83b2e813a489b5d44ed68983cb5128cba910930d5e942', 'vout': '0'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'mqYkXS1St67h656u9YryCw4rR8bTwv78HX', 'vout': '1', 'value': 2867400775}], 'to_count': 2}, {'txid': 'eb97ffbd35dbf9fd8238966cbc977f0ed641078edcf5254174257ac7ea2586ac', 'block': 430406, 'confirmations': 412831, 'timestamp': 1519898683, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'e6e41f909096dd89287b8b223518afc0831fe7b41131d978df7c8ca1a649440b', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '99cdcad45c70fe4845d723d152ffa65e398f577ff7f4f1b8bb260ed5e86383ee', 'vout': '0'}}, {'address': 'n1WESwdpcr1grLXbKZa3eBbxdAsVviuLi3', 'value': 345609600, 'spent': {'txid': '448926e236ceec32054829d58b65bd76b189ea7b98601bbe5adf4e769aa33331', 'vout': '1'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'n1EPqYvggYxyaZSawyJVASGsikfrYAH12g', 'vout': '1', 'value': 335609600}], 'to_count': 2}, {'txid': 'f2ea71ad79f4dcd357196a0a5b1c10453c5abbaececa4d62be67ab97a2563f71', 'block': 466734, 'confirmations': 376503, 'timestamp': 1520865100, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'f330b15488bbfac244c042d96a62f5328dbbe6dc83a73008524e9c0d182e8934', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '6505bab3a5df574a888b552ff6858201ed529e1a846529c3d3fec7df027b5d7a', 'vout': '0'}}, {'address': 'miumhNkh9wsDQwXX5UrVoiqkRcZbJgfdqC', 'value': 41815400, 'spent': {'txid': 'ddaeed906259bae5945048f8e74574e4021f3aeefb68b580157374c9314e9955', 'vout': '0'}}], 'from_count': 3, 'fee': 10000000, 'to': [{'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '0', 'value': 10000000000}, {'address': 'mvyhG17sCo1fCxjMWV9oPsLbBEj3GuzkLr', 'vout': '1', 'value': 31815400}], 'to_count': 2}, {'txid': 'fe3f661f3cd46556c293decfa570f43973ccc1450005c9e8dbebcf3a3a3e46c3', 'block': 390061, 'confirmations': 453176, 'timestamp': 1518667819, 'type': 'received', 'from': [{'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': 'b878d827c9422a7b6806b74946c318ffa009b475016df409541fa02ad5a5c44a', 'vout': '0'}}, {'address': 'muKY6WAFLVwLFDwEkGevbTh5vk2ewYa9Qc', 'value': 5000000000, 'spent': {'txid': '961d3ed008ba8e03d266e38a6f3c61ee5ac16a9ae280b7b5d843c1046e79be4e', 'vout': '0'}}, {'address': 'mhLgSB3wziN3vELDwxDRt99w4mdmsJkmyh', 'value': 993527000, 'spent': {'txid': 'e4b5183e8bf4bb26c056618cb259f5b09beb5748f4d88384f79462a2d1410ce4', 'vout': '0'}}], 'from_count': 3, 'fee': 5220000, 'to': [{'address': 'mfXWXASrYBs1zeetKWWE1CM64W2o2goJXN', 'vout': '0', 'value': 988307000}, {'address': 'n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU', 'vout': '1', 'value': 10000000000}], 'to_count': 2}]}, 'url': 'http://exchange-web:8001/api/address/litecoin_testnet4/n24pZghJBAjjGT5V8i8bufRuhb2LEACuzU'}, 'balance': 40000000000}], 'address_count': 2}}
```

#### Breakdown

Breaking this down line by line.

The first few lines of the response indicate all is well with this API call:
```
{
  'status': 'OK', 
  'code': 200, 
  'debug': {}, 
```

Next we receive information about the user's wallet, starting with the unique ID:
```
  'data': {
    'wallet': {
      'id': '9f2816fd-1ee7-488f-bec8-90d3420ab6b7',
```

At this time the label is always set to 'default':
```
      'label': 'default',
```

The balance is the sum total of all addresses in the wallet.
```
      'balance': 801089282,
```

How many addresses we're currently aware of:
```
      'addresses': 20,
```

404 errors are addresses we've created but that don't yet exist on the blockchain (this is not an error):
```
      '404': [{'id': '38c3422e-2de8-4f3a-a498-46e6f59f082c', 'address': 'mxisCfQuGGK1gNdP7ZN9FFoPsepv5XFXgz'}, {'id': '65f4562e-d89c-4ecd-be21-b981d2727472', 'address': 'mtg3mEre62woxLJ6A22E55dx7EgqFe7iMr'}, {'id': '7f3fdb7b-1ba4-49db-823a-1e6c0dde1da9', 'address': 'mygjNfa6YBMQjShSNEx4UdMV2LxPX64ygi'}, {'id': 'f4138539-f714-48c3-beaf-2697a4f454b1', 'address': 'n3A3AboaUgvaMECi52jHTn2vkQmB8TWgWa'}, {'id': '92c8bd55-d795-474d-82c3-3a630ba09c32', 'address': 'mux6knE9B6AyyEuZLDkoqWS4Gquw1yFVpv'}, {'id': 'a694a862-9ce6-4241-88d0-6c755779e253', 'address': 'mtTP14XwE9t5F3QEueLH8fj7G3ijvj68Zm'}],
      '404_count': 6,
```

If error_count is non zero, something is wrong and the request should be made again. Look in debug for the problem.
```
      'error_count': 0,
```

Description can optionally be set by the front-end, and is informational only.
```
      'description': None,
```

The symbol for the currency contained in the wallet. In this case it's Litecoin Testnet:
```
      'currencycode': 'XLT'
    },
```

Next is a listing of all addresses, and full details about each address, starting with a unique id:
```
    'addresses': [
      {
        'id': 'e5ff1bbd-38fa-4273-829b-5952ea7acf18',
```

The label and description are optionally set by the frontend, and are only informational:
```
        'label': 'test address, index 0',
        'description': None,
```

The bitcoin address:
```
        'p2pkh': 'n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn',
```

The segwit compatible bitcoin address (not yet supported):
```
        'bech32': None,
```

Each address includes the results of a callback to the blockchain backend API -- it includes the same header:
```
        'addressapi': {
          'status': 'OK',
          'code': 200,
          'debug': [],
```

Each address includes a sanity check coin and symbol, the latter of which must match the wallet currencycode.
```
          'data': {
            'coin': 'litecoin_testnet4',
            'symbol': 'XLT',
```

The address details are provided by the blockchain API making an RPC request to the coin daemon to validate the address:
```
            'address': {
              'isvalid': True,
              'address': 'n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn',
              'scriptPubKey': '76a914dc8fb120ec5996d3d9a75921fe8e78525b1c667088ac',
              'isscript': False,
              'iswitness': False
            },
```

This is the unspent balance of this specific address, in satoshi:
```
            'balance': 100292681,
```

The total section includes the total received at and the total sent from this address, in satoshi.
```
            'total': {
              'received': 675449219,
              'sent': 575156538,
```

The vin and vout represent the total number of vin and vout involved in transactions related to this address.
```
              'vin': 16,
              'vout': 31,
```

The blockcoint is the current number of blocks on the coin's blockchain, not specific to this address.
```
              'blockcount': 863750
            },
```

Next comes a list of transactions. Each transaction has a unique ID:
```
            'transactions': [
              {
                'txid': 'a1d5ab1627b8ca9357ad079ba73c4198c653dea12aff9e9aecca30f33a666419',
```

Block indicates the height at which this transaction is found on the blockchain:
```
                'block': 844393,
```

How many blocks on the blockchain after the block containing this transaction. If <6 the transaction is pending.
```
                'confirmations': 19357,
```

The coin daemon supplied timestamp of the block the transaction is in:
```
                'timestamp': 1542349788,
```

Whether coins were received in this transaction, and how many (in satoshi):
```
                'received': True,
                'value_in': 100000000,
```

Whether coins were sent in this transaction, and how many (in satoshi):
```
                'sent': False,
                'value_out': 0,
```

How many vout were spent (becomining vin) during this transaction, and how many vout were created (typically 2,
the address we're sending funds to, and the change address):
```
                'from_count': 1,
                'to_count': 2,
```

How much was sent to the miner for including this transaction in the blockchain, in satoshi:
```
                'fee': 84000,
```

Addresses that sent coins, and how much (in satoshi):
```
                'from': [
                  {
                    'address': 'QPWY39kAbkzjRxa2hLLaLoViAxxpXzBxms',
                    'value': 149403500
                  }
                ],
```

Addresses that are being sent coins, how much (in satoshi), and whether the sent coins have been spent:
```
                'to': [
                  {
                    'address': 'QNdAU4vyaKhdMze4yuXg1Fv8TyYWV9y8x5',
                    'value': 49319500,
                    'is_spent': True
                  },
                  {
                    'address': 'n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn',
                    'value': 100000000,
                    'is_spent': False
                  }
                ]
```

The above continues for each transaction containing this address:
```
              },
                 ...
            ],
          },
```

The URL that was queried on the backend to get the address information.
(@TODO: move this into debug?)
```
        'url': 'http://exchange-web:8001/api/address/litecoin_testnet4/n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn'},
```

This repeats for each address in the wallet.
```
      },
    ],
    'address_count': 20
  }
}
``` 

#### Responses
 - 200 OK `OK` (a list of all addresses and associated details within the wallet)
 - 200 OK `wallet not found` (specified wallet does not exist):
 ``` {'status': 'wallet not found', 'code': 200, 'debug': {'user_id': 'b01d9ace-75fd-48f8-be30-c22bca9ce503', 'wallet_id': 'no-such-wallet', 'exception': '["\'no-such-wallet\' is not a valid UUID."]'}, 'data': {}} ```
 - 400 Bad Request `wallet_id is required` (failed to provide a wallet id)
 - 400 Bad Request `invalid data` (currencycode set to unsupported symbol)


### Send funds
Send funds from a specified wallet. It is the wallet's job to determine which addresses to
spend, and where to send the change (to a different address in our wallet). You must set
`wallet_id`, `output` and `passphrase` when POSTing to this endpoint.

The `output` parameter should be in the format {address: satoshi}, and can include any
number of destination addresses. The wallet will calculate any change and automatically
add it to your output.

You may also optionally set the `priority` parameter. If set, it must specify
`number_of_blocks` and/or `estimate_mode`. Number of blocks is used to indicate how quickly
you want the funds to show up in the blockchain, and can be a value from 0 (force the
minimum possible fee) to 1008 -- for example, if set to 4 (default) then the transaction
should show up in the blockchain within 4 blocks. The estimate mode can be one of:
CONSERVATIVE (default), or ECONOMICAL. (I expect the UI to hide all of this complexity,
and to just have simple choices like "urgent, high fee", "best-effort, low fee", etc.)

Example:
```
  $ curl -X POST 127.0.0.1:8000/api/wallet/send/ --data 'wallet_id=45ac8756-dae7-45d0-94ff-0637cd516f6d&output={'mnBc74s2Wg656UmgikCjPB3zRRXPBeoxQ4': 25000}&priority={'number_of_blocks': 6}' -H 'Authorization: JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VybmFtZSI6Im1lQGV4YW1wbGUuY29tIiwiZXhwIjoxNTM3OTk2NTk5LCJlbWFpbCI6Im1lQGV4YW1wbGUuY29tIiwib3JpZ19pYXQiOjE1Mzc5OTU2OTksIm90cF9kZXZpY2VfaWQiOm51bGx9.U8XPcB6B4dZMllFvhw3NdSXelk3lEUVzJlhIAg477ps'
  {'status': 'funds sent', 'code': 200, 'debug': {}, 'data': {'txid': '29c9e41b2412945c9b0b3b411cd7fbfac5543c4aea93915121f93066016bb51e', 'fee': 4297, 'output': {'mfnavjQjqKmn6hwiFyv8kwowPeagHyEack': 0.00064532, 'mqzMZqaNNPBs9Bj9XGSKxB1X23jySz2duV': 0.00049908, 'mmELS2QqnNe413qjtpft8MmgFfzfPEDvMR': 0.00065475}, 'spent': [{'txid': '2477d3bd80c4f9b3079163ab1e13b191ee6e32f8fa49e65223f8f3425886f158', 'vout': 0}], 'change_address': 'mmELS2QqnNe413qjtpft8MmgFfzfPEDvMR'}}
```

#### Responses
 - 200 OK `funds sent` (transaction created and posted to coin network)
 - 200 OK `no funds sent` (something went wrong when we tried to send funds)
 - 200 OK `insufficient funds` (trying to send more funds than are in your wallet):
``` {'status': 'insufficient funds', 'code': 200, 'debug': {'wallet_id': '93eb1822-acd0-4329-887e-220b0dde5810', 'currencycode': 'XLT', 'unspent': [{'txid': '2477d3bd80c4f9b3079163ab1e13b191ee6e32f8fa49e65223f8f3425886f158', 'vout': 0}, {'txid': '58c0cd492ef33dbf32f7062bbdfcfeac0c6a6bb1dd45a89e752170afa3866639', 'vout': 0}, {'txid': '682f4f3e95ab9258e344349ada36688b0c2cbb4cb411b027e8c7b7ca8d185d86', 'vout': 0}, {'txid': 'b7f9ecaee6237e49c49d3bf4556a9ddc104e822cbd08a6091f42b55f50010f5f', 'vout': 0}, {'txid': '325e1b910d8995356ec2c0c3ddfe65f08a7d419c50be4a90f519b0d65b376418', 'vout': 0}], 'total': 200191712, 'addresses': ['mhewyCgGDFKoEeivE6x46ibujQJMEMxre7', 'mnWJ9vzDuxyh31savkLGBzUA6rDxaCVZVu', 'mtg3mEre62woxLJ6A22E55dx7EgqFe7iMr', 'mygjNfa6YBMQjShSNEx4UdMV2LxPX64ygi', 'mzMXDbE6JRx7EagiqTaL2w6sooMsEamdAm', 'mtKEx5hzjibPZyRBmzxd4FACEfZXZTk3YT', 'mpXDuHniRKtPgMWRb7j4AXa8Fzk2DG3mGB', 'n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn', 'mfnavjQjqKmn6hwiFyv8kwowPeagHyEack', 'mxisCfQuGGK1gNdP7ZN9FFoPsepv5XFXgz', 'n3A3AboaUgvaMECi52jHTn2vkQmB8TWgWa', 'mpAguj9No3X7NeDfjejTw9CTQkBZSY5w6v', 'mqvUwMie7QbetXujEJDTccbxAXES7PYPok', 'n3gYbfQdb7BLJGxGwY4z483DHCWmBw7GRA', 'mvDTdVg2J73CYDDnhLL8x9eMHXjXpRHBrT', 'mtTP14XwE9t5F3QEueLH8fj7G3ijvj68Zm', 'n1kmRdFZPMgyHeYJMsr42hUZaDsvDt9FMK', 'mux6knE9B6AyyEuZLDkoqWS4Gquw1yFVpv', 'mqzMZqaNNPBs9Bj9XGSKxB1X23jySz2duV', 'mz96sfnpYW1GFG7yzaxMjP4KqihAVXsogB'], 'addresses_with_unspent': ['n1dB69Ptu1HMt1tRqiueyJ1tsaj59qSjLn', 'n3gYbfQdb7BLJGxGwY4z483DHCWmBw7GRA', 'mqzMZqaNNPBs9Bj9XGSKxB1X23jySz2duV']}, 'data': {}} ```
 - 400 Bad Request `invalid address` (specified invalid address in output)
 - 400 Bad Request `invalid output` (bad data provided in output):
``` {'status': 'invalid output', 'code': 400, 'debug': {'exception': "'output'", 'request': {'wallet_id': 'c362f618-6b3a-4eb6-ae4a-bf0b04c528ab', 'passphrase': 'thisISs3cured00d!', '~': {'mfnavjQjqKmn6hwiFyv8kwowPeagHyEack': 500000000000}, 'priority': {'number_of_blocks': 556}}}, 'data': {}} ```
 - 400 Bad Request `invalid data` (currencycode set to unsupported symbol)
 - 400 Bad Request `invalid passphrase`:
``` {'status': 'invalid passphrase', 'code': 400, 'debug': {'passphrase': 'thisISs3cured00d!', 'request': {'wallet_id': '93eb1822-acd0-4329-887e-220b0dde5810', 'passphrase': 'thisISwrong', 'output': {'mhewyCgGDFKoEeivE6x46ibujQJMEMxre7': 500000000000}, 'priority': {'number_of_blocks': 10}}}, 'data': {}} ```
 - 400 Bad Request `invalid number_of_blocks, must be a value from 0 to 1008`
 - 400 Bad Request `invalid estimate_mode, must be one of: CONSERVATIVE, ECONOMICAL`
 - 500 Internal Server Error `fee error` (attempt to calculate fee failed, smart fee issue)
 - 500 Internal Server Error `invalid transaction` (attempt to sign raw transaction failed)
``` {'status': 'invalid private key', 'code': 500, 'debug': {'request': {'wallet_id': '09981f02-8aa4-4ade-8371-fad77540c5c3', 'passphrase': 'thisISs3cured00d!', 'output': {'mfnavjQjqKmn6hwiFyv8kwowPeagHyEack': 128948, 'mux6knE9B6AyyEuZLDkoqWS4Gquw1yFVpv': 172586, 'mqvUwMie7QbetXujEJDTccbxAXES7PYPok': 22547, 'n3A3AboaUgvaMECi52jHTn2vkQmB8TWgWa': 92217, 'mpXDuHniRKtPgMWRb7j4AXa8Fzk2DG3mGB': 197468, 'mtKEx5hzjibPZyRBmzxd4FACEfZXZTk3YT': 182744, 'mz96sfnpYW1GFG7yzaxMjP4KqihAVXsogB': 46364, 'mygjNfa6YBMQjShSNEx4UdMV2LxPX64ygi': 231672}, 'priority': {'number_of_blocks': 194}}, 'errors': [{'txid': '325e1b910d8995356ec2c0c3ddfe65f08a7d419c50be4a90f519b0d65b376418', 'vout': 0, 'witness': [], 'scriptSig': '', 'sequence': 4294967295, 'error': 'Input not found or already spent'}], 'fee': 16230, 'output': {'mfnavjQjqKmn6hwiFyv8kwowPeagHyEack': 0.00128948, 'mux6knE9B6AyyEuZLDkoqWS4Gquw1yFVpv': 0.00172586, 'mqvUwMie7QbetXujEJDTccbxAXES7PYPok': 0.00022547, 'n3A3AboaUgvaMECi52jHTn2vkQmB8TWgWa': 0.00092217, 'mpXDuHniRKtPgMWRb7j4AXa8Fzk2DG3mGB': 0.00197468, 'mtKEx5hzjibPZyRBmzxd4FACEfZXZTk3YT': 0.00182744, 'mz96sfnpYW1GFG7yzaxMjP4KqihAVXsogB': 0.00046364, 'mygjNfa6YBMQjShSNEx4UdMV2LxPX64ygi': 0.00231672, 'mmELS2QqnNe413qjtpft8MmgFfzfPEDvMR': 1.99100936}, 'spent': [{'txid': '2477d3bd80c4f9b3079163ab1e13b191ee6e32f8fa49e65223f8f3425886f158', 'vout': 0}, {'txid': '58c0cd492ef33dbf32f7062bbdfcfeac0c6a6bb1dd45a89e752170afa3866639', 'vout': 0}, {'txid': '682f4f3e95ab9258e344349ada36688b0c2cbb4cb411b027e8c7b7ca8d185d86', 'vout': 0}, {'txid': 'b7f9ecaee6237e49c49d3bf4556a9ddc104e822cbd08a6091f42b55f50010f5f', 'vout': 0}, {'txid': '325e1b910d8995356ec2c0c3ddfe65f08a7d419c50be4a90f519b0d65b376418', 'vout': 0}]}, 'data': {}} ```
 - 500 Internal Server Error `signing error` (attempt to sign raw transaction caused exception)


## Example

This example assumes you're using the backends running in containers on dev.net, and that
you have set up an ssh tunnel as follows:

    ssh -L 8000:localhost:8000 dev.net

1. A user signs up for the service:
    ```
    $ curl -X POST http://localhost:8000/api/user/create/ --data 'email=foo@bar.net&password=Qwerty12!'
    {"email":"foo@bar.net","id":"0aeee7ad-d832-4978-bd0f-bac1bfb5e836"} 
    ```

1. The user logs into their new account:
    ```
    $ curl -X POST http://localhost:8000/api/user/login/ --data 'email=foo@bar.net&password=Qwerty12!'
    {"token":TOKEN}
    ```
    (We replace the actual token with the work TOKEN in capital letters to make this example easier to read.)

1. The user supplies a passphrase, and an HD wallet seed is created:
    ```
    $ curl -X POST http://localhost:8000/api/wallet/create-seed/ --data 'passphrase=abc123DEF' -H 'Authorization: JWT TOKEN'
    {"status":"seed already created","code":200,"debug":{"mnemonic":"holiday direct again wage any bleak dawn document lucky lizard become adjust rug metal patch coin warm future exhibit giggle treat stadium cruel soup","salt":"nyLIvi4XMkoUC_0_Gex9MiJsXMH5iI8xzMZ1qQPZk97QmZIiR-UPjw-XxjW2Xng3","passphrase":"abc123DEF"},"data":{}}
    ```

1. With the same passphrase, the user creates a Bitcoin wallet:
    ```
    $ curl -X POST http://localhost:8000/api/wallet/create/ --data 'label=default&currencycode=BTC&passphrase=abc123DEF' -H 'Authorization: JWT TOKEN'
    {"status":"wallet already exists","code":200,"debug":{"request":{"label":"default","currencycode":"BTC","passphrase":"abc123DEF"}},"data":{"id":"3645533f-43aa-4fb7-9da8-6f680e855663","label":"default","description":null,"coin":"bitcoin","symbol":"BTC"}}
    ```

1. The user creates a Bitcoin address within the wallet (no passphrase required):
    ```
    $ curl -X POST 127.0.0.1:8000/api/address/create/ --data 'wallet_id=3645533f-43aa-4fb7-9da8-6f680e855663&label=test' -H 'Authorization: JWT TOKEN'
    {"status":"address already exists","code":200,"debug":{},"data":{"id":"3418920b-734f-416a-b158-8b7c923bf6fd","label":"test","description":null,"p2pkh":"19y14GkqWn3ocXQxPPB1ezywsCjgZrUma5","index":0,"is_change":false,"wallet_id":"3645533f-43aa-4fb7-9da8-6f680e855663","coin":"bitcoin","symbol":"BTC"}}
    ```

1. With the same passphrase, the user creates a Litecoin testnet wallet:
    ```
    $ curl -X POST http://localhost:8000/api/wallet/create/ --data 'label=default&currencycode=XLT&passphrase=abc123DEF' -H 'Authorization: JWT TOKEN'
    {"status":"wallet already exists","code":200,"debug":{"request":{"label":"default","currencycode":"XLT","passphrase":"abc123DEF"}},"data":{"id":"45ac8756-dae7-45d0-94ff-0637cd516f6d","label":"default","description":null,"coin":"litecoin_testnet4","symbol":"XLT"}}
    ```

1. The user creates a Litecoin testnet address within the wallet (no passphrase required):
    ```
    $ curl -X POST 127.0.0.1:8000/api/address/create/ --data 'wallet_id=45ac8756-dae7-45d0-94ff-0637cd516f6d&label=test' -H 'Authorization: JWT TOKEN'
    {"status":"address already exists","code":200,"debug":{},"data":{"id":"cb06e94f-879f-480b-b509-c661c67a67a0","label":"test","description":null,"p2pkh":"mgMWLGtorCfehKpQEGfo6tC7EFkDCak3hj","index":2,"is_change":false,"wallet_id":"45ac8756-dae7-45d0-94ff-0637cd516f6d","coin":"litecoin_testnet4","symbol":"XLT"}}
    ```

1. We send some money to the wallet from another address:
    https://chain.so/tx/LTCTEST/10555832dfef9fe6c3762d560adf79f4412ba9fa73ca684c85c4a8f534feb91d

1. Wait until the transaction lands in a block.

1. We list all our wallets:
    ```
    $ curl -X GET http://localhost:8000/api/wallet/list/ -H 'Authorization: JWT TOKEN'
    {"status":"3 wallets found","code":200,"debug":{},"data":[{"id":"3645533f-43aa-4fb7-9da8-6f680e855663","label":"default","description":null,"currencycode":"BTC","balance":0,"address_count":1,"404_count":0,"error":[{"url":"http://exchange-web:8001/api/address/bitcoin/19y14GkqWn3ocXQxPPB1ezywsCjgZrUma5/unspent","code":400}],"error_count":1},{"id":"70ddaf47-edd2-4463-badb-9fffd637c4df","label":"default","description":null,"currencycode":"LTC","balance":0,"address_count":0,"404_count":0,"error":[],"error_count":0},{"id":"45ac8756-dae7-45d0-94ff-0637cd516f6d","label":"default","description":null,"currencycode":"XLT","balance":100002000,"address_count":6,"404_count":1,"error":[],"error_count":0}]}
    ```
    
1. We list all addresses in our Litecoin testnet wallet:
    ```
    $ curl -X POST http://localhost:8000/api/address/list/ --data 'wallet_id=45ac8756-dae7-45d0-94ff-0637cd516f6d' -H 'Authorization: JWT TOKEN'
    {"status":"OK","code":200,"debug":{},"data":{"wallet":{"id":"45ac8756-dae7-45d0-94ff-0637cd516f6d","label":"default","balance":749989913,"addresses":6,"404":[{"id":"cb06e94f-879f-480b-b509-c661c67a67a0","address":"mgMWLGtorCfehKpQEGfo6tC7EFkDCak3hj"}],"404_count":1,"error_count":0,"description":null,"currencycode":"XLT"},"addresses":[{"id":"bbe16b02-d00d-4d18-8dc9-7ef01738b6fb","label":"test","description":null,"p2pkh":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","bech32":null,"addressapi":{"status":"OK","code":200,"debug":[],"data":{"coin":"litecoin_testnet4","symbol":"XLT","address":{"isvalid":true,"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","scriptPubKey":"76a9146df5389b177845017f9c32bb26dea3d519827bbf88ac","isscript":false,"iswitness":false},"balance":100004000,"total":{"received":350004000,"sent":250000000,"vin":1,"vout":4,"blockcount":843917},"transactions":[{"txid":"10555832dfef9fe6c3762d560adf79f4412ba9fa73ca684c85c4a8f534feb91d","block":811506,"confirmations":32411,"timestamp":1540231384,"type":"received","from":[{"address":"n1tVFWgZfdfTrjQKG4ARwSy3pEc7KiTtht","value":199742442,"spent":{"txid":"4baa55236e1d04715116047797b92da73961c53c6c06f66416b4b1363c7e3a76","vout":"1"}},{"address":"n1tVFWgZfdfTrjQKG4ARwSy3pEc7KiTtht","value":1000000000,"spent":{"txid":"f44bf877d8fd637174c79c8b0192be98671b0bb83989621f02505faad34ec89e","vout":"0"}}],"from_count":2,"fee":2861,"to":[{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","vout":"0","value":250000000},{"address":"n1tVFWgZfdfTrjQKG4ARwSy3pEc7KiTtht","vout":"1","value":949739581}],"to_count":2},{"txid":"2b2da5117dc9297ba14b578cfe675becb81167d3cedfd9c07c676042526aec24","block":812963,"confirmations":30954,"timestamp":1540391744,"type":"received","from":[{"address":"mmKmMDYuXcfeJKkit8CeUzC1csetkxyb74","value":400000000,"spent":{"txid":"4e411ff9004c5b73731694a916d328ab666f8f9a7e1f34bf4a61e97706c6f29c","vout":"0"}}],"from_count":1,"fee":2529,"to":[{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","vout":"0","value":2000},{"address":"mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W","vout":"1","value":399995471}],"to_count":2},{"txid":"33ad4ea8bd158ba4e545c2bfb4f3288f1b4900ecca269b90db9ddfbdd2f23f38","block":813024,"confirmations":30893,"timestamp":1540413584,"type":"received","from":[{"address":"mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W","value":399995471,"spent":{"txid":"2b2da5117dc9297ba14b578cfe675becb81167d3cedfd9c07c676042526aec24","vout":"1"}}],"from_count":1,"fee":2529,"to":[{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","vout":"0","value":2000},{"address":"moKgE5ZyxrzyqwM8xRqx9W1Ru6A81NiChe","vout":"1","value":399990942}],"to_count":2},{"txid":"94cfea1c7efb9ca79d41a8ad97baecc2531d81a7af2afa17d6a5373da2605624","block":812233,"confirmations":31684,"timestamp":1540358681,"type":"received","from":[{"address":"QYc5tvqcqj9oTWDw4ZsoQVQz1JgkFTy2Jy","value":238400652,"spent":{"txid":"af0f502a177fe03852ad806013b3064fb9e2148e6601feb9b9f3e21b631b2c79","vout":"0"}}],"from_count":1,"fee":168000,"to":[{"address":"QaQCMSxwi5HeTtatDLpKTc6J3gN5vG4gu7","vout":"0","value":138232652},{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","vout":"1","value":100000000}],"to_count":2}]},"url":"http://exchange-web:8001/api/address/litecoin_testnet4/mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP"},"balance":100004000},{"id":"356462c8-eb2c-4a8d-a6c8-e8fc030042ef","label":"test","description":null,"p2pkh":"mmKmMDYuXcfeJKkit8CeUzC1csetkxyb74","bech32":null,"addressapi":{"status":"OK","code":200,"debug":[],"data":{"coin":"litecoin_testnet4","symbol":"XLT","address":{"isvalid":true,"address":"mmKmMDYuXcfeJKkit8CeUzC1csetkxyb74","scriptPubKey":"76a9143fb30ad4e56f8e70872c32a1d2cc8e4baa6dd9e488ac","isscript":false,"iswitness":false},"balance":0,"total":{"received":400000000,"sent":400000000,"vin":1,"vout":1,"blockcount":843917},"transactions":[{"txid":"4e411ff9004c5b73731694a916d328ab666f8f9a7e1f34bf4a61e97706c6f29c","block":812199,"confirmations":31718,"timestamp":1540358100,"type":"received","from":[{"address":"QPZ7qwjGaemSmQTJmHabxSESMnYkxSroxJ","value":643099526,"spent":{"txid":"501575e79bc2f32ec6b63033564b8b89ddb2141d2f662ff84d37d18deb69d790","vout":"1"}}],"from_count":1,"fee":168000,"to":[{"address":"mmKmMDYuXcfeJKkit8CeUzC1csetkxyb74","vout":"0","value":400000000},{"address":"QdWoSjaiiQzjdHCZzUyACSSbHjRHRTPHSK","vout":"1","value":242931526}],"to_count":2}]},"url":"http://exchange-web:8001/api/address/litecoin_testnet4/mmKmMDYuXcfeJKkit8CeUzC1csetkxyb74"},"balance":0},{"id":"cb06e94f-879f-480b-b509-c661c67a67a0","label":"test","description":null,"p2pkh":"mgMWLGtorCfehKpQEGfo6tC7EFkDCak3hj","bech32":null,"addressapi":{"status":"ERROR","code":404,"error":"not found","debug":[],"data":{"coin":"litecoin_testnet4","symbol":"XLT","address":{"isvalid":true,"address":"mgMWLGtorCfehKpQEGfo6tC7EFkDCak3hj","scriptPubKey":"76a914092eb5dbb17c274353efc2b118ab11658513d73488ac","isscript":false,"iswitness":false}},"url":"http://exchange-web:8001/api/address/litecoin_testnet4/mgMWLGtorCfehKpQEGfo6tC7EFkDCak3hj"}},{"id":"4d257ca2-1684-4d4a-96c3-b1dbfc62d382","label":"change","description":null,"p2pkh":"mxbDTSkvMtmWE9xfpc8GwUyaPbVXrJ4AK8","bech32":null,"addressapi":{"status":"OK","code":200,"debug":[],"data":{"coin":"litecoin_testnet4","symbol":"XLT","address":{"isvalid":true,"address":"mxbDTSkvMtmWE9xfpc8GwUyaPbVXrJ4AK8","scriptPubKey":"76a914bb48756d3b4ab3d383713af776d16abef9243b3d88ac","isscript":false,"iswitness":false},"balance":249994971,"total":{"received":249994971,"sent":0,"vin":0,"vout":1,"blockcount":843917},"transactions":[{"txid":"dbe49a32b458956d3cf32e1ffd4978d508ff6ed565eba7458493a0bb616f0691","block":811745,"confirmations":32172,"timestamp":1540315351,"type":"received","from":[{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","value":250000000,"spent":{"txid":"10555832dfef9fe6c3762d560adf79f4412ba9fa73ca684c85c4a8f534feb91d","vout":"0"}}],"from_count":1,"fee":2529,"to":[{"address":"n1tVFWgZfdfTrjQKG4ARwSy3pEc7KiTtht","vout":"0","value":2500},{"address":"mxbDTSkvMtmWE9xfpc8GwUyaPbVXrJ4AK8","vout":"1","value":249994971}],"to_count":2}]},"url":"http://exchange-web:8001/api/address/litecoin_testnet4/mxbDTSkvMtmWE9xfpc8GwUyaPbVXrJ4AK8"},"balance":249994971},{"id":"4483d250-3945-4e78-ba7a-2c796ed1c79b","label":"change","description":null,"p2pkh":"mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W","bech32":null,"addressapi":{"status":"OK","code":200,"debug":[],"data":{"coin":"litecoin_testnet4","symbol":"XLT","address":{"isvalid":true,"address":"mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W","scriptPubKey":"76a91442e914a7cd60801e5b239978e11b12bb231d314c88ac","isscript":false,"iswitness":false},"balance":0,"total":{"received":399995471,"sent":399995471,"vin":1,"vout":1,"blockcount":843917},"transactions":[{"txid":"2b2da5117dc9297ba14b578cfe675becb81167d3cedfd9c07c676042526aec24","block":812963,"confirmations":30954,"timestamp":1540391744,"type":"received","from":[{"address":"mmKmMDYuXcfeJKkit8CeUzC1csetkxyb74","value":400000000,"spent":{"txid":"4e411ff9004c5b73731694a916d328ab666f8f9a7e1f34bf4a61e97706c6f29c","vout":"0"}}],"from_count":1,"fee":2529,"to":[{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","vout":"0","value":2000},{"address":"mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W","vout":"1","value":399995471}],"to_count":2}]},"url":"http://exchange-web:8001/api/address/litecoin_testnet4/mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W"},"balance":0},{"id":"5978084e-826c-4403-8a84-96516782ac19","label":"change","description":null,"p2pkh":"moKgE5ZyxrzyqwM8xRqx9W1Ru6A81NiChe","bech32":null,"addressapi":{"status":"OK","code":200,"debug":[],"data":{"coin":"litecoin_testnet4","symbol":"XLT","address":{"isvalid":true,"address":"moKgE5ZyxrzyqwM8xRqx9W1Ru6A81NiChe","scriptPubKey":"76a914559f0471cf0aaae131fd4769c1ef39a17ef4018c88ac","isscript":false,"iswitness":false},"balance":399990942,"total":{"received":399990942,"sent":0,"vin":0,"vout":1,"blockcount":843917},"transactions":[{"txid":"33ad4ea8bd158ba4e545c2bfb4f3288f1b4900ecca269b90db9ddfbdd2f23f38","block":813024,"confirmations":30893,"timestamp":1540413584,"type":"received","from":[{"address":"mmck7SkT4ZuyGHrS7uQrZXnQDFrm7EeD9W","value":399995471,"spent":{"txid":"2b2da5117dc9297ba14b578cfe675becb81167d3cedfd9c07c676042526aec24","vout":"1"}}],"from_count":1,"fee":2529,"to":[{"address":"mqYMiE2YPugoDCH3zJD7X4iVKZEDwZbfYP","vout":"0","value":2000},{"address":"moKgE5ZyxrzyqwM8xRqx9W1Ru6A81NiChe","vout":"1","value":399990942}],"to_count":2}]},"url":"http://exchange-web:8001/api/address/litecoin_testnet4/moKgE5ZyxrzyqwM8xRqx9W1Ru6A81NiChe"},"balance":399990942}],"address_count":6}}
    ```
    
1. We send money from our wallet to another litecoin address:
    ```
    $ curl -X POST http://localhost:8000/api/wallet/send/ --data '{"wallet_id":"45ac8756-dae7-45d0-94ff-0637cd516f6d","passphrase":"abc123DEF","output":{"n1tVFWgZfdfTrjQKG4ARwSy3pEc7KiTtht":2500}}' -H 'Content-type: application/json' -H 'Authorization: JWT TOKEN'
    {"status":"funds sent","code":200,"debug":{},"data":{"txid":"385dd7ee76a7775da17f969822c280ee4ea9dbf20042eaeaf475f41e5b2a9e29","fee":2861,"output":{"n1tVFWgZfdfTrjQKG4ARwSy3pEc7KiTtht":2.5e-05,"mfeHt4WkzQhhV5eNUA44EaH1qHM6FtXopG":0.99996639},"spent":[{"txid":"2b2da5117dc9297ba14b578cfe675becb81167d3cedfd9c07c676042526aec24","vout":0},{"txid":"94cfea1c7efb9ca79d41a8ad97baecc2531d81a7af2afa17d6a5373da2605624","vout":1}],"change_address":"mfeHt4WkzQhhV5eNUA44EaH1qHM6FtXopG"}}
    ```
    This create a real transaction on the testnet4 blockchain, visible here:
      https://chain.so/tx/LTCTEST/385dd7ee76a7775da17f969822c280ee4ea9dbf20042eaeaf475f41e5b2a9e29
      
    Notes:
    * the fee was automatically calculated (and accepted by the network)
    * the output array shows where the funds were sent, including an auto-generated change address (part of our HD wallet)
    * we had to get funds from two unspent vouts to fulfill this transaction

## Configuration

Configuration lives in settings.py. Currently it assumes it's in a container based on the included docker
configuration.

### Enabling coins

Coins are defined in the `COINS` dictionary. The keys are a currency code as defined by pycoin. The values are
as follows:
 - name: the name of the currency as expected by the blockchain api
 - server: the host and port of the coin daemon
 - rpcauth: the username and password required for RCP connections to the daemon
 - bip44_index: the integer index assigned to this currency in BIP044
 - account_index: live coins are 0, testnet coins get the live coin bip44_index

Pycoin currency codes (we currently use the 0.80 release):
* https://github.com/richardkiss/pycoin/blob/0.80/pycoin/networks/all.py
* https://github.com/richardkiss/pycoin/blob/0.80/pycoin/networks/legacy_networks.py

For example:
```
  COINS = {
    'BTC': {
        'name': 'bitcoin',
        'server': 'bitcoin:8332',
        'rpcauth': 'bitcoin:bitcoin',
        'bip44_index': 0,
        'account_index': 0,
    },
    'XTN': {
        'name': 'bitcoin_testnet3',
        'server': 'bitcoin-testnet3:18332',
        'rpcauth': 'bitcoin:bitcoin',
        'bip44_index': 1,
        'account_index': 1,
    },
    ...
}
```

The location of the address API is defined in the `ADDRESSAPI` dictionary. Currently it is assumed that all coins
live on the same server.

For example, the default configuration assumes the Address API lives in a locally hosted container:
```
  ADDRESSAPI = {
    'protocol': 'http',
    'domain': 'exchange-web',
    'port': 8001,
}
```

## Docker

The docker configuration included in this repo is based on the follow blogs:

- https://blog.jetbrains.com/pycharm/2017/08/using-docker-compose-on-windows-in-pycharm/
- https://blog.jetbrains.com/pycharm/2017/03/docker-compose-getting-flask-up-and-running/

The new blog is specific to Django, but the older blog provides a lot of missing detail.

### Setup

1. Install Docker Composer and dependencies: https://docs.docker.com/compose/install/
1. Clone this repo: https://github.com/ ..
1. In PyCharm **Preferences >> Build, Execution, Deployment >> Docker** enable docker
1. In **Preferences >> Project: .. >> Project Interpreter** click the Gear to the right of Project Interpreter and select *Add*.
1. Select **Docker Compose**, and add `docker-compose.dev.yml` (in addition to `docker-compose.yml` which is there by default), and be sure **Web** is the selected Service (it seems to default to **db** which won't work).
1. Select **Run >> Edit Configurations**, click **+**, and select **Docker >> Docker Compose**
1. Name it **Rebuild Images**,  and be sure both `docker-compose.dev.yml` and `docker-compose.yml` are selected.

You should now be able to click the green triangle in the PyCharm menubard, or click **Rebuild Images >> Rebuild Images**

To help avoid port-collisions, I've configured docker to pick its own port for the database. The web instance is locked to port 8000 however. You can access the API at http://localhost:8000

### Helpful Commands

List composer containers and their ports:

  `docker-compose ps`

Connect to the web container and create the database schema:

  `docker exec -it web_1 bash`
  
  `python ./manage.py migrate`
  
Connect to the db container and list the database tables:

  `docker exec -it db_1 bash`
  
  `psql -Upostgres`
  
  `\d`
