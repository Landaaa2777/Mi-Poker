"""Los juegos de la plataforma. Cada uno vive en su carpeta, como un módulo enchufable:

    games/<juego>/engine/     las reglas, en Python puro (sin FastAPI)
    games/<juego>/bots/       los bots, que solo ven la información pública
    games/<juego>/session.py  la partida en el servidor
    games/<juego>/protocol.py los mensajes que entiende
    games/<juego>/info.py     su ficha para el registro
    games/<juego>/tests/      sus tests

La lista de juegos que ve el menú está en `games/registry.py`.
"""
