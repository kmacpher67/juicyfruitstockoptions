# Implementation Plan: IBKR Client Portal Fallback

## Goal

Implement the lower-priority IBKR Client Portal fallback items already listed in `docs/features-requirements.md` without changing the existing Flex or TWS behavior by default.

## Checklist

- [x] Settings updates required
- [x] Docker Compose update required
- [x] New service added with single responsibility
- [x] New CLI entry point added for manual verification
- [x] Tests added for new backend behavior
- [x] Related `docs/features-requirements.md` items updated
- [x] Feature and learning docs updated

## Given / When

- Given `IBKR_PORTAL_ENABLED=false`, when the service is instantiated, then it should behave as a no-op fallback and return safe empty values.
- Given the Client Portal gateway is running and authenticated, when `keepalive()` is called, then the service should POST `/tickle`.
- Given an account id is configured or discoverable, when `get_positions()` or `get_summary()` is called, then the service should poll the corresponding REST endpoint.

## Scope Delivered

1. Add portal feature-flag settings to `app/config.py`.
2. Add an `ibkr-portal` Docker Compose service around the checked-in `clientportal.gw` bundle.
3. Create `app/services/ibkr_portal_service.py`.
4. Create `app/scripts/ibkr_portal_cli.py`.
5. Add unit tests in `tests/test_ibkr_portal_service.py`.
6. Update README and roadmap/docs.

## Deferred

- FastAPI lifespan registration
- APScheduler integration
- Frontend status surfaces
- Automatic auth/session bootstrap beyond keepalive support
