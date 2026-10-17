"""La web compilada: las direcciones de cada juego devuelven la página."""

import pytest
from fastapi.testclient import TestClient

from server.app import create_app

PAGE = "<!doctype html><title>mi-poker</title><div id=root></div>"


@pytest.fixture
def client(tmp_path):
    (tmp_path / "index.html").write_text(PAGE, encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log('hola')", encoding="utf-8")
    return TestClient(create_app(bot_delay=(0, 0), frontend_dist=tmp_path))


@pytest.mark.parametrize("path", ["/", "/poker", "/blackjack", "/prisma", "/una/ruta/cualquiera"])
def test_every_page_of_the_web_gets_the_app(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.text == PAGE


def test_files_are_served_as_they_are(client):
    response = client.get("/assets/app.js")
    assert response.status_code == 200 and "hola" in response.text


def test_missing_files_and_api_routes_are_not_the_app(client):
    assert client.get("/assets/no-existe.js").status_code == 404
    assert client.get("/api/no-existe").status_code == 404
    assert client.get("/api/juegos").status_code == 200  # la API de verdad sigue funcionando
