# IBKR TWS API — Vendored Local Install

## Problem

The `ibapi` package on PyPI is **frozen at version 9.81.1.post1** (a community upload from circa 2020). Interactive Brokers does not officially maintain a PyPI presence. All versions from 10.x onward must be obtained directly from IBKR.

This means `pip install ibapi` or pinning `ibapi>=9.81.1.post1` in `requirements.txt` is effectively useless for anyone who needs the modern API (asyncio support, newer order types, updated field sets, etc.).

## Solution — Vendor the Source

IBKR distributes the TWS API as a zip containing a standard Python package at:

```
IBJts/source/pythonclient/
```

That directory has a `setup.py` and the `ibapi/` module. It's pip-installable as-is from a local path.

### Directory layout after vendoring

```
juicyfruitstockoptions/
└── vendor/
    └── ibapi/          ← extracted from IBKR zip (gitignored binary, tracked via script)
        ├── setup.py
        ├── ibapi/
        │   ├── client.py
        │   ├── wrapper.py
        │   └── ...
        └── ...
```

### requirements.txt entry

```
# ibapi is NOT on PyPI — install from vendored local source
./vendor/ibapi
```

`pip install -r requirements.txt` resolves the local path and runs `setup.py install`. Works identically in Docker because `COPY . .` includes `vendor/`.

## Update Script

`ibkr-ibapi-update.sh` automates the fetch-and-extract:

```bash
./ibkr-ibapi-update.sh              # auto-detect latest version
./ibkr-ibapi-update.sh 10.26.01     # pin specific version
```

What it does:
1. Attempts to scrape the IBKR CDN page for the latest `twsapi_macunix.{VERSION}.zip`
2. Falls back to a hardcoded `FALLBACK_VERSION` if scraping fails
3. Downloads the zip, extracts only `IBJts/source/pythonclient/`
4. Copies it to `vendor/ibapi/`

### CDN URL pattern

```
https://interactivebrokers.github.io/downloads/twsapi_macunix.{VERSION}.zip
```

If the auto-detect fails (IBKR changes their CDN structure), manually download from:
> https://www.interactivebrokers.com/en/trading/ib-api.php

Then run: `./ibkr-ibapi-update.sh <version>`

## Docker Compatibility

The `Dockerfile` already does:

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

Since `COPY . .` runs **after** the pip install step, the local `./vendor/ibapi` path must be available **before** the `pip install` step. Two options:

**Option A (current — simplest):** Commit `vendor/ibapi/` to git.
- Pro: fully reproducible builds with no network dependency
- Con: commits IBKR source into your repo

**Option B (CI-clean):** Run `ibkr-ibapi-update.sh` in the Dockerfile before `pip install`.

```dockerfile
COPY ibkr-ibapi-update.sh .
RUN apt-get install -y unzip && ./ibkr-ibapi-update.sh
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
```

Option A is preferred for a dev-focused single-machine setup.

## Version History Awareness

| Version | Notes |
|---------|-------|
| 9.81.1.post1 | Last PyPI upload (~2020), used legacy socket threading model |
| 10.x | Major rewrite — newer field names, asyncio-friendly structure |
| 10.26.x | Current stable as of late 2024 |

Always check: https://www.interactivebrokers.com/en/trading/ib-api.php for the latest.

## References
- IBKR API download page: https://www.interactivebrokers.com/en/trading/ib-api.php
- IBKR CDN: https://interactivebrokers.github.io/downloads/
- Update script: [ibkr-ibapi-update.sh](../../ibkr-ibapi-update.sh)
