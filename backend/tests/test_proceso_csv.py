# backend/tests/test_proceso_csv.py

import pytest
import os
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.mark.asyncio
async def test_proceso_csv():
    # Transport especial para usar httpx con apps ASGI como FastAPI
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        path = os.path.join("tests", "data", "sample.csv")
        with open(path, "rb") as f:
            response = await ac.post(
                "/proceso-csv",
                files={"file": ("sample.csv", f, "text/csv")}
            )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "preview_antes" in data
    assert "resumen" in data
