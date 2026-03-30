from unittest.mock import MagicMock

from app.services.ibkr_portal_service import IBKRPortalService


def make_response(payload, *, content_type="application/json"):
    response = MagicMock()
    response.content = b"{}"
    response.headers = {"Content-Type": content_type}
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    response.text = str(payload)
    return response


def test_get_positions_returns_empty_when_disabled():
    service = IBKRPortalService(enabled=False)

    assert service.get_positions() == []


def test_keepalive_posts_to_tickle():
    session = MagicMock()
    session.request.return_value = make_response({"session": "ok"})
    service = IBKRPortalService(enabled=True, session=session)

    payload = service.keepalive()

    assert payload == {"session": "ok"}
    session.request.assert_called_once()
    call = session.request.call_args.kwargs
    assert call["method"] == "POST"
    assert call["url"].endswith("/tickle")


def test_get_positions_resolves_account_and_fetches_positions():
    session = MagicMock()
    session.request.side_effect = [
        make_response([{"id": "DU123456"}]),
        make_response([{"ticker": "AAPL", "position": 100}]),
    ]
    service = IBKRPortalService(enabled=True, session=session)

    payload = service.get_positions()

    assert payload == [{"ticker": "AAPL", "position": 100}]
    assert service.account_id == "DU123456"
    assert session.request.call_args_list[0].kwargs["url"].endswith("/portfolio/accounts")
    assert session.request.call_args_list[1].kwargs["url"].endswith(
        "/portfolio/DU123456/positions/0"
    )


def test_get_summary_uses_configured_account_id():
    session = MagicMock()
    session.request.return_value = make_response({"netliquidation": {"amount": 12345}})
    service = IBKRPortalService(
        enabled=True,
        account_id="DU777777",
        session=session,
    )

    payload = service.get_summary()

    assert payload == {"netliquidation": {"amount": 12345}}
    session.request.assert_called_once()
    assert session.request.call_args.kwargs["url"].endswith(
        "/portfolio/DU777777/summary"
    )
