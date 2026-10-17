"""Graba partidas reales del servidor para los tests de la línea de tiempo.

Juega contra el servidor de verdad (sin esperas de los bots) y guarda, tal
cual, todos los estados que recibiría el navegador. No modifica el backend.

    backend\\.venv\\Scripts\\python.exe frontend\\tools\\record_fixtures.py

Cada sesión se repite hasta que contiene los casos difíciles que le tocan
(botes laterales, manos que llegan enteras en el primer mensaje, reinicios...).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from server.app import create_app  # noqa: E402

OUTPUT = ROOT / "frontend" / "src" / "games" / "poker" / "timeline" / "fixtures" / "sessions.json"
MAX_ATTEMPTS = 400

# nombre, configuración, manos, probabilidades del humano (all-in, subir, retirarse), casos exigidos
SESSIONS = [
    (
        "mesa de seis",
        dict(bots=5, difficulty="medium", starting_stack=1000, small_blind=5, big_blind=10),
        4,
        (0.02, 0.15, 0.35),
        {"human_fold", "fold_win", "showdown"},
    ),
    (
        "tres con pocas fichas",
        dict(bots=2, difficulty="hard", starting_stack=200, small_blind=10, big_blind=20),
        6,
        (0.25, 0.15, 0.10),
        {"side_pots", "burst", "showdown"},
    ),
    (
        "mano a mano corto",
        dict(bots=1, difficulty="easy", starting_stack=30, small_blind=10, big_blind=20),
        8,
        (0.30, 0.10, 0.10),
        {"complete_on_arrival", "restart_same_number", "refund"},
    ),
]


def choose(legal: dict, odds: tuple[float, float, float], rng: random.Random) -> dict:
    all_in, raise_, fold = odds
    roll = rng.random()
    if legal["can_raise"] and roll < all_in:
        return {"type": "action", "action": "all_in", "amount": 0}
    if legal["can_raise"] and roll < all_in + raise_:
        low, high = legal["min_raise_to"], legal["max_raise_to"]
        return {"type": "action", "action": "raise", "amount": rng.randint(low, min(high, low * 3))}
    if legal["call_amount"] > 0 and roll < all_in + raise_ + fold:
        return {"type": "action", "action": "fold", "amount": 0}
    return {"type": "action", "action": "call", "amount": 0}


def record(config: dict, hands: int, odds: tuple[float, float, float], rng: random.Random):
    """Juega `hands` manos y devuelve los estados recibidos y los casos que aparecieron."""
    app = create_app(bot_delay=(0, 0), simulations=30, serve_frontend=False)
    states: list[dict] = []
    tags: set[str] = set()
    played = 0
    client = TestClient(app)
    guest = "grabadora-de-partidas"
    partida = client.post("/api/partidas", json={"game": "poker", "guest_id": guest}).json()
    with client.websocket_connect(f"/ws/poker/{partida['partida_id']}?guest_id={guest}") as socket:
        socket.receive_json()  # hello
        socket.send_json({"type": "new_game", "config": config})
        while True:
            message = socket.receive_json()
            assert message["type"] == "state", message
            state = message["state"]
            previous = states[-1] if states else None
            states.append(state)

            events = state["events"]
            continues = (
                previous is not None
                and previous["hand_number"] == state["hand_number"]
                and events[: len(previous["events"])] == previous["events"]
                and len(events) >= len(previous["events"])
            )
            new = events[len(previous["events"]) :] if continues else events
            if not continues:
                played += 1
                if previous is not None and previous["hand_number"] == state["hand_number"]:
                    tags.add("restart_same_number")
                if not state["hand_in_progress"]:
                    tags.add("complete_on_arrival")
            if continues and len(new) >= 6:
                tags.add("burst")
            for event in new:
                if event["kind"] == "refund":
                    tags.add("refund")
                if event["kind"] == "action" and event["seat"] == 0 and event["action"] == "fold":
                    if state["hand_in_progress"]:
                        tags.add("human_fold")
            result = state["result"]
            if result is not None:
                tags.add("showdown" if result["showdown"] else "fold_win")
                if len(result["awards"]) > 1:
                    tags.add("side_pots")

            if state["hand_in_progress"]:
                if state["to_act_seat"] == 0:
                    socket.send_json(choose(state["legal_actions"], odds, rng))
            elif played >= hands:
                return states, tags
            elif state["game_over"] or state["human_out"]:
                socket.send_json({"type": "restart"})
            else:
                socket.send_json({"type": "next_hand"})


def main() -> None:
    rng = random.Random(2026)
    sessions = []
    for name, config, hands, odds, required in SESSIONS:
        for attempt in range(1, MAX_ATTEMPTS + 1):
            states, tags = record(config, hands, odds, rng)
            if required <= tags:
                break
        else:
            raise SystemExit(f"No salió una sesión '{name}' con {sorted(required)}")
        print(f"{name}: {len(states)} estados, intento {attempt}, casos: {sorted(tags)}")
        sessions.append({"name": name, "config": config, "cases": sorted(tags), "states": states})

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(sessions, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(text + "\n", encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(text) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
