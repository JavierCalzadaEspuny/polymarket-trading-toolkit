import asyncio
from dataclasses import dataclass
from decimal import Decimal

from polymarket import AcceptedOrder, AsyncSecureClient, RejectedOrder, RelayerApiKey


@dataclass(slots=True)
class OrderResult:
    order_id: str | None
    status: str
    fills: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "order_id": self.order_id,
            "status": self.status,
            "fills": self.fills,
        }


class PolymarketClient:
    """Authenticated client for BUY FAK orders."""

    _POLL_INTERVAL_S = 0.25
    _ORDER_STATUS_TIMEOUT_S = 10.0
    _TERMINAL_ORDER_STATUSES = {
        "UNMATCHED",
        "INVALID",
        "CANCELED",
        "CANCELED_MARKET_RESOLVED",
    }

    def __init__(self, client: AsyncSecureClient) -> None:
        self._client = client

    @classmethod
    async def create(
        cls,
        private_key: str,
        wallet_address: str,
        relayer_api_key: str,
        relayer_api_key_address: str,
    ) -> "PolymarketClient":
        client = await AsyncSecureClient.create(
            private_key=private_key,
            wallet=wallet_address,
            api_key=RelayerApiKey(
                key=relayer_api_key,
                address=relayer_api_key_address,
            ),
        )
        wrapper = cls(client)
        try:
            await client.setup_trading_approvals()
        except Exception:
            await wrapper.close()
            raise
        return wrapper

    async def place_order(
        self,
        *,
        token: str,
        amount: Decimal,
        max_price: Decimal | float | None,
    ) -> OrderResult:
        response = await self._client.place_market_order(
            token_id=token,
            side="BUY",
            amount=amount,
            max_price=max_price,
            max_spend=amount,
            order_type="FAK",
        )

        if isinstance(response, RejectedOrder):
            return OrderResult(None, "REJECTED", [])
        if not isinstance(response, AcceptedOrder):
            raise RuntimeError("Polymarket returned an unknown order response")

        order_id = str(response.order_id)
        trade_ids = {str(trade_id) for trade_id in response.trade_ids}
        deadline = asyncio.get_running_loop().time() + self._ORDER_STATUS_TIMEOUT_S

        while True:
            remaining_s = deadline - asyncio.get_running_loop().time()
            if remaining_s <= 0:
                return OrderResult(order_id, "ORDER_STATUS_TIMEOUT", [])

            try:
                order = await asyncio.wait_for(
                    self._client.get_order(order_id=order_id),
                    timeout=remaining_s,
                )
            except asyncio.TimeoutError:
                return OrderResult(order_id, "ORDER_STATUS_TIMEOUT", [])

            trade_ids.update(str(trade_id) for trade_id in order.associate_trades)

            if trade_ids:
                break

            order_status = str(order.status).upper()
            if (
                order_status in self._TERMINAL_ORDER_STATUSES
                and order.size_matched == 0
            ):
                return OrderResult(order_id, order_status, [])

            remaining_s = deadline - asyncio.get_running_loop().time()
            if remaining_s <= 0:
                return OrderResult(order_id, "ORDER_STATUS_TIMEOUT", [])
            await asyncio.sleep(min(self._POLL_INTERVAL_S, remaining_s))

        accepted = response.model_copy(update={"trade_ids": tuple(trade_ids)})
        await self._client.wait_for_order_fill_settlement(accepted)

        fills: list[dict[str, object]] = []
        for trade_id in trade_ids:
            page = await self._client.list_account_trades(id=trade_id).first_page()
            trade = next(item for item in page.items if str(item.id) == trade_id)
            fills.append(
                {
                    "trade_id": str(trade.id),
                    "size": Decimal(str(trade.size)),
                    "price": Decimal(str(trade.price)),
                    "status": str(trade.status),
                    "transaction_hash": trade.transaction_hash,
                }
            )

        if any(str(fill["status"]).upper() == "FAILED" for fill in fills):
            status = "SETTLEMENT_FAILED"
        elif sum((fill["size"] for fill in fills), Decimal("0")) < order.original_size:
            status = "PARTIAL_FILL"
        else:
            status = "FULL_FILL"

        return OrderResult(order_id, status, fills)

    async def close(self) -> None:
        await self._client.close()
