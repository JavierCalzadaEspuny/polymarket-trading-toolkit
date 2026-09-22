"""Simulate one CLOB result and inspect the order ledger.

This smoke does not contact the network or spend funds. Run it from the
repository root with:

    uv run smoke/ledger/smoke.py
"""

from __future__ import annotations

import asyncio
import json
import time
from decimal import Decimal
from pathlib import Path

from polymarket_sdk_wrapper.clob import Fill, OrderResult
from polymarket_sdk_wrapper.ledger import OrderLedger, OrderRecord


ORDERS_PATH = Path(__file__).with_name("orders.jsonl")


class SimulatedClob:
    async def place_order(
        self,
        *,
        token: str,
        amount: Decimal,
        max_price: Decimal | None,
    ) -> OrderResult:
        del token, amount, max_price
        order_id = f"smoke-order-{time.time_ns()}"
        return OrderResult(
            order_id=order_id,
            status="FULL_FILL",
            fills=[
                Fill(
                    trade_id=f"{order_id}-trade-1",
                    size=Decimal("2"),
                    price=Decimal("0.40"),
                    status="CONFIRMED",
                    transaction_hash=None,
                ),
                Fill(
                    trade_id=f"{order_id}-trade-2",
                    size=Decimal("3"),
                    price=Decimal("0.50"),
                    status="CONFIRMED",
                    transaction_hash=None,
                ),
            ],
        )


async def main() -> None:
    token = "simulated-token"
    ledger = OrderLedger(ORDERS_PATH)
    orders_before = len(ledger.orders_for_token(token))
    spent_before = ledger.spent_usd(token)

    result = await SimulatedClob().place_order(
        token=token,
        amount=Decimal("10"),
        max_price=Decimal("0.50"),
    )

    record = OrderRecord(
        created_at=int(time.time()),
        token=token,
        amount=Decimal("10"),
        order_result=result,
        max_price=Decimal("0.50"),
        outcome="Yes",
        side="BUY",
        order_type="FAK",
    )
    if not await ledger.register_order(record):
        raise RuntimeError("The simulated order was not registered")

    orders_for_token = ledger.orders_for_token(token)
    spent_after = ledger.spent_usd(token)
    if len(orders_for_token) != orders_before + 1:
        raise RuntimeError("The ledger did not index the order by token")
    if spent_after != spent_before + result.total_cost:
        raise RuntimeError("The ledger calculated an unexpected token spend")

    result = record.order_result
    print(f"orders path:   {ORDERS_PATH}")
    print("Simulated order registered through OrderLedger.")
    print(json.dumps(record.to_dict(), indent=2, ensure_ascii=False))
    print(f"total_cost:    {result.total_cost}")
    print(f"total_size:    {result.total_size}")
    print(f"average_price: {result.average_price}")
    print(f"orders_for_token: {len(orders_for_token)}")
    print(f"spent_usd:        {spent_after}")
    print("Orders currently stored in memory:")
    for stored_order in ledger.orders:
        print(json.dumps(stored_order.to_dict(), indent=2, ensure_ascii=False))
    print(f"stored orders:  {len(ledger.orders)}")


if __name__ == "__main__":
    asyncio.run(main())
