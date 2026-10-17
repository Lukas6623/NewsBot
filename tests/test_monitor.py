import httpx
import pytest
from serverguard.services import website_monitor

@pytest.mark.asyncio
async def test_ping_http_error(monkeypatch):
    class Response:
        status_code = 503
        is_success = False
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url): return Response()
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: Client())
    result = await website_monitor.ping('https://serverguard.site')
    assert result['available'] is False and result['status_code'] == 503

@pytest.mark.asyncio
async def test_ping_timeout(monkeypatch):
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def get(self, url): raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: Client())
    result = await website_monitor.ping('https://serverguard.site')
    assert result['available'] is False and result['status_code'] is None
