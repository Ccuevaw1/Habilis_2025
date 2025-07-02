# backend/tests/test_main.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Backend is ready"

def test_estado_csv_procesado():
    response = client.get("/estado-csv-procesado")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
