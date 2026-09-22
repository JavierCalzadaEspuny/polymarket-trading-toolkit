# Polymarket SDK Wrapper

Small, independent wrappers around the official `polymarket-client` SDK.

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

## CLOB quick start

The CLOB wrapper creates one authenticated client that can be reused for
multiple BUY FAK orders:

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

See [docs/clob.md](docs/clob.md) for order states, fill details and timeouts.

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

The real `.env` files are ignored by Git. Gamma and CLOB live in independent
packages under `src/polymarket_sdk_wrapper/`; see
[docs/architecture.md](docs/architecture.md) for the package boundary.
