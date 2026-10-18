"""Graba partidas reales de Prisma del servidor para los tests de su línea de tiempo.

    backend\\.venv\\Scripts\\python.exe frontend\\tools\\record_prisma.py

Juega varias partidas contra el servidor de verdad (sin esperas de los bots),
con decisiones al azar, y guarda los estados recibidos en
src/games/prisma/fixtures/sessions.json.

Para que el archivo no pese, el registro de cada ronda se guarda una sola vez:
dentro de una ronda solo crece, así que cada estado guarda cuántos sucesos
lleva (`event_count`) y el test lo rehace con el registro completo de su ronda.
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

OUTPUT = ROOT / "frontend" / "src" / "games" / "prisma" / "fixtures" / "sessions.json"
COLORS = ["panal", "halo", "cumbre", "astro"]

# (nombre, configuración, rondas)
SESSIONS = [
    ("tres_rivales", {"bots": 3, "difficulty": "easy"}, 1),
    ("duelo_a_puntos", {"bots": 1, "scoring": True, "target": 100, "difficulty": "medium"}, 3),
]
WANTED = {"deal", "play", "draw", "skip", "reverse", "round_over", "last"}


def choose(state: dict, rng: random.Random) -> dict:
    legal = state["legal"]
    if legal["choose_color"]:
        return {"type": "color", "color": rng.choice(COLORS)}
    if legal["challenge"]:
        return {"type": rng.choice(["challenge", "accept"])}
    if legal["catch"] and rng.random() < 0.7:
        return {"type": "catch"}
    if legal["play"]:
        card_id = rng.choice(legal["play"])
        card = next(card for card in state["hand"] if card["id"] == card_id)
        message = {"type": "play", "card": card_id, "declare": len(state["hand"]) == 2 and rng.random() < 0.6}
        if card["color"] is None:
            message["color"] = rng.choice(COLORS)
        return message
    return {"type": "pass"} if legal["pass"] else {"type": "draw"}


def record(config: dict, rounds: int, rng: random.Random) -> tuple[list[dict], set[str]]:
    app = create_app(bot_delay=(0, 0), serve_frontend=False)
    client = TestClient(app)
    guest = "grabadora-de-prisma"
    partida = client.post("/api/partidas", json={"game": "prisma", "guest_id": guest}).json()
    states: list[dict] = []
    seen: set[str] = set()
    played = 1
    with client.websocket_connect(f"/ws/prisma/{partida['partida_id']}?guest_id={guest}") as socket:
        socket.receive_json()  # hello
        socket.send_json({"type": "new_game", "config": config})
        for _ in range(5000):
            message = socket.receive_json()
            if message["type"] == "error":
                continue  # una intención que llegó tarde: se ignora y se sigue
            state = message["state"]
            states.append(state)
            seen |= {event["kind"] for event in state["events"]}
            legal = state["legal"]
            if state["phase"] == "round_over":
                if state["game_over"] or played >= rounds:
                    return states, seen
                played += 1
                socket.send_json({"type": "next_round"})
            elif legal["play"] or legal["draw"] or legal["pass"] or legal["choose_color"] or legal["challenge"]:
                socket.send_json(choose(state, rng))
    return states, seen


def compact(states: list[dict]) -> dict:
    """Quita de cada estado su registro y guarda el de cada ronda una sola vez."""
    rounds: dict[str, list] = {}
    slim = []
    for state in states:
        events = state["events"]
        key = str(state["round_number"])
        full = rounds.setdefault(key, events)
        if len(events) > len(full):
            assert events[: len(full)] == full, "el registro de una ronda no solo crece"
            rounds[key] = full = events
        assert full[: len(events)] == events
        slim.append({**{k: v for k, v in state.items() if k != "events"}, "event_count": len(events)})
    return {"rounds": rounds, "states": slim}


def main() -> None:
    for attempt in range(1, 30):
        rng = random.Random(attempt)
        sessions, seen = [], set()
        for name, config, rounds in SESSIONS:
            states, kinds = record(config, rounds, rng)
            seen |= kinds
            sessions.append({"name": name, "config": config, **compact(states)})
        if WANTED <= seen:
            break
    else:
        raise SystemExit(f"No salieron todos los casos: faltan {sorted(WANTED - seen)}")
    for session in sessions:
        print(f"{session['name']}: {len(session['states'])} estados")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(sessions, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(text + "\n", encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(text) / 1024:.0f} KB, casos: {sorted(seen)}")


if __name__ == "__main__":
    main()
