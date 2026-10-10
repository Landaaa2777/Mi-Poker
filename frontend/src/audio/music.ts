// Música de fondo. Por defecto se genera con la Web Audio API: acordes largos y
// notas sueltas, tranquila y sin derechos de autor. Como se compone sobre la
// marcha no tiene punto de bucle, así que nunca se nota un corte.
//
// Si existe un archivo `src/assets/audio/music.*`, se usa esa pista en su
// lugar, repetida con un fundido entre el final y el principio.

const BEATS_PER_MINUTE = 66;
const BEAT = 60 / BEATS_PER_MINUTE;
export const BAR = 4 * BEAT;
const BARS_PER_CHORD = 2;

// Fa mayor 7 – Mi menor 7 – Re menor 7 – Do mayor 7: una bajada suave en do mayor.
// Notas MIDI: primero el bajo y después las cuatro voces del acorde.
const CHORDS = [
  { bass: 41, voices: [53, 57, 60, 64], melody: [69, 72, 76, 79, 81] },
  { bass: 40, voices: [52, 55, 59, 62], melody: [67, 71, 74, 76, 79] },
  { bass: 38, voices: [50, 53, 57, 60], melody: [69, 72, 74, 77, 81] },
  { bass: 36, voices: [48, 52, 55, 59], melody: [67, 71, 72, 76, 79] },
];

const hertz = (midi: number) => 440 * 2 ** ((midi - 69) / 12);

export interface MusicBus {
  ctx: BaseAudioContext;
  dry: AudioNode; // sonido directo
  echo: AudioNode; // envío al eco
}

/** Mezcla de la música: un filtro que la suaviza y un eco largo para las notas sueltas. */
export function createMusicBus(ctx: BaseAudioContext, out: AudioNode): MusicBus {
  const warmth = ctx.createBiquadFilter();
  warmth.type = "lowpass";
  warmth.frequency.value = 4200;
  warmth.connect(out);

  const delay = ctx.createDelay(2);
  delay.delayTime.value = BEAT * 0.75;
  const feedback = ctx.createGain();
  feedback.gain.value = 0.32;
  const damping = ctx.createBiquadFilter();
  damping.type = "lowpass";
  damping.frequency.value = 1600;
  delay.connect(damping).connect(feedback).connect(delay);
  damping.connect(warmth);

  return { ctx, dry: warmth, echo: delay };
}

/** Nota larga de acorde: entra y sale muy despacio. */
function pad(bus: MusicBus, midi: number, at: number, duration: number, peak: number, bass: boolean): void {
  const { ctx } = bus;
  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = bass ? 320 : 1300;
  filter.Q.value = 0.4;
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0, at);
  gain.gain.linearRampToValueAtTime(peak, at + 1.8);
  gain.gain.setValueAtTime(peak, at + duration);
  gain.gain.linearRampToValueAtTime(0, at + duration + 2.4);
  filter.connect(gain).connect(bus.dry);

  // Dos osciladores algo desafinados entre sí: suena más lleno y menos electrónico.
  const layers: [OscillatorType, number, number][] = bass
    ? [["sine", 0, 1]]
    : [
        ["triangle", -6, 1],
        ["sawtooth", 7, 0.3],
      ];
  for (const [type, detune, level] of layers) {
    const oscillator = ctx.createOscillator();
    oscillator.type = type;
    oscillator.frequency.value = hertz(midi);
    oscillator.detune.value = detune;
    const layer = ctx.createGain();
    layer.gain.value = level;
    oscillator.connect(layer).connect(filter);
    oscillator.start(at);
    oscillator.stop(at + duration + 2.5);
  }
}

/** Nota suelta, parecida a un piano eléctrico suave, con eco. */
function pluck(bus: MusicBus, midi: number, at: number, peak: number): void {
  const { ctx } = bus;
  const gain = ctx.createGain();
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.linearRampToValueAtTime(peak, at + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + 1.6);
  gain.connect(bus.dry);
  const send = ctx.createGain();
  send.gain.value = 0.45;
  gain.connect(send).connect(bus.echo);

  const harmonics: [number, number][] = [
    [1, 1],
    [2, 0.28],
    [3, 0.06],
  ];
  for (const [multiple, level] of harmonics) {
    const oscillator = ctx.createOscillator();
    oscillator.frequency.value = hertz(midi) * multiple;
    const partial = ctx.createGain();
    partial.gain.value = level;
    oscillator.connect(partial).connect(gain);
    oscillator.start(at);
    oscillator.stop(at + 1.7);
  }
}

