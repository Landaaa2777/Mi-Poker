"""Cuentas por HTTP: registrarse, entrar, salir y saber quién soy.

    POST /api/register  {"username": "...", "password": "..."}   crea la cuenta y entra
    POST /api/login     {"username": "...", "password": "..."}   entra
    POST /api/logout                                             sale
    GET  /api/me                                                 la cuenta de esta sesión

Todas responden {"user": {"username": "..."} | null}, o {"message": "..."} con
un código de error. La sesión viaja en una cookie que los scripts de la página
no pueden leer; la contraseña no se guarda ni se devuelve nunca.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.datastructures import Headers

from accounts import SESSION_SECONDS, AccountError, AccountStore, Throttle, User, UsernameTaken

SESSION_COOKIE = "mi_poker_session"
WRONG_CREDENTIALS = "Usuario o contraseña incorrectos"

# Se llama al cerrar una sesión, con su token, para cortar sus conexiones abiertas.
OnLogout = Callable[[str], Awaitable[None]]


class Credentials(BaseModel):
    # Aquí solo se acota el tamaño; las reglas de verdad están en `accounts`.
    model_config = ConfigDict(extra="forbid", strict=True)
    username: str = Field(max_length=64)
    password: str = Field(max_length=256)


def same_origin(headers: Headers) -> bool:
    """¿Viene la petición de nuestra propia página?

    Los navegadores dicen en `Origin` qué página hace la petición. Si es otra,
    se rechaza: así una web ajena no puede actuar con la sesión del usuario.
    Los clientes que no son navegadores no mandan `Origin` y pasan.
    """
    origin = headers.get("origin")
    return origin is None or urlsplit(origin).netloc == headers.get("host")


def public_user(user: User | None) -> dict | None:
    """Lo que el cliente puede saber de una cuenta."""
    return {"username": user.username} if user else None


def account_routes(store: AccountStore, throttle: Throttle, on_logout: OnLogout) -> APIRouter:
    router = APIRouter(prefix="/api")

    def failure(status: int, message: str, **headers: str) -> JSONResponse:
        return JSONResponse({"message": message}, status_code=status, headers=headers)

    def signed_in(request: Request, user: User, status: int = 200) -> JSONResponse:
        response = JSONResponse({"user": public_user(user)}, status_code=status)
        response.set_cookie(
            SESSION_COOKIE,
            store.create_session(user),
            max_age=SESSION_SECONDS,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
        return response

    @router.post("/register")
    def register(request: Request, credentials: Credentials) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        try:
            user = store.register(credentials.username, credentials.password)
        except UsernameTaken as error:
            return failure(409, str(error))
        except AccountError as error:
            return failure(400, str(error))
        return signed_in(request, user, status=201)

    @router.post("/login")
    def login(request: Request, credentials: Credentials) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        client = request.client.host if request.client else ""
        key = f"{credentials.username.strip().lower()}|{client}"
        wait = throttle.wait_seconds(key)
        if wait:
            return failure(
                429, f"Demasiados intentos. Espera {wait} segundos.", **{"Retry-After": str(wait)}
            )
        user = store.authenticate(credentials.username, credentials.password)
        if user is None:
            throttle.fail(key)
            # El mismo mensaje exista o no la cuenta: no se dice cuál de los dos falló.
            return failure(401, WRONG_CREDENTIALS)
        throttle.reset(key)
        return signed_in(request, user)

    @router.post("/logout")
    async def logout(request: Request) -> JSONResponse:
        if not same_origin(request.headers):
            return failure(403, "Petición rechazada")
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            await asyncio.to_thread(store.delete_session, token)
            await on_logout(token)
        response = JSONResponse({"user": None})
        response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax")
        return response

    @router.get("/me")
    def me(request: Request) -> dict:
        return {"user": public_user(store.user_for_token(request.cookies.get(SESSION_COOKIE)))}

    return router
