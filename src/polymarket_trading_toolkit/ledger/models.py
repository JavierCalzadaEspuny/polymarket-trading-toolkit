from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from polymarket_trading_toolkit.clob import Fill, OrderResult


@dataclass(slots=True)
class OrderRecord:
    created_at: int
    token: str
    amount: Decimal
    order_result: OrderResult
    max_price: Decimal | None = None
    outcome: Literal["Yes", "No"] | None = None
    side: Literal["BUY", "SELL"] | None = None
    order_type: Literal["FAK", "GTC"] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "created_at": self.created_at,
            "outcome": self.outcome,
            "side": self.side,
            "order_type": self.order_type,
            "token": self.token,
            "amount": str(self.amount),
            "max_price": str(self.max_price) if self.max_price is not None else None,
            "order_result": self.order_result.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "OrderRecord":
        order_data = data["order_result"]
        if not isinstance(order_data, dict):
            raise ValueError("Order record has invalid order result data")

        fills_data = order_data["fills"]
        if not isinstance(fills_data, list):
            raise ValueError("Order record has invalid fills data")

        fills = [
            Fill(
                trade_id=str(fill["trade_id"]),
                size=Decimal(str(fill["size"])),
                price=Decimal(str(fill["price"])),
                status=str(fill["status"]),
                transaction_hash=(
                    str(fill["transaction_hash"])
                    if fill["transaction_hash"] is not None
                    else None
                ),
            )
            for fill in fills_data
            if isinstance(fill, dict)
        ]
        if len(fills) != len(fills_data):
            raise ValueError("Order record has invalid fill data")

        order_result = OrderResult(
            order_id=(
                str(order_data["order_id"])
                if order_data["order_id"] is not None
                else None
            ),
            status=order_data["status"],
            fills=fills,
        )
        return cls(
            created_at=int(data["created_at"]),
            token=str(data["token"]),
            amount=Decimal(str(data["amount"])),
            order_result=order_result,
            max_price=(
                Decimal(str(data["max_price"]))
                if data.get("max_price") is not None
                else None
            ),
            outcome=data.get("outcome"),
            side=data.get("side"),
            order_type=data.get("order_type"),
        )
