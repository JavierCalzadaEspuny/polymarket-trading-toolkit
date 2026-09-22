# Repository instructions

## Purpose

This repository contains small, reusable Python wrappers around the official
Polymarket SDK. Keep the wrappers narrow and avoid turning them into an
application, persistence layer, or trading daemon.

## Layout

- `src/polymarket_sdk_wrapper/gamma/`: public event and market snapshots.
- `src/polymarket_sdk_wrapper/clob/`: authenticated BUY FAK orders and fill
  reconciliation.
- `docs/`: user-facing API and architecture documentation.
- `smoke/`: explicitly manual scripts; the CLOB smoke script sends a real
  order.

## Development commands

Use the locked environment and Python version:

```bash
uv sync --frozen
./.venv/bin/python -m compileall -q src smoke
```

This repository intentionally does not keep a committed `tests/` directory or
test dependency. When focused validation is needed, create a temporary test
file outside the repository, run it with `PYTHONPATH=src`, inspect the result,
and delete the file and any bytecode before finishing.

## Safety

- Never print, commit, or paste private keys, relayer keys, or real `.env`
  contents.
- `smoke/clob/smoke.py` can spend real funds. Check token, amount, minimum
  order size, current order book, and `max_price` before running it.
- Keep `.env` files local; only `.env.example` files belong in the repository.
- Do not add automatic retries for order submission unless the operation's
  idempotency and possible duplicate execution are understood.

## API conventions

- Use `Decimal` for prices, budgets, shares, fees, and PnL-related values.
- Keep the official SDK models where they are useful; do not duplicate its
  entire domain model in the wrapper.
- Preserve machine-readable error codes and human-readable messages.
- A known FAK no-match rejection is normalized as `NO_FILL` by the manual smoke
  script; authentication, transport, and unrelated request errors should
  remain visible to callers.
- `FULL_FILL` means the requested quantity was filled, not that execution used
  one price level. The current wrapper returns the aggregate fill price and
  does not expose `maker_orders`.
- The in-memory CLOB client can be reused until `close()`; it is not persisted
  across process restarts.

## Boundaries

Gamma selects markets and returns token identifiers. CLOB submits orders and
reconciles their fills. There is currently no position reader, Polygon
indexer, WebSocket tracker, database, or automatic position cache in this
repository.

## Documentation changes

When public behavior changes, update `docs/clob.md` or `docs/gamma.md`, the
relevant README section, and this file if the repository workflow or safety
rules change. Keep examples aligned with the actual public signatures.
