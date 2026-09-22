# Polymarket SDK Wrapper

Small, independent wrappers around the official `polymarket-client` SDK.

Current package version: `0.1.0`.

## Gamma quick start

Install the project with `uv`, then load an event snapshot:

```python
from polymarket_sdk_wrapper.gamma import GammaEvent, token
from datetime import datetime

link = "https://polymarket.com/event/example"
snapshot = GammaEvent.load(link)
reference_time = datetime.now().astimezone()
market = snapshot.nearest_market(reference_time=reference_time)

yes_token = token(market, "Yes")
no_token = token(market, "No")
```

Gamma uses the official SDK and keeps the parsed event snapshot in memory.
`nearest_market(...)` compares the absolute `endDate` timestamps and accepts a
timezone-aware `datetime`, ISO string, or Unix timestamp. The caller supplies
the instant used for selection; Gamma does not read the system clock.
`token(...)` receives the selected market and performs an in-memory lookup. See
[docs/gamma.md](docs/gamma.md) for the exact rules and the async API.

## CLOB

The CLOB wrapper provides a reusable authenticated client for `BUY` orders with
`FAK` (Fill And Kill). The client can send multiple orders during the same
process:

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
    result = await client.place_order(
        token=token_id,
        amount=Decimal("10"),
        max_price=Decimal("0.55"),
    )
finally:
    await client.close()
```

`place_order(...)` always returns an `OrderResult` with one of these statuses:

- `FULL_FILL`: the requested amount was fully executed.
- `PARTIAL_FILL`: only part of the requested amount was executed.
- `NO_FILL`: no shares were bought because there was no matching liquidity
  within `max_price`.

The result includes typed `Fill` objects with the executed fills and their
prices. In Python, fill sizes and prices use `Decimal`; `OrderResult.to_dict()`
converts them to strings for JSON serialization. Authentication,
balance, parameter, transport, timeout, and settlement problems are raised as
exceptions from the official Polymarket SDK. The polling timeout for an
accepted order is 10 seconds.

See [docs/clob.md](docs/clob.md) for the complete API and execution details.

## Optional order ledger

The optional ledger stores executed CLOB results as `OrderRecord` values in an
append-only JSONL file. Order submission remains explicit through the CLOB
client; the application creates and registers the record after a successful
result:

```python
import time
from decimal import Decimal

from polymarket_sdk_wrapper.ledger import OrderLedger, OrderRecord

# client is the initialized PolymarketClient from the CLOB example above.
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
await ledger.register_order(record)
```

Gamma, CLOB and the ledger remain independent. Direct CLOB use does not
require a ledger, and `OrderRecord` metadata is optional when the application
does not have outcome, side or order-type context available. See
[docs/ledger.md](docs/ledger.md) for the complete ledger API.

## Smoke tests

Create a local configuration from the example and fill in a real event link:

```bash
cp smoke/gamma/.env.example smoke/gamma/.env
uv run --env-file smoke/gamma/.env python smoke/gamma/smoke.py
```

The CLOB smoke script sends a real order and can spend funds:

```bash
cp smoke/clob/.env.example smoke/clob/.env
uv run --env-file smoke/clob/.env python smoke/clob/smoke.py
```

The ledger smoke simulates a CLOB result, records it as an `OrderRecord` in
`smoke/ledger/orders.jsonl`, and prints the calculated properties and orders
currently loaded by the ledger:

```bash
uv run smoke/ledger/smoke.py
```

Review the token, amount, minimum order size, current order book, and
`max_price` before running the CLOB real-order smoke.

The real `.env` files are ignored by Git. Gamma and CLOB live in independent
packages under `src/polymarket_sdk_wrapper/`; see
[docs/architecture.md](docs/architecture.md) for the package boundary.
