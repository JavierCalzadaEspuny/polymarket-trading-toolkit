from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(slots=True)
class Fill:
    trade_id: str
    size: Decimal
    price: Decimal
    status: str
    transaction_hash: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "trade_id": self.trade_id,
            "size": str(self.size),
            "price": str(self.price),
            "status": self.status,
            "transaction_hash": self.transaction_hash,
        }


@dataclass(slots=True)
class OrderResult:
    order_id: str | None
    status: Literal["FULL_FILL", "PARTIAL_FILL", "NO_FILL"]
    fills: list[Fill]

    @property
    def total_cost(self) -> Decimal:
        return sum(
            (
                fill.size * fill.price
                for fill in self.fills
                if fill.status.upper() == "CONFIRMED"
            ),
            Decimal("0"),
        )

    @property
    def total_size(self) -> Decimal:
        return sum(
            (
                fill.size
                for fill in self.fills
                if fill.status.upper() == "CONFIRMED"
            ),
            Decimal("0"),
        )

    @property
    def average_price(self) -> Decimal | None:
        total_size = self.total_size
        if total_size == 0:
            return None
        return self.total_cost / total_size

    def to_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "status": self.status,
            "fills": [fill.to_dict() for fill in self.fills],
        }
