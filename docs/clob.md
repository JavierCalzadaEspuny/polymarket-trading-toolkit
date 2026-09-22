# CLOB

`PolymarketClient` is a small wrapper around `polymarket-client` for
authenticated `BUY` orders with `FAK` (Fill And Kill) order type.

The client can be reused while the process is running. Authentication and
approvals are prepared once when the instance is created, and the same
instance can then submit multiple orders.

## Creating and reusing the client

```python
from decimal import Decimal

from polymarket_sdk_wrapper.clob import PolymarketClient


client = await PolymarketClient.create(
    private_key=private_key,
    wallet_address=wallet_address,
    relayer_api_key=relayer_api_key,
    relayer_api_key_address=relayer_api_key_address,
)

try:
    first = await client.place_order(
        token=yes_token_id,
        amount=Decimal("10"),
        max_price=Decimal("0.55"),
    )
    second = await client.place_order(
        token=no_token_id,
        amount=Decimal("10"),
        max_price=Decimal("0.50"),
    )
finally:
    await client.close()
```

The class does not implement `async with`; call `close()` explicitly. The
authenticated client lives in memory. If the process exits, create another
instance.

## Order parameters

`place_order(...)` currently accepts:

- `token`: the CLOB outcome identifier (`Yes` or `No`).
- `amount`: the purchase budget in pUSD.
- `max_price`: the maximum price per share. `None` removes this protection and
  is not recommended for a smoke test.

After an order is accepted, the wrapper waits up to 10 seconds for the CLOB
to publish its trade ids. This limit is built into the class and cannot be
configured per call.

The wrapper also passes `max_spend=amount` to the SDK. This keeps total spend
within the specified budget, including any costs estimated by the SDK. The
amount must be compatible with the market's minimum share size. Gamma's price
may be stale; before executing, query the CLOB order book immediately before
placing the order.

FAK attempts to execute immediately against available liquidity. The unfilled
portion is canceled, so the order never rests on the book. If the CLOB rejects
the operation because there is no match, the wrapper returns an `OrderResult`
with status `NO_FILL`.

After an order is accepted, the wrapper polls its status every 250 ms and waits
up to 10 seconds for its trade ids to appear. If the timeout is reached, it
raises `polymarket.errors.TimeoutError`.

## Result and statuses

`OrderResult.fills` contains `Fill` objects with the fields `trade_id`, `size`,
`price`, `status`, and `transaction_hash`. For example:

```python
fill = result.fills[0]
print(fill.price)
print(fill.size)
```

`OrderResult.to_dict()` always returns the same structure:

```json
{
  "order_id": "0x...",
  "status": "FULL_FILL",
  "fills": [
    {
      "trade_id": "...",
      "size": "61.836735",
      "price": "0.049",
      "status": "CONFIRMED",
      "transaction_hash": "0x..."
    }
  ]
}
```

Possible statuses:

- `FULL_FILL`: all requested shares were executed.
- `PARTIAL_FILL`: only part of the requested amount was executed.
- `NO_FILL`: no shares were executed because there was no counterparty within
  `max_price`.

Authentication, transport, validation, balance, timeout, and settlement errors
are propagated as exceptions from the SDK. The wrapper only converts known FAK
rejections caused by a lack of matching liquidity into `NO_FILL`.

## Fills and price levels

Each fill contains `trade_id`, `size`, `price`, `status`, and
`transaction_hash`.

`FULL_FILL` describes the total executed quantity; it does not imply that all
price levels used the same price. The fill `price` is the aggregate value
returned by the CLOB. This wrapper does not currently expose the
`maker_orders` breakdown; query the SDK's original trade model if that detail
is required.

## Scope

The wrapper does not persist orders or positions, maintain a continuous
tracker, use WebSocket, or index Polygon. Applications can store
`OrderResult` objects and their fills as needed.

## Smoke test

`smoke/clob/smoke.py` sends a real order and can spend funds. It is not an
offline test.

```bash
cp smoke/clob/.env.example smoke/clob/.env
# Edit the token, amount, maximum price, and credentials.
uv run --env-file smoke/clob/.env python smoke/clob/smoke.py
```

The `.env` file is ignored by Git. Never include private keys or relayer keys
in the repository.
