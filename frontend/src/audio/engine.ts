// Motor de audio: un único contexto con dos canales (efectos y música), cada
// uno con su volumen, y un interruptor general para silenciarlo todo.

import { playEffect, type EffectName } from "./effects";
import { FileMusic, GeneratedMusic, createMusicBus, type MusicPlayer } from "./music";

// Pista opcional puesta por el usuario en `src/assets/audio/`. Vite resuelve
// esto al compilar: si el archivo no existe, la lista queda vacía y no se pide
// nada al servidor, así que nunca hay un error por un archivo que falta.
const musicFiles = import.meta.glob<string>("../assets/audio/music.{mp3,ogg,wav,m4a}", {
  eager: true,
  query: "?url",
  import: "default",
});
const MUSIC_FILE_URL: string | undefined = Object.values(musicFiles)[0];

export interface AudioLevels {
  music: number; // de 0 a 1
  effects: number; // de 0 a 1
  muted: boolean;
}

/** El oído no percibe el volumen de forma lineal: al cuadrado, el deslizador se siente uniforme. */
const loudness = (level: number) => level * level;

export class AudioEngine {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private effects: GainNode | null = null;
  private musicGain: GainNode | null = null;
  private music: MusicPlayer | null = null;
  private musicPlaying = false;
  private levels: AudioLevels = { music: 0, effects: 0, muted: false };
  private hidden = false;

  /**
   * Activa el audio. Hay que llamarlo dentro de un gesto del usuario (clic o
   * tecla): los navegadores no dejan sonar nada antes de la primera interacción.
   */
  unlock = (): void => {
    if (this.ctx === null) this.create();
    if (this.ctx?.state === "suspended") void this.ctx.resume();
    this.apply();
  };

  setLevels(levels: AudioLevels): void {
    this.levels = levels;
    this.apply();
  }

  /** Con la pestaña oculta no suena nada: ni efectos ni música. */
  setHidden(hidden: boolean): void {
    this.hidden = hidden;
    this.apply();
  }

  /** Hace sonar un efecto, con un retraso opcional en segundos. */
  play(name: EffectName, delay = 0): void {
    const { ctx, effects } = this;
    if (!ctx || !effects || ctx.state !== "running") return;
    if (this.hidden || this.levels.muted || this.levels.effects === 0) return;
    playEffect(ctx, effects, name, ctx.currentTime + 0.01 + delay);
  }

  private create(): void {
    const ctx = new AudioContext();
    const master = ctx.createGain();
    master.connect(ctx.destination);

    // Un compresor suave evita picos cuando coinciden varios efectos.
    const limiter = ctx.createDynamicsCompressor();
    limiter.threshold.value = -14;
    limiter.ratio.value = 4;
    limiter.connect(master);
    const effects = ctx.createGain();
    effects.gain.value = 0;
    effects.connect(limiter);

    const musicGain = ctx.createGain();
    musicGain.gain.value = 0;
    musicGain.connect(master);

    this.ctx = ctx;
    this.master = master;
    this.effects = effects;
    this.musicGain = musicGain;
    this.music = new GeneratedMusic(createMusicBus(ctx, musicGain));
    if (MUSIC_FILE_URL) void this.useMusicFile(MUSIC_FILE_URL);
  }

  /** Sustituye la música generada por la pista del usuario, si se puede leer. */
  private async useMusicFile(url: string): Promise<void> {
    const { ctx, musicGain } = this;
    if (!ctx || !musicGain) return;
    try {
      const data = await (await fetch(url)).arrayBuffer();
      const buffer = await ctx.decodeAudioData(data);
      this.music?.stop();
      this.music = new FileMusic(ctx, musicGain, buffer);
      if (this.musicPlaying) this.music.start();
    } catch {
      // Archivo ilegible o en un formato que el navegador no entiende: se queda la música generada.
    }
  }

  private apply(): void {
    const { ctx, master, effects, musicGain, music } = this;
    if (!ctx || !master || !effects || !musicGain || !music) return;
    const { muted } = this.levels;
    const wantMusic = !muted && !this.hidden && this.levels.music > 0;

    fade(ctx, master.gain, muted || this.hidden ? 0 : 1, 0.08);
    fade(ctx, effects.gain, loudness(this.levels.effects), 0.08);
    // La música entra y sale con un fundido largo, nunca de golpe.
    fade(ctx, musicGain.gain, wantMusic ? loudness(this.levels.music) : 0, wantMusic ? 1.2 : 0.4);

    if (wantMusic && !this.musicPlaying) music.start();
    if (!wantMusic && this.musicPlaying) music.stop();
    this.musicPlaying = wantMusic;
  }
}

/** Lleva un volumen a su nuevo valor poco a poco, para que no se oiga un chasquido. */
function fade(ctx: AudioContext, param: AudioParam, value: number, seconds: number): void {
  param.cancelScheduledValues(ctx.currentTime);
  param.setTargetAtTime(value, ctx.currentTime, seconds / 3);
}

export const audio = new AudioEngine();
