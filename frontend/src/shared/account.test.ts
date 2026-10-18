import { describe, expect, it, vi } from "vitest";
import {
  checkCredentials,
  fetchProfile,
  login,
  logout,
  percent,
  refill,
  register,
  rememberSignedIn,
  signedInBefore,
} from "./account";

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
    expect(checkCredentials("login", "joker", PASSWORD)).toBeNull();
    expect(checkCredentials("login", "joker@ejemplo.com", PASSWORD)).toBeNull(); // o el correo
    expect(checkCredentials("login", "", PASSWORD)).not.toBeNull();
    expect(checkCredentials("login", "joker", "")).not.toBeNull();
    expect(checkCredentials("login", "   ", PASSWORD)).not.toBeNull();
    // Una cuenta antigua podría no cumplir las reglas de hoy: eso lo decide el servidor.
    expect(checkCredentials("login", "ab", "corta")).toBeNull();
  });

  it("al crear la cuenta basta con un usuario y una contraseña válidos", () => {
    expect(checkCredentials("register", "joker_99", PASSWORD)).toBeNull();
    expect(checkCredentials("register", "  joker  ", PASSWORD, "   ")).toBeNull();
    expect(checkCredentials("register", "joker", PASSWORD, " Joker@Ejemplo.com ")).toBeNull();
  });

  it.each(["ab", "x".repeat(17), "con espacio", "ñandú", "a@b.com"])(
    "rechaza el nombre de usuario %j",
    (username) => {
      expect(checkCredentials("register", username, PASSWORD)).toMatch(/usuario/);
    },
  );

  it("rechaza contraseñas cortas o larguísimas", () => {
    expect(checkCredentials("register", "joker", "corta12")).toMatch(/al menos 8/);
    expect(checkCredentials("register", "joker", "x".repeat(129))).toMatch(/128/);
  });

  it.each(["sin-arroba", "a@b", "@ejemplo.com", "a b@ejemplo.com", "x".repeat(250) + "@b.com"])(
    "rechaza el correo %j, que se puede dejar en blanco",
    (email) => {
      expect(checkCredentials("register", "joker", PASSWORD, email)).toMatch(/correo.*en blanco/);
    },
  );
});

describe("primera vez en este navegador", () => {
  it("recuerda que ya se entró alguna vez", () => {
    const data = new Map<string, string>();
    const storage = {
      getItem: (key: string) => data.get(key) ?? null,
      setItem: (key: string, value: string) => void data.set(key, value),
    };
    expect(signedInBefore(storage)).toBe(false);
    rememberSignedIn(storage);
    expect(signedInBefore(storage)).toBe(true);
  });

  it("sin almacenamiento, es como la primera vez", () => {
    expect(signedInBefore(null)).toBe(false);
    expect(() => rememberSignedIn(null)).not.toThrow();
  });
});

describe("percent", () => {
  it("redondea al entero más cercano y no divide entre cero", () => {
    expect(percent(1, 3)).toBe(33);
    expect(percent(2, 3)).toBe(67);
    expect(percent(5, 5)).toBe(100);
    expect(percent(0, 0)).toBe(0);
  });
});

describe("perfil", () => {
  const profile = {
    user: { username: "Joker", balance: 10000, member_since: 1760000000, email: null },
    stats: {
      total: { hands_played: 3, hands_won: 1, biggest_win: 40, best_hand: "Color", games_played: 1, games_won: 0 },
      levels: [],
    },
  };

  it("devuelve la cuenta y sus estadísticas", async () => {
    const fetcher = reply(200, profile);
    expect(await fetchProfile(fetcher)).toEqual({ ok: true, profile });
    expect(fetcher.mock.calls[0]).toEqual(["/api/profile", { credentials: "same-origin" }]);
  });

  it("sin sesión, da el motivo", async () => {
    const result = await fetchProfile(reply(401, { message: "Inicia sesión para ver tu perfil" }));
    expect(result).toEqual({ ok: false, message: "Inicia sesión para ver tu perfil" });
  });

  it("una respuesta incompleta no se da por buena", async () => {
    expect((await fetchProfile(reply(200, { user: profile.user }))).ok).toBe(false);
    expect((await fetchProfile(reply(200, {}))).ok).toBe(false);
  });
});

describe("recarga", () => {
  it("devuelve el saldo nuevo", async () => {
    const fetcher = reply(200, { balance: 10000 });
    expect(await refill(fetcher)).toEqual({ ok: true, balance: 10000 });
    expect(fetcher.mock.calls[0]).toEqual([
      "/api/refill",
      { method: "POST", credentials: "same-origin" },
    ]);
  });

  it("si el servidor la niega, da su motivo", async () => {
    const message = "La recarga gratis es para cuando te quedan menos de 100 fichas";
    expect(await refill(reply(400, { message }))).toEqual({ ok: false, message });
  });

  it("una respuesta sin saldo no se da por buena", async () => {
    expect((await refill(reply(200, {}))).ok).toBe(false);
  });
});

describe("peticiones de cuenta", () => {
  it("entrar envía usuario y contraseña y devuelve la cuenta", async () => {
    const fetcher = reply(200, { user: { username: "Joker", balance: 10000 } });
    expect(await login(" joker ", PASSWORD, fetcher)).toEqual({
      ok: true,
      user: { username: "Joker", balance: 10000 },
    });
    const { path, options, body } = sent(fetcher);
    expect(path).toBe("/api/login");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("same-origin");
    expect(body).toEqual({ username: "joker", password: PASSWORD });
  });

  it("crear la cuenta usa su propia ruta, con el correo si se dio", async () => {
    const fetcher = reply(201, { user: { username: "Joker", balance: 10000 } });
    expect((await register(" Joker ", PASSWORD, " joker@ejemplo.com ", fetcher)).ok).toBe(true);
    expect(sent(fetcher).path).toBe("/api/register");
    expect(sent(fetcher).body).toEqual({
      username: "Joker",
      password: PASSWORD,
      email: "joker@ejemplo.com",
    });
    const without = reply(201, { user: { username: "Joker", balance: 10000 } });
    await register("Joker", PASSWORD, "  ", without);
    expect(sent(without).body).toEqual({ username: "Joker", password: PASSWORD, email: null });
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
