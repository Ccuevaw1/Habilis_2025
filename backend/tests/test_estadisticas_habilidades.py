import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_estadisticas_habilidades_valida():
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/estadisticas/habilidades", params={"carrera": "Ingeniería de Sistemas"})

    assert response.status_code == 200
    data = response.json()

    # Verifica estructura principal
    assert "carrera" in data
    assert "total_ofertas" in data
    assert "habilidades_tecnicas" in data
    assert "habilidades_blandas" in data

    assert isinstance(data["carrera"], str)
    assert isinstance(data["total_ofertas"], int)
    assert isinstance(data["habilidades_tecnicas"], list)
    assert isinstance(data["habilidades_blandas"], list)

    # Verifica estructura de cada habilidad
    if data["habilidades_tecnicas"]:
        habilidad = data["habilidades_tecnicas"][0]
        assert "nombre" in habilidad
        assert "frecuencia" in habilidad
        assert isinstance(habilidad["nombre"], str)
        assert isinstance(habilidad["frecuencia"], int)

    if data["habilidades_blandas"]:
        habilidad = data["habilidades_blandas"][0]
        assert "nombre" in habilidad
        assert "frecuencia" in habilidad
        assert isinstance(habilidad["nombre"], str)
        assert isinstance(habilidad["frecuencia"], int)
