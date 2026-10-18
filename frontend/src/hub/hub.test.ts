import { describe, expect, it } from "vitest";
import { cardState, fetchGames, menuOrder, playersLabel, type GameEntry } from "./hub";

function game(id: string, overrides: Partial<GameEntry> = {}): GameEntry {
  return {
    id,
    name: id,
    description: "",
    min_bots: 1,
    max_bots: 5,
    min_players: 2,
    max_players: 6,
    available: true,
    options: [],
    ...overrides,
  };
}

describe("playersLabel", () => {
  it("da el rango de jugadores en palabras", () => {
    expect(playersLabel(game("poker"))).toBe("2 a 6 jugadores");
    expect(playersLabel(game("blackjack", { min_players: 1, max_players: 5 }))).toBe("1 a 5 jugadores");
    expect(playersLabel(game("duelo", { min_players: 2, max_players: 2 }))).toBe("2 jugadores");
  });

  it("no dice nada de un juego sin mesa", () => {
    expect(playersLabel(game("puzle", { min_players: 1, max_players: 1 }))).toBeNull();
  });
});

describe("cardState", () => {
  const partidas = [{ game: "poker", partida_id: "x", in_progress: true }];

  it("ofrece continuar la partida que está a medias", () => {
    expect(cardState(game("poker"), partidas, true)).toBe("continue");
    expect(cardState(game("poker"), [{ ...partidas[0], in_progress: false }], true)).toBe("play");
    expect(cardState(game("blackjack"), partidas, true)).toBe("play");
  });

  it("deja en Próximamente lo que el servidor o la web aún no tienen", () => {
    expect(cardState(game("salas", { available: false }), [], true)).toBe("soon");
    expect(cardState(game("nuevo"), [], false)).toBe("soon");
  });
});

describe("menuOrder", () => {
  it("pone primero lo que se puede jugar, sin cambiar el orden del registro", () => {
    const games = [
      game("poker"),
      game("blackjack", { available: false }),
      game("prisma"),
      game("salas", { available: false }),
    ];
    const ids = menuOrder(games, (id) => id !== "prisma").map((entry) => entry.id);
    expect(ids).toEqual(["poker", "blackjack", "prisma", "salas"]);
    expect(menuOrder(games, () => true).map((entry) => entry.id)).toEqual([
      "poker",
      "prisma",
      "blackjack",
      "salas",
    ]);
  });
});

describe("fetchGames", () => {
  it("lee el registro del servidor", async () => {
    const fake = (async () =>
      new Response(JSON.stringify([game("poker")]), { status: 200 })) as unknown as typeof fetch;
    expect((await fetchGames(fake))[0].id).toBe("poker");
  });

  it("avisa si el servidor falla", async () => {
    const fake = (async () => new Response("", { status: 500 })) as unknown as typeof fetch;
    await expect(fetchGames(fake)).rejects.toThrow("lista de juegos");
  });
});
