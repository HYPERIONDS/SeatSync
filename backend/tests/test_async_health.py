import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


def test_health_with_httpx_async_client():
    async def request():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "ok"}

    asyncio.run(request())
