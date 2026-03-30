import logging
from typing import Any

import requests

from app.config import settings


logger = logging.getLogger(__name__)


class IBKRPortalService:
    """Session-aware REST client for the IBKR Client Portal gateway."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        enabled: bool | None = None,
        account_id: str | None = None,
        verify_ssl: bool | None = None,
        timeout_seconds: int | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self.enabled = settings.IBKR_PORTAL_ENABLED if enabled is None else enabled
        self.base_url = self._normalize_base_url(
            base_url or settings.IBKR_PORTAL_BASE_URL
        )
        self.account_id = account_id
        self._fallback_account_id = settings.IBKR_PORTAL_ACCOUNT_ID
        self._account_id_explicit = account_id is not None
        self.verify_ssl = (
            settings.IBKR_PORTAL_VERIFY_SSL if verify_ssl is None else verify_ssl
        )
        self.timeout_seconds = (
            settings.IBKR_PORTAL_TIMEOUT_SECONDS
            if timeout_seconds is None
            else timeout_seconds
        )
        self.session = session or requests.Session()

    @staticmethod
    def _normalize_base_url(base_url: str) -> str:
        return base_url.rstrip("/")

    def _is_disabled(self) -> bool:
        if not self.enabled:
            logger.info("IBKR Client Portal service is disabled by feature flag.")
            return True
        return False

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base_url}{path}"
        response = self.session.request(
            method=method,
            url=url,
            timeout=kwargs.pop("timeout", self.timeout_seconds),
            verify=kwargs.pop("verify", self.verify_ssl),
            **kwargs,
        )
        response.raise_for_status()

        if not response.content:
            return {}

        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type.lower():
            return response.json()

        try:
            return response.json()
        except ValueError:
            logger.debug("Non-JSON response received from %s", url)
            return {"raw": response.text}

    def _extract_account_id(self, payload: Any) -> str | None:
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    account_id = item.get("id") or item.get("accountId") or item.get("accountIdKey")
                    if account_id:
                        return str(account_id)

        if isinstance(payload, dict):
            for key in ("selectedAccount", "accountId", "id"):
                if payload.get(key):
                    return str(payload[key])
            for key in ("accounts", "acctList"):
                if isinstance(payload.get(key), list):
                    extracted = self._extract_account_id(payload[key])
                    if extracted:
                        return extracted

        return None

    def _resolve_account_id(self) -> str | None:
        if self._account_id_explicit and self.account_id:
            return self.account_id

        accounts = self._request("GET", "/portfolio/accounts")
        resolved_account_id = self._extract_account_id(accounts)
        if resolved_account_id:
            self.account_id = resolved_account_id
            logger.info("Resolved IBKR Client Portal account id: %s", resolved_account_id)
            return resolved_account_id

        if self.account_id:
            return self.account_id
        if self._fallback_account_id:
            self.account_id = self._fallback_account_id
            logger.info(
                "Falling back to configured IBKR Client Portal account id: %s",
                self._fallback_account_id,
            )
            return self._fallback_account_id

        logger.warning("Unable to resolve an IBKR Client Portal account id from gateway response.")
        return None

    def keepalive(self) -> dict[str, Any]:
        if self._is_disabled():
            return {"enabled": False, "status": "disabled"}

        payload = self._request("POST", "/tickle")
        if isinstance(payload, dict):
            return payload
        return {"enabled": True, "payload": payload}

    def get_positions(self) -> list[dict[str, Any]]:
        if self._is_disabled():
            return []

        account_id = self._resolve_account_id()
        if not account_id:
            return []

        payload = self._request("GET", f"/portfolio/{account_id}/positions/0")
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict) and isinstance(payload.get("positions"), list):
            return payload["positions"]
        return [payload] if isinstance(payload, dict) and payload else []

    def get_summary(self) -> dict[str, Any]:
        if self._is_disabled():
            return {}

        account_id = self._resolve_account_id()
        if not account_id:
            return {}

        payload = self._request("GET", f"/portfolio/{account_id}/summary")
        if isinstance(payload, dict):
            return payload
        return {"summary": payload}
