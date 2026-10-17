import time
import httpx

async def ping(url: str, timeout: float = 10.0) -> dict:
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
            response = await client.get(url)
        return {"available": response.is_success, "status_code": response.status_code, "elapsed_ms": round((time.monotonic() - started) * 1000)}
    except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError):
        return {"available": False, "status_code": None, "elapsed_ms": round((time.monotonic() - started) * 1000)}
