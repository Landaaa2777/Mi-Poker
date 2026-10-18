"""Graba partidas reales de blackjack del servidor para los tests de su línea de tiempo.

    backend\\.venv\\Scripts\\python.exe frontend\\tools\\record_blackjack.py

Juega varias sesiones contra el servidor de verdad (sin esperas de los bots),
con decisiones al azar, y guarda todos los estados recibidos en
src/games/blackjack/fixtures/sessions.json. Con semilla fija para las
decisiones del humano; el reparto es del servidor y cambia cada vez.
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

OUTPUT = ROOT / "frontend" / "src" / "games" / "blackjack" / "fixtures" / "sessions.json"

# (nombre, configuración, rondas)
SESSIONS = [
    ("solo", {"bots": 0, "starting_stack": 2000}, 10),
    ("mesa_llena", {"bots": 4, "starting_stack": 3000, "difficulty": "easy"}, 5),
    ("rendicion_h17", {"bots": 2, "surrender": True, "dealer_hits_soft_17": True}, 7),
]
WANTED = {"split", "double", "insurance", "settle", "reveal"}


def choose(state: dict, rng: random.Random) -> dict:
    legal = state["legal_actions"]
    weights = {"hit": 3, "stand": 3, "double": 2, "split": 5, "surrender": 1}
    action = rng.choices(legal, [weights[name] for name in legal])[0]
    return {"type": "action", "action": action}


def record(config: dict, rounds: int, rng: random.Random) -> tuple[list[dict], set[str]]:
    app = create_app(bot_delay=(0, 0), serve_frontend=False, require_account=False)
    client = TestClient(app)
    guest = "grabadora-de-blackjack"
    partida = client.post("/api/partidas", json={"game": "blackjack", "guest_id": guest}).json()
    states: list[dict] = []
    seen: set[str] = set()
    with client.websocket_connect(f"/ws/blackjack/{partida['partida_id']}?guest_id={guest}") as socket:
        socket.receive_json()  # hello
        socket.send_json({"type": "new_game", "config": config})
        played = 0
        while True:
            message = socket.receive_json()
            assert message["type"] == "state", message
            state = message["state"]
            states.append(state)
            for event in state["events"]:
                seen.add(event["kind"])
                if event["kind"] == "action":
                    seen.add(event["action"])
            if state["insurance_offered"]:
                socket.send_json({"type": "insurance", "take": rng.random() < 0.5})
            elif state["legal_actions"]:
                socket.send_json(choose(state, rng))
            elif state["phase"] in ("betting", "complete"):
                if state["human_out"] or played >= rounds:
                    return states, seen
                played += 1
                rules = state["rules"]
                bet = rng.choice([rules["min_bet"], rules["min_bet"] * 2, rules["min_bet"] * 5])
                socket.send_json({"type": "bet", "amount": min(bet, rules["max_bet"])})


def main() -> None:
    rng = random.Random(2026)
    sessions = []
    seen: set[str] = set()
    for name, config, rounds in SESSIONS:
        states, kinds = record(config, rounds, rng)
        seen |= kinds
        print(f"{name}: {len(states)} estados, sucesos: {sorted(kinds)}")
        sessions.append({"name": name, "config": config, "states": states})
    missing = WANTED - seen
    if missing:
        raise SystemExit(f"Faltan casos en las grabaciones: {sorted(missing)}. Vuelve a lanzarlo.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(sessions, ensure_ascii=False, separators=(",", ":"))
    OUTPUT.write_text(text + "\n", encoding="utf-8")
    print(f"{OUTPUT.relative_to(ROOT)}: {len(text) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
