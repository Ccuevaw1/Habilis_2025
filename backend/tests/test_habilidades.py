import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_obtener_habilidades():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/habilidades/?carrera=Ingeniería de Sistemas")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)  

    if len(data) > 0:
        for item in data:
            assert "career" in item
            assert "title" in item
            assert "company" in item
