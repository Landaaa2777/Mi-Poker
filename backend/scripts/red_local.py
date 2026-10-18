"""Arranca el servidor para jugar con otras personas en la red de casa (la misma WiFi).

    python scripts/red_local.py          # en el puerto 8000
    python scripts/red_local.py 8080     # en otro puerto

Escucha en todas las direcciones del ordenador (0.0.0.0), no solo en él mismo,
y dice qué dirección hay que abrir en los otros dispositivos. La primera vez,
Windows pregunta si Python puede recibir conexiones: hay que permitirlo en
"redes privadas" (las de casa), no en las públicas.

Antes hay que compilar la web (`npm run build` en frontend), como para jugar solo.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def lan_address() -> str:
    """La dirección de este ordenador en la red de casa.

    Un socket UDP "conectado" solo elige por qué tarjeta de red saldría: no se
    envía nada por la red.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        except OSError:
            return "127.0.0.1"  # sin red: solo este ordenador


def main() -> None:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f"En este ordenador:                     http://localhost:{port}")
    print(f"En los demás dispositivos de tu WiFi:  http://{lan_address()}:{port}")
    print("Para parar el servidor: Ctrl+C")
    # Los mensajes del juego son cortos: no hace falta aceptar WebSocket enormes.
    uvicorn.run("server.app:app", host="0.0.0.0", port=port, ws_max_size=64 * 1024)


if __name__ == "__main__":
    main()
