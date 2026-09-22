"""Small, in-memory wrapper around the Polymarket Gamma API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from polymarket import AsyncPublicClient, Event, Market, PublicClient

ReferenceTime = datetime | str | int | float


def _as_utc(value: ReferenceTime) -> datetime:
    """Normalize an aware datetime, ISO string, or Unix timestamp to UTC."""
    if isinstance(value, (int, float)):
        value = datetime.fromtimestamp(value, tz=UTC)
    elif isinstance(value, str):
        value = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    elif not isinstance(value, datetime):
        raise TypeError("reference_time must be a datetime, ISO string, or Unix timestamp")

    if value.tzinfo is None:
        raise ValueError("reference_time must include a timezone")
    return value.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class GammaEvent:
    """An SDK event snapshot whose lookups never access the network."""

    link: str
    event: Event

    @classmethod
    def load(cls, link: str) -> "GammaEvent":
        """Load one event snapshot synchronously."""
        with PublicClient() as client:
            return cls(link, client.get_event(url=link))

    @classmethod
    async def load_async(cls, link: str) -> "GammaEvent":
        """Load one event snapshot asynchronously."""
        async with AsyncPublicClient() as client:
            return cls(link, await client.get_event(url=link))

    def nearest_market(self, reference_time: ReferenceTime) -> Market | None:
        """Return the future market with the nearest absolute ``endDate``."""
        current = _as_utc(reference_time)
        future_markets = [
            market
            for market in self.event.markets
            if market.state.end_date is not None
            and _as_utc(market.state.end_date) > current
        ]
        return min(
            future_markets,
            key=lambda market: _as_utc(market.state.end_date),
            default=None,
        )


def token(market: Market, outcome: Literal["Yes", "No"]) -> str:
    """Return the selected outcome's asset identifier from a market."""
    if outcome not in ("Yes", "No"):
        raise ValueError("outcome must be 'Yes' or 'No'")

    selected = market.outcomes.yes if outcome == "Yes" else market.outcomes.no
    counterpart = market.outcomes.no if outcome == "Yes" else market.outcomes.yes
    if selected.token_id is not None and counterpart.token_id is not None:
        return str(selected.token_id)
    if selected.position_id is not None and counterpart.position_id is not None:
        return str(selected.position_id)

    raise ValueError(
        f"Gamma market does not contain a complete Yes/No identifier pair (outcome={outcome!r})"
    )
