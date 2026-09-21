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

## Smoke test

Create a local configuration from the example and fill in a real event link:

```bash
cp smoke/gamma/.env.example smoke/gamma/.env
uv run --env-file smoke/gamma/.env python smoke/gamma/smoke.py
```

The real `.env` is ignored by Git. CLOB code lives in its own package under
`src/polymarket_sdk_wrapper/clob/`; Gamma does not import it. See
[docs/architecture.md](docs/architecture.md) for the package boundary.
