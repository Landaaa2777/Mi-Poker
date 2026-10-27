import { describe, expect, it, vi } from "vitest";
import { DEFAULT_SETTINGS, SettingsStore, parseSettings } from "./settings";

function fakeStorage(initial: Record<string, string> = {}) {
  const data = new Map(Object.entries(initial));
  return {
    data,
    getItem: (key: string) => data.get(key) ?? null,
    setItem: (key: string, value: string) => void data.set(key, value),
  };
}

describe("parseSettings", () => {
  it("usa los valores por defecto si no hay nada guardado", () => {
    expect(parseSettings(null)).toEqual(DEFAULT_SETTINGS);
    expect(DEFAULT_SETTINGS.animations).toBeNull();
    expect(DEFAULT_SETTINGS.view).toBeNull();
    expect(DEFAULT_SETTINGS.muted).toBe(false);
  });

  it("la música suena más baja que los efectos por defecto", () => {
    expect(DEFAULT_SETTINGS.musicVolume).toBeGreaterThan(0);
    expect(DEFAULT_SETTINGS.musicVolume).toBeLessThan(DEFAULT_SETTINGS.effectsVolume);
  });

  it("lee lo guardado", () => {
    const saved = { animations: false, view: "3d", musicVolume: 0.1, effectsVolume: 1, muted: true };
    expect(parseSettings(JSON.stringify(saved))).toEqual(saved);
    expect(parseSettings('{"animations":true}').animations).toBe(true);
    expect(parseSettings('{"musicVolume":0}').musicVolume).toBe(0);
    expect(parseSettings('{"view":"2d"}').view).toBe("2d");
  });

  it("solo acepta las vistas 2d y 3d; lo demás cuenta como no elegido", () => {
    for (const view of ['"4d"', '"3D"', "true", "1", "null"]) {
      expect(parseSettings(`{"view":${view}}`).view).toBeNull();
    }
  });

  it("completa con los valores por defecto lo que falte", () => {
    expect(parseSettings('{"animations":false}')).toEqual({ ...DEFAULT_SETTINGS, animations: false });
  });

  it("ignora datos corruptos o de otro tipo", () => {
    for (const text of ["no es JSON", "null", "42", '"texto"', "[]", '{"animations":"sí"}']) {
      expect(parseSettings(text)).toEqual(DEFAULT_SETTINGS);
    }
  });

  it("descarta volúmenes fuera de rango y campos desconocidos", () => {
    const text = '{"musicVolume":3,"effectsVolume":-1,"muted":"no","otra":1}';
    expect(parseSettings(text)).toEqual(DEFAULT_SETTINGS);
    expect(parseSettings('{"musicVolume":"0.5"}').musicVolume).toBe(DEFAULT_SETTINGS.musicVolume);
    expect(parseSettings('{"effectsVolume":null}').effectsVolume).toBe(DEFAULT_SETTINGS.effectsVolume);
  });
});

describe("SettingsStore", () => {
  it("guarda los cambios y avisa a quien escucha", () => {
    const storage = fakeStorage();
    const store = new SettingsStore(storage);
    const listener = vi.fn();
    const unsubscribe = store.subscribe(listener);

    store.update({ animations: false });
    store.update({ musicVolume: 0.2, muted: true });
    const expected = { ...DEFAULT_SETTINGS, animations: false, musicVolume: 0.2, muted: true };
    expect(store.get()).toEqual(expected);
    expect(listener).toHaveBeenCalledTimes(2);
    expect(new SettingsStore(storage).get()).toEqual(expected);

    unsubscribe();
    store.update({ animations: true });
    expect(listener).toHaveBeenCalledTimes(2);
  });

  it("funciona aunque el navegador no deje guardar", () => {
    const broken = {
      getItem: () => {
        throw new Error("bloqueado");
      },
      setItem: () => {
        throw new Error("bloqueado");
      },
    };
    for (const storage of [null, broken]) {
      const store = new SettingsStore(storage);
      expect(store.get()).toEqual(DEFAULT_SETTINGS);
      store.update({ effectsVolume: 0.25 });
      expect(store.get().effectsVolume).toBe(0.25);
    }
  });
});
