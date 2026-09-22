"""Place one real BUY FAK order and print its execution report.

This script can spend real funds. Use it only with a deliberate token,
amount, and maximum price.

Run from the repository root with:

    uv run --env-file smoke/clob/.env python smoke/clob/smoke.py
"""

from __future__ import annotations

import asyncio
import json
import os
from decimal import Decimal

from polymarket_sdk_wrapper.clob import PolymarketClient


def _required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing {name}")
    return value


async def main() -> None:
    token = _required("POLYMARKET_TOKEN_ID")
    amount = Decimal(_required("POLYMARKET_AMOUNT"))
    max_price = Decimal(_required("POLYMARKET_MAX_PRICE"))
    print(f"token:      {token}")
    print(f"amount:     {amount}")
    print(f"max_price:  {max_price}")
    client = await PolymarketClient.create(
        private_key=_required("POLYMARKET_PRIVATE_KEY"),
        wallet_address=_required("POLYMARKET_WALLET_ADDRESS"),
        relayer_api_key=_required("POLYMARKET_RELAYER_API_KEY"),
        relayer_api_key_address=_required("POLYMARKET_RELAYER_API_KEY_ADDRESS"),
    )
    print("Client created successfully")

    try:
        result = await client.place_order(
            token=token,
            amount=amount,
            max_price=max_price,
        )
        print(f"Order result: {result.status}")
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str))
    finally:
        await client.close()
        print("Client closed successfully")


if __name__ == "__main__":
    asyncio.run(main())
