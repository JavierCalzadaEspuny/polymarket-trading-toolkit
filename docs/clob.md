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
rechaza la operación porque no hay match, el wrapper devuelve un
`OrderResult` con estado `NO_FILL`.

Después de aceptar una orden, el wrapper consulta su estado cada 250 ms y
espera como máximo 10 segundos a que aparezcan sus trade ids. El límite está
integrado en la clase y no se configura por llamada. Si se alcanza, devuelve
lanza una excepción `polymarket.errors.TimeoutError`.

## Resultado y estados

`OrderResult.to_dict()` devuelve siempre la misma estructura:

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
- `NO_FILL`: no se ejecutó ninguna share porque no había una contraparte
  compatible con `max_price`.

Los errores de autenticación, transporte, validación, balance, timeout y
settlement se propagan como excepciones del SDK. El wrapper solo convierte los
rechazos FAK conocidos por falta de match en `NO_FILL`.

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
