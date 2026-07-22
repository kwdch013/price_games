import httpx
import pytest
from _pytest.outcomes import Skipped

from tests.upstream_probe import skip_if_unreachable


def _mock_client(monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport) -> None:
	original_client = httpx.Client

	def client(*args: object, **kwargs: object) -> httpx.Client:
		return original_client(transport=handler, **kwargs)

	monkeypatch.setattr(httpx, "Client", client)


@pytest.mark.parametrize("exception_type", [httpx.ConnectError, httpx.ConnectTimeout])
def test_接続不能ならモジュールをスキップする(
	monkeypatch: pytest.MonkeyPatch,
	exception_type: type[httpx.ConnectError] | type[httpx.ConnectTimeout],
) -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		raise exception_type("接続不能", request=request)

	_mock_client(monkeypatch, httpx.MockTransport(handler))

	with pytest.raises(Skipped):
		skip_if_unreachable("https://example.com", {"q": "game"}, "Example")


@pytest.mark.parametrize("exception_type", [httpx.ReadTimeout, httpx.RemoteProtocolError])
def test_接続後の通信障害ではスキップしない(
	monkeypatch: pytest.MonkeyPatch,
	exception_type: type[httpx.ReadTimeout] | type[httpx.RemoteProtocolError],
) -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		raise exception_type("通信障害", request=request)

	_mock_client(monkeypatch, httpx.MockTransport(handler))

	with pytest.raises(exception_type):
		skip_if_unreachable("https://example.com", {"q": "game"}, "Example")


@pytest.mark.parametrize("status_code", [400, 404, 500, 503])
def test_HTTPエラー応答ではスキップしない(
	monkeypatch: pytest.MonkeyPatch,
	status_code: int,
) -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(status_code, request=request)

	_mock_client(monkeypatch, httpx.MockTransport(handler))

	skip_if_unreachable("https://example.com", {"q": "game"}, "Example")
