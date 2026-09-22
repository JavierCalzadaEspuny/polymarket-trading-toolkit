"""Small real-network check for the Gamma wrapper.

Run from the repository root with:

    uv run --env-file smoke/gamma/.env python smoke/gamma/smoke.py
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime

from polymarket_trading_toolkit import GammaEvent, token


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}")
    return value


def main() -> None:
    link = _required("POLYMARKET_EVENT_URL")
    outcome = _required("POLYMARKET_EVENT_OUTCOME")
    reference_value = os.environ.get("POLYMARKET_EVENT_REFERENCE_TIME")

    snapshot = GammaEvent.load(link)
    if reference_value:
        reference_time = datetime.fromisoformat(reference_value.replace("Z", "+00:00"))
    else:
        reference_time = datetime.now(UTC)

    market = snapshot.nearest_market(reference_time=reference_time)
    if market is None:
        raise SystemExit("The event has no market with a future endDate.")
    outcome_token = token(market, outcome)

    print(f"link:               {snapshot.link}")
    print(f"reference:          {reference_time.isoformat()}")
    print(f"reference UTC:      {reference_time.astimezone(UTC).isoformat()}")
    print(f"input:              {reference_value or 'current time'}")
    print("SELECTED MARKET")
    print(json.dumps(
        market.model_dump(mode="json", by_alias=True),
        indent=2,
        ensure_ascii=False,
        default=str,
    ))
    print(f"{outcome} token: {outcome_token}")


if __name__ == "__main__":
    main()
