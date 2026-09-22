import asyncio
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from polymarket import AcceptedOrder, AsyncSecureClient, RejectedOrder, RelayerApiKey
from polymarket.errors import (
    RequestRejectedError,
    TransactionFailedError,
    UnexpectedResponseError,
    TimeoutError as PolymarketTimeoutError,
)


@dataclass(slots=True)
class OrderResult:
    order_id: str | None
    status: Literal["FULL_FILL", "PARTIAL_FILL", "NO_FILL"]
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
    _NO_FILL_ERROR_CODES = {"FAK_NOT_FILLED", "UNMATCHED"}

    def __init__(self, client: AsyncSecureClient) -> None:
        self._client = client

    @classmethod
    def _is_no_fill_rejection(cls, error: RequestRejectedError) -> bool:
        code = (error.code or "").upper()
        message = str(error).lower()
        return code in cls._NO_FILL_ERROR_CODES or (
            "no orders found to match with fak order" in message
        )

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
        try:
            response = await self._client.place_market_order(
                token_id=token,
                side="BUY",
                amount=amount,
                max_price=max_price,
                max_spend=amount,
                order_type="FAK",
            )
        except RequestRejectedError as error:
            if not self._is_no_fill_rejection(error):
                raise
            return OrderResult(None, "NO_FILL", [])

        if isinstance(response, RejectedOrder):
            if response.code.upper() in self._NO_FILL_ERROR_CODES:
                return OrderResult(None, "NO_FILL", [])
            raise RequestRejectedError(
                response.message,
                status=400,
                code=response.code,
            )
        if not isinstance(response, AcceptedOrder):
            raise UnexpectedResponseError("Polymarket returned an unknown order response")

        order_id = str(response.order_id)
        trade_ids = {str(trade_id) for trade_id in response.trade_ids}
        deadline = asyncio.get_running_loop().time() + self._ORDER_STATUS_TIMEOUT_S

        while True:
            remaining_s = deadline - asyncio.get_running_loop().time()
            if remaining_s <= 0:
                raise PolymarketTimeoutError(
                    "Timed out waiting for the accepted order status"
                )

            try:
                order = await asyncio.wait_for(
                    self._client.get_order(order_id=order_id),
                    timeout=remaining_s,
                )
            except asyncio.TimeoutError:
                raise PolymarketTimeoutError(
                    "Timed out waiting for the accepted order status"
                ) from None

            trade_ids.update(str(trade_id) for trade_id in order.associate_trades)

            if trade_ids:
                break

            order_status = str(order.status).upper()
            if (
                order_status in self._TERMINAL_ORDER_STATUSES
                and order.size_matched == 0
            ):
                if order_status == "UNMATCHED":
                    return OrderResult(order_id, "NO_FILL", [])
                raise RequestRejectedError(
                    f"Polymarket order ended with status {order_status}",
                    status=400,
                    code=order_status.lower(),
                )

            remaining_s = deadline - asyncio.get_running_loop().time()
            if remaining_s <= 0:
                raise PolymarketTimeoutError(
                    "Timed out waiting for the accepted order status"
                )
            await asyncio.sleep(min(self._POLL_INTERVAL_S, remaining_s))

        accepted = response.model_copy(update={"trade_ids": tuple(trade_ids)})
        await self._client.wait_for_order_fill_settlement(accepted)

        fills: list[dict[str, object]] = []
        for trade_id in trade_ids:
            page = await self._client.list_account_trades(id=trade_id).first_page()
            try:
                trade = next(item for item in page.items if str(item.id) == trade_id)
            except StopIteration as error:
                raise UnexpectedResponseError(
                    f"Trade {trade_id} was not returned by the account trades endpoint"
                ) from error
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
            raise TransactionFailedError("At least one order fill failed settlement")
        elif sum((fill["size"] for fill in fills), Decimal("0")) < order.original_size:
            status = "PARTIAL_FILL"
        else:
            status = "FULL_FILL"

        return OrderResult(order_id, status, fills)

    async def close(self) -> None:
        await self._client.close()
