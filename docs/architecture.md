# Architecture

This document describes package version `0.1.0`.

The wrapper is split by Polymarket API surface:

```text
polymarket_sdk_wrapper/
├── gamma/   public event and market metadata
├── clob/    authenticated order and fill workflows
│   └── models.py   public CLOB result models
└── ledger/  optional order records and JSONL persistence
```

Gamma and CLOB are intentionally independent modules. Gamma only loads a
public event snapshot through the official SDK and performs fast in-memory
selection. It does not know about wallets, orders, fills, persistence, or
trading decisions.

CLOB is the place for authenticated order submission and fill reconciliation.
It can consume the identifier returned by `token(...)` without making Gamma
depend on CLOB details. It does not persist orders or positions, track account
state continuously, or index Polygon logs itself.

The optional `ledger` package provides `OrderRecord` and the default JSONL
`OrderLedger`. Applications submit orders through CLOB, create an
`OrderRecord` from the resulting `OrderResult`, and register it in the ledger.
Neither Gamma nor CLOB imports `ledger`, and applications can use CLOB without
any persistence layer.

The repository contains no shared application configuration layer. Each
wrapper accepts the small set of values it needs, so the package can be used
from scripts, services, or tests without importing another application.

See [docs/clob.md](clob.md), [docs/gamma.md](gamma.md) and
[docs/ledger.md](ledger.md) for the public examples and current boundaries of
those wrappers. The ledger smoke demonstrates the optional persistence flow
without contacting the network.
