import { describe, expect, it, vi } from "vitest";
import type { GameOption } from "../shared/options";
import {
  CODE_ALPHABET,
  createSala,
  describeOptions,
  fetchMySala,
  joinSala,
  normalizeCode,
  onlyHere,
  salaLink,
  salaSocketUrl,
} from "./salas";
import { secondsLeft } from "../shared/room";

function reply(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

describe("normalizeCode", () => {
  it("acepta el código escrito a mano", () => {
    expect(normalizeCode(" k7p-2qx ")).toBe("K7P2QX");
    expect(normalizeCode("K7P 2QX")).toBe("K7P2QX");
  });

  it.each(["K7P2Q", "K7P2QXX", "K7P2Q0", "K7P2QI", "", "../../x"])("rechaza %j", (text) => {
    expect(normalizeCode(text)).toBeNull();
  });

  it("usa las mismas letras que el servidor: nada que se confunda", () => {
    expect(CODE_ALPHABET).not.toMatch(/[01OIL]/);
  });
});

describe("enlaces", () => {
  it("el de invitar usa la dirección por la que se ha entrado", () => {
    expect(salaLink("K7P2QX", "https://abc.trycloudflare.com")).toBe(
      "https://abc.trycloudflare.com/sala/K7P2QX",
    );
  });

  it("sabe cuándo el enlace solo sirve en este ordenador", () => {
    expect(onlyHere("localhost")).toBe(true);
    expect(onlyHere("127.0.0.1")).toBe(true);
    expect(onlyHere("192.168.1.20")).toBe(false);
    expect(onlyHere("abc.trycloudflare.com")).toBe(false);
  });

  it("el WebSocket va cifrado si la página lo está", () => {
    expect(salaSocketUrl("K7P2QX", { protocol: "https:", host: "x.example" })).toBe("wss://x.example/ws/sala/K7P2QX");
    expect(salaSocketUrl("K7P2QX", { protocol: "http:", host: "192.168.1.20:8000" })).toBe(
      "ws://192.168.1.20:8000/ws/sala/K7P2QX",
    );
  });
});

describe("secondsLeft", () => {
  it("cuenta hacia atrás desde que llegó, sin bajar de cero", () => {
    const timer = { seat: 1, left: 29.4, total: 30 };
    expect(secondsLeft(timer, 0)).toBe(30);
    expect(secondsLeft(timer, 10)).toBe(20);
    expect(secondsLeft(timer, 40)).toBe(0);
  });
});

describe("describeOptions", () => {
  const fields: GameOption[] = [
    { key: "bots", type: "number", label: "Bots", default: 0, min: 0, max: 5, step: 1 },
    {
      key: "difficulty",
      type: "choice",
      label: "Dificultad",
      default: "medium",
      choices: [
        { value: "easy", label: "Fácil" },
        { value: "medium", label: "Medio" },
      ],
    },
    { key: "surrender", type: "toggle", label: "Rendición", default: false },
    { key: "starting_stack", type: "number", label: "Fichas iniciales", default: 1000, min: 1, max: null, step: 1 },
  ];

  it("dice cada opción en palabras", () => {
    expect(describeOptions(fields, { bots: 2, difficulty: "easy", surrender: true, starting_stack: 10000 })).toEqual([
      "Bots: 2",
      "Dificultad: Fácil",
      "Rendición: sí",
      "Fichas iniciales: 10.000",
    ]);
  });

  it("lo que falta, con su valor por defecto", () => {
    expect(describeOptions(fields, {})).toContain("Dificultad: Medio");
  });
});

describe("peticiones", () => {
  it("crear una sala devuelve su código", async () => {
    const fetcher = reply(201, { code: "K7P2QX", game: "poker", status: "waiting" });
    expect(await createSala("poker", fetcher)).toEqual({
      ok: true,
      sala: { code: "K7P2QX", game: "poker", status: "waiting" },
    });
    const [path, options] = fetcher.mock.calls[0] as unknown as [string, RequestInit];
    expect(path).toBe("/api/salas");
    expect(JSON.parse(options.body as string)).toEqual({ game: "poker" });
    expect(options.credentials).toBe("same-origin");
  });

  it("entrar con un código que no existe da el motivo del servidor", async () => {
    const result = await joinSala("ZZZZZZ", reply(404, { message: "No hay ninguna sala con ese código" }));
    expect(result).toEqual({ ok: false, message: "No hay ninguna sala con ese código" });
  });

  it("sin conexión, lo dice", async () => {
    const offline = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    expect((await joinSala("K7P2QX", offline)).ok).toBe(false);
  });

  it("mi sala, o ninguna", async () => {
    const mine = { code: "K7P2QX", game: "prisma", status: "playing" };
    expect(await fetchMySala(reply(200, { sala: mine }))).toEqual(mine);
    expect(await fetchMySala(reply(200, { sala: null }))).toBeNull();
    expect(await fetchMySala(reply(500, {}))).toBeNull();
  });
});
