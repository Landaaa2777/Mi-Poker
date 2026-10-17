"""Registro de juegos: lo que ve el menú principal en GET /api/juegos."""

from typing import Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from games.poker.protocol import TableConfig
from games.registry import REGISTRY, find_game
from server.app import create_app
from server.options import describe_options


@pytest.fixture
def client():
    return TestClient(create_app(bot_delay=(0, 0), simulations=30, serve_frontend=False))


def test_every_game_has_a_unique_id_name_and_description():
    ids = [game.id for game in REGISTRY]
    assert len(ids) == len(set(ids))
    for game in REGISTRY:
        assert game.id.isascii() and game.id.islower() and " " not in game.id
        assert game.name and game.description
        assert 0 <= game.min_bots <= game.max_bots


def test_poker_is_registered_and_playable():
    poker = find_game("poker")
    assert poker is not None and poker.available
    assert (poker.min_bots, poker.max_bots) == (1, 5)
    assert poker.players == (2, 6)
    assert find_game("no-existe") is None


def test_the_menu_reads_the_registry(client):
    games = client.get("/api/juegos").json()
    assert [game["id"] for game in games] == [game.id for game in REGISTRY]
    poker = games[0]
    assert poker["id"] == "poker" and poker["available"]
    assert poker["min_players"] == 2 and poker["max_players"] == 6
    # Las tarjetas "Próximamente" también vienen del registro.
    soon = {game["id"] for game in games if not game["available"]}
    assert {"minijuegos", "salas"} <= soon


def test_poker_options_are_described_for_the_panel(client):
    poker = client.get("/api/juegos").json()[0]
    options = {option["key"]: option for option in poker["options"]}
    assert list(options) == ["bots", "difficulty", "starting_stack", "small_blind", "big_blind"]
    assert options["bots"] == {
        "key": "bots", "label": "Bots", "default": 3, "type": "number", "min": 1, "max": 5, "step": 1
    }
    levels = options["difficulty"]
    assert levels["type"] == "choice" and levels["default"] == "medium"
    assert [choice["label"] for choice in levels["choices"]] == ["Fácil", "Medio", "Difícil", "Experto"]
    assert options["starting_stack"]["presets"] == [500, 1000, 2000, 5000]
    assert "player_name" not in options  # el nombre no se elige en el panel


def test_the_described_defaults_are_the_real_ones():
    defaults = TableConfig().model_dump()
    for option in describe_options(TableConfig):
        assert option["default"] == defaults[option["key"]]


def test_options_of_every_kind():
    class Example(BaseModel):
        count: int = Field(2, ge=0, le=10, multiple_of=2, title="Cuántos")
        mode: Literal["a", "b"] = Field("a", title="Modo")
        fast: bool = Field(False, title="Rápido", description="Sin esperas")
        note: str = "texto libre: no va en el panel"

    described = describe_options(Example)
    assert described == [
        {"key": "count", "label": "Cuántos", "default": 2, "type": "number", "min": 0, "max": 10, "step": 2},
        {
            "key": "mode",
            "label": "Modo",
            "default": "a",
            "type": "choice",
            "choices": [{"value": "a", "label": "a"}, {"value": "b", "label": "b"}],
        },
        {"key": "fast", "label": "Rápido", "default": False, "help": "Sin esperas", "type": "toggle"},
    ]
