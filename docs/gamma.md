# Gamma

This document describes package version `1.0.0`.

`GammaEvent` loads one event with the official Polymarket SDK and keeps the
parsed `Event` snapshot in memory. All lookups after loading are local.

```python
from datetime import UTC, datetime

from polymarket_trading_toolkit.gamma import GammaEvent, token

event = GammaEvent.load("https://polymarket.com/event/example")
market = event.nearest_market(reference_time=datetime.now(UTC))

yes_token = token(market, "Yes")
no_token = token(market, "No")
```

`GammaEvent.load_async(...)` provides the same result for async programs.

## Market selection

`nearest_market(reference_time)` considers every market with a non-null
`endDate`. It compares the timestamp as an absolute instant and returns the
market with the smallest `endDate` strictly after `reference_time`.

It deliberately does not filter on `active`, `closed`, `acceptingOrders`, or
`enableOrderBook`; those are separate trading checks for the CLOB layer.

`reference_time` accepts an aware `datetime`, an ISO 8601 string with an
offset, or a Unix timestamp. Naive datetimes and ISO strings without a timezone
are rejected because Gamma no longer receives a timezone from the caller to
interpret them safely.

This means an API value such as `2027-01-01T04:59:00Z` is compared as that
instant. It is not converted into a calendar date and rebuilt at local
`23:59:59`, which avoids shifting the deadline across a timezone boundary.

## Identifiers

`token(market, outcome)` is an in-memory lookup. It uses a complete Yes/No
`token_id` pair when available and otherwise a complete Yes/No `position_id`
pair. It never performs a network request or selects a market itself.

There is no refresh, TTL, persistence, or implicit clock read. If newer
markets may have appeared, call `GammaEvent.load(...)` again explicitly.
