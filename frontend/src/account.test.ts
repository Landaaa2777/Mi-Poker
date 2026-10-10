import { describe, expect, it, vi } from "vitest";
import { checkCredentials, login, logout, register } from "./account";

const PASSWORD = "una clave de prueba";

function reply(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

/** A dónde se envió la petición y con qué. */
function sent(fetcher: ReturnType<typeof vi.fn>) {
  const [path, options] = fetcher.mock.calls[0] as [string, RequestInit];
  return { path, options, body: JSON.parse(options.body as string) };
}

describe("checkCredentials", () => {
  it("para entrar solo pide que no falte nada", () => {
    expect(checkCredentials("login", "joker", PASSWORD, "")).toBeNull();
    expect(checkCredentials("login", "", PASSWORD, "")).not.toBeNull();
    expect(checkCredentials("login", "joker", "", "")).not.toBeNull();
    expect(checkCredentials("login", "   ", PASSWORD, "")).not.toBeNull();
    // Una cuenta antigua podría no cumplir las reglas de hoy: eso lo decide el servidor.
    expect(checkCredentials("login", "ab", "corta", "")).toBeNull();
  });

  it("al crear la cuenta acepta un usuario y una contraseña válidos", () => {
    expect(checkCredentials("register", "joker_99", PASSWORD, PASSWORD)).toBeNull();
    expect(checkCredentials("register", "  joker  ", PASSWORD, PASSWORD)).toBeNull();
  });

  it.each(["ab", "x".repeat(17), "con espacio", "ñandú", "a@b.com"])(
    "rechaza el nombre de usuario %j",
    (username) => {
      expect(checkCredentials("register", username, PASSWORD, PASSWORD)).toMatch(/usuario/);
    },
  );

  it("rechaza contraseñas cortas, larguísimas o que no coinciden", () => {
    expect(checkCredentials("register", "joker", "corta12", "corta12")).toMatch(/al menos 8/);
    const huge = "x".repeat(129);
    expect(checkCredentials("register", "joker", huge, huge)).toMatch(/128/);
    expect(checkCredentials("register", "joker", PASSWORD, PASSWORD + "!")).toMatch(/no coinciden/);
  });
});

describe("peticiones de cuenta", () => {
  it("entrar envía usuario y contraseña y devuelve la cuenta", async () => {
    const fetcher = reply(200, { user: { username: "Joker" } });
    expect(await login(" joker ", PASSWORD, fetcher)).toEqual({
      ok: true,
      user: { username: "Joker" },
    });
    const { path, options, body } = sent(fetcher);
    expect(path).toBe("/api/login");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("same-origin");
    expect(body).toEqual({ username: "joker", password: PASSWORD });
  });

  it("crear la cuenta usa su propia ruta", async () => {
    const fetcher = reply(201, { user: { username: "Joker" } });
    expect((await register("Joker", PASSWORD, fetcher)).ok).toBe(true);
    expect(sent(fetcher).path).toBe("/api/register");
  });

  it("salir deja la cuenta en nada", async () => {
    expect(await logout(reply(200, { user: null }))).toEqual({ ok: true, user: null });
  });

  it("muestra el motivo que da el servidor", async () => {
    const wrong = reply(401, { message: "Usuario o contraseña incorrectos" });
    expect(await login("joker", "otra", wrong)).toEqual({
      ok: false,
      message: "Usuario o contraseña incorrectos",
    });
  });

  it("si la respuesta no se entiende, da un mensaje genérico", async () => {
    const broken = vi.fn(async () => new Response("<html>error</html>", { status: 500 }));
    const result = await login("joker", PASSWORD, broken);
    expect(result).toEqual({ ok: false, message: "No se pudo completar. Inténtalo otra vez." });
    const odd = await login("joker", PASSWORD, reply(422, { detail: [{ msg: "x" }] }));
    expect(odd.ok).toBe(false);
  });

  it("si no hay conexión, lo dice", async () => {
    const offline = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const result = await login("joker", PASSWORD, offline);
    expect(result.ok).toBe(false);
    expect(result).toMatchObject({ message: expect.stringMatching(/conexión/) });
  });
});