/**
 * Programa un compás. Cada dos compases entra un acorde nuevo; por encima caen
 * unas pocas notas al azar, elegidas entre las que suenan bien con ese acorde.
 */
export function scheduleBar(bus: MusicBus, index: number, at: number, random: () => number = Math.random): void {
  const chord = CHORDS[Math.floor(index / BARS_PER_CHORD) % CHORDS.length];
  if (index % BARS_PER_CHORD === 0) {
    const length = BARS_PER_CHORD * BAR;
    pad(bus, chord.bass, at, length, 0.11, true);
    for (const voice of chord.voices) pad(bus, voice, at, length, 0.045, false);
  }
  for (let half = 0; half < 8; half++) {
    if (random() >= 0.2) continue;
    const note = chord.melody[Math.floor(random() * chord.melody.length)];
    pluck(bus, note, at + (half * BEAT) / 2 + random() * 0.03, 0.07 + random() * 0.03);
  }
}

export interface MusicPlayer {
  start(): void;
  stop(): void;
}

const LOOKAHEAD_SECONDS = 2;
const TICK_MS = 400;

/** Música generada: va programando compases un poco por delante del reloj de audio. */
export class GeneratedMusic implements MusicPlayer {
  private timer: number | null = null;
  private bar = 0;
  private nextBarAt = 0;

  constructor(private readonly bus: MusicBus) {}

  start(): void {
    if (this.timer !== null) return;
    this.nextBarAt = this.bus.ctx.currentTime + 0.1;
    this.tick();
    this.timer = window.setInterval(this.tick, TICK_MS);
  }

  stop(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
  }

  private tick = (): void => {
    while (this.nextBarAt < this.bus.ctx.currentTime + LOOKAHEAD_SECONDS) {
      scheduleBar(this.bus, this.bar, this.nextBarAt);
      this.bar += 1;
      this.nextBarAt += BAR;
    }
  };
}

const MAX_CROSSFADE_SECONDS = 3;

/**
 * Pista de un archivo, repetida sin corte: cada vuelta empieza un poco antes de
 * que acabe la anterior y las dos se funden. Vale para cualquier pista, aunque
 * no esté preparada para repetirse.
 */
export class FileMusic implements MusicPlayer {
  private timer: number | null = null;
  private nextStartAt = 0;
  private readonly playing = new Set<AudioBufferSourceNode>();
  private readonly crossfade: number;

  constructor(
    private readonly ctx: BaseAudioContext,
    private readonly out: AudioNode,
    private readonly buffer: AudioBuffer,
  ) {
    this.crossfade = Math.min(MAX_CROSSFADE_SECONDS, buffer.duration / 4);
  }

  start(): void {
    if (this.timer !== null) return;
    this.nextStartAt = this.ctx.currentTime + 0.1;
    this.tick();
    this.timer = window.setInterval(this.tick, TICK_MS);
  }

  stop(): void {
    if (this.timer !== null) window.clearInterval(this.timer);
    this.timer = null;
    // Quien llama ya está bajando el volumen: se corta cuando ha terminado de bajar.
    for (const source of this.playing) source.stop(this.ctx.currentTime + 2);
    this.playing.clear();
  }

  private tick = (): void => {
    while (this.nextStartAt < this.ctx.currentTime + LOOKAHEAD_SECONDS) {
      const at = this.nextStartAt;
      const end = at + this.buffer.duration;
      const source = this.ctx.createBufferSource();
      source.buffer = this.buffer;
      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0, at);
      gain.gain.linearRampToValueAtTime(1, at + this.crossfade);
      gain.gain.setValueAtTime(1, end - this.crossfade);
      gain.gain.linearRampToValueAtTime(0, end);
      source.connect(gain).connect(this.out);
      source.start(at);
      this.playing.add(source);
      source.onended = () => this.playing.delete(source);
      this.nextStartAt = end - this.crossfade;
    }
  };
}
