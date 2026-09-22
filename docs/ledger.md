# Ledger

The optional `ledger` package provides the `OrderRecord` model and the
append-only JSONL `OrderLedger`. It stores application metadata together with
the `OrderResult` returned by the CLOB wrapper.

The ledger does not submit orders. The application calls the CLOB client,
creates an `OrderRecord` from the result, and registers the record:

```python
import time
from decimal import Decimal

from polymarket_sdk_wrapper.clob import PolymarketClient
from polymarket_sdk_wrapper.ledger import OrderLedger, OrderRecord

client = ...  # an initialized PolymarketClient
ledger = OrderLedger("data/orders.jsonl")

result = await client.place_order(
    token=token_id,
    amount=Decimal("10"),
    max_price=Decimal("0.55"),
)
record = OrderRecord(
    created_at=int(time.time()),
    token=token_id,
    amount=Decimal("10"),
    order_result=result,
    max_price=Decimal("0.55"),
    outcome="Yes",
    side="BUY",
    order_type="FAK",
)
registered = await ledger.register_order(record)
```

## `OrderRecord`

`OrderRecord` contains the required execution context:

- `created_at`: Unix timestamp in seconds.
- `token`: CLOB token identifier.
- `amount`: requested purchase amount as a `Decimal`.
- `order_result`: the complete `OrderResult`, including fills.

The following metadata fields are optional and are stored as `null` when they
are not available:

- `max_price`: maximum requested price.
- `outcome`: `Yes` or `No`.
- `side`: `BUY` or `SELL`.
- `order_type`: `FAK` or `GTC`.

`to_dict()` converts Decimal values to strings and emits keys in this order:
`created_at`, `outcome`, `side`, `order_type`, `token`, `amount`, `max_price`,
`order_result`. `from_dict()` reconstructs the Decimal and CLOB model values.

## `OrderLedger`

`OrderLedger(path)` creates the parent directory when needed and loads every
non-empty JSONL line into memory. Each registered record is appended as one JSON
object per line.

`register_order(record)` behaves as follows:

- Raises `ValueError` when the record has no order ID or its result is
  `NO_FILL`.
- Returns `False` when the order ID is already present.
- Appends and indexes the record, then returns `True` for a new filled order.

`orders_for_token(token)` returns the loaded records for one token.
`spent_usd(token)` sums `total_cost` from confirmed fills only; it does not sum
the requested `amount`.

The ledger uses an `asyncio.Lock` to serialize coroutines sharing the same
instance. It is intended for one process and does not provide cross-process
file locking or a transactional database. For multiple workers or a database
backend, keep the same record semantics and provide application-specific
coordination.

## Smoke test

The ledger smoke uses a simulated CLOB result, verifies both
`orders_for_token()` and `spent_usd()`, and does not contact the network or
require credentials. It writes its local result to `smoke/ledger/orders.jsonl`,
which is ignored by Git:

```bash
uv run smoke/ledger/smoke.py
```

The real CLOB smoke remains separate and can submit an order with real funds;
see [clob.md](clob.md).
