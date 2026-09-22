import asyncio
import json
from decimal import Decimal
from pathlib import Path

from .models import OrderRecord


class OrderLedger:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.orders: list[OrderRecord] = self._load()
        self._order_ids = {
            record.order_result.order_id
            for record in self.orders
            if record.order_result.order_id is not None
        }
        self._lock = asyncio.Lock()

    def _load(self) -> list[OrderRecord]:
        if not self.path.exists():
            return []
        return [
            OrderRecord.from_dict(json.loads(line))
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _append(self, record: OrderRecord) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(
                f"{json.dumps(record.to_dict(), ensure_ascii=False)}\n"
            )

    def orders_for_token(self, token: str) -> list[OrderRecord]:
        return [record for record in self.orders if record.token == token]

    def spent_usd(self, token: str) -> Decimal:
        return sum(
            (
                record.order_result.total_cost
                for record in self.orders_for_token(token)
            ),
            Decimal("0"),
        )

    async def register_order(self, record: OrderRecord) -> bool:
        order_id = record.order_result.order_id
        if order_id is None or record.order_result.status == "NO_FILL":
            raise ValueError("Only filled orders can be registered")

        async with self._lock:
            if order_id in self._order_ids:
                return False
            await asyncio.to_thread(self._append, record)
            self.orders.append(record)
            self._order_ids.add(order_id)
            return True
