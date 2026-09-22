# CLOB

`PolymarketClient` es un wrapper pequeño sobre `polymarket-client` para
órdenes autenticadas de compra `BUY` con tipo `FAK` (Fill And Kill).

El cliente es reutilizable mientras el proceso siga vivo. La autenticación y
las approvals se preparan una vez al crear la instancia; después se pueden
enviar varias órdenes con la misma instancia.

## Crear y reutilizar el cliente

```python
from decimal import Decimal

from polymarket_sdk_wrapper.clob import PolymarketClient


client = await PolymarketClient.create(
    private_key=private_key,
    wallet_address=wallet_address,
    relayer_api_key=relayer_api_key,
    relayer_api_key_address=relayer_api_key_address,
)

try:
    first = await client.place_order(
        token=yes_token_id,
        amount=Decimal("10"),
        max_price=Decimal("0.55"),
    )
    second = await client.place_order(
        token=no_token_id,
        amount=Decimal("10"),
        max_price=Decimal("0.50"),
    )
finally:
    await client.close()
```

La clase no implementa `async with`; el cierre se hace explícitamente con
`close()`. El objeto autenticado vive en memoria. Si el proceso termina, hay
que crear otra instancia.

## Parámetros de una orden

`place_order(...)` acepta actualmente:

- `token`: identificador CLOB del outcome (`Yes` o `No`).
- `amount`: presupuesto de compra en pUSD.
- `max_price`: precio máximo por share. `None` elimina esta protección y no se
  recomienda para un smoke test.

Después de aceptar una orden, el wrapper espera como máximo 10 segundos a que
el CLOB publique sus trade ids. Este límite está integrado en la clase y no se
configura por llamada.

El wrapper pasa también `max_spend=amount` al SDK. Esto mantiene el gasto total
dentro del presupuesto indicado, incluyendo los costes que el SDK pueda
estimar. La cantidad debe ser compatible con el mínimo de shares del mercado.
El precio de Gamma puede estar desactualizado; para ejecutar conviene consultar
el order book del CLOB inmediatamente antes.

FAK intenta ejecutar inmediatamente contra la liquidez disponible. La parte no
ejecutada se cancela y la orden nunca queda descansando en el book. Si el CLOB
rechaza la operación porque no hay match, el SDK puede lanzar
`RequestRejectedError`; el smoke test reconoce ese caso y lo imprime como
`NO_FILL`.

Después de aceptar una orden, el wrapper consulta su estado cada 250 ms y
espera como máximo 10 segundos a que aparezcan sus trade ids. El límite está
integrado en la clase y no se configura por llamada. Si se alcanza, devuelve
`ORDER_STATUS_TIMEOUT`.

## Resultado y estados

`OrderResult.to_dict()` devuelve únicamente los datos normalizados por el
wrapper:

```json
{
  "order_id": "0x...",
  "status": "FULL_FILL",
  "fills": [
    {
      "trade_id": "...",
      "size": "61.836735",
      "price": "0.049",
      "status": "CONFIRMED",
      "transaction_hash": "0x..."
    }
  ]
}
```

Estados posibles:

- `FULL_FILL`: todas las shares solicitadas se ejecutaron.
- `PARTIAL_FILL`: solo se ejecutó una parte.
- `REJECTED`: el SDK devolvió una respuesta `RejectedOrder`.
- `UNMATCHED`: el CLOB marcó la orden aceptada como no emparejada.
- `INVALID`: el CLOB marcó la orden aceptada como inválida.
- `CANCELED`: la orden fue cancelada sin ejecución.
- `CANCELED_MARKET_RESOLVED`: la orden fue cancelada porque el mercado se
  resolvió.
- `SETTLEMENT_FAILED`: al menos un fill terminó con estado `FAILED`.
- `ORDER_STATUS_TIMEOUT`: la orden aceptada no expuso sus trade ids dentro de
  los 10 segundos.

Los nombres `UNMATCHED`, `INVALID`, `CANCELED` y
`CANCELED_MARKET_RESOLVED` se devuelven tal como los proporciona el CLOB; el
wrapper no los traduce a nombres propios. Los errores de autenticación,
transporte, validación y los rechazos del SDK que no sean gestionados
explícitamente se propagan como excepciones.

## Fills y niveles de precio

Cada fill contiene `trade_id`, `size`, `price`, `status` y
`transaction_hash`.

`FULL_FILL` describe la cantidad total ejecutada; no implica que todos los
niveles tuvieran el mismo precio. El `price` del fill es el valor agregado que
devuelve el CLOB. El desglose de `maker_orders` no lo expone actualmente este
wrapper; si se necesita, hay que consultar el modelo de trade original del
SDK.

## Alcance

El wrapper no persiste órdenes ni posiciones, no mantiene un tracker continuo,
no usa WebSocket y no indexa Polygon. La aplicación que lo consuma puede
guardar los `OrderResult` y sus fills según sus propias necesidades.

## Smoke test

`smoke/clob/smoke.py` envía una orden real y puede gastar fondos. No es un test
offline.

```bash
cp smoke/clob/.env.example smoke/clob/.env
# Edita el token, importe, precio máximo y credenciales.
uv run --env-file smoke/clob/.env python smoke/clob/smoke.py
```

El archivo `.env` está ignorado por Git. Nunca incluyas claves privadas ni
claves del relayer en el repositorio.
