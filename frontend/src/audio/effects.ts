// Efectos de sonido generados con la Web Audio API: ruido filtrado y tonos
// cortos. No hay archivos de audio ni nada con derechos de autor.
//
// Todo se programa sobre un `BaseAudioContext`, así sirve igual para sonar en
// directo que para renderizar un efecto sin altavoces y comprobarlo.

export type EffectName =
  | "deal" // repartir una carta
  | "flip" // voltear una carta
  | "check" // pasar: dos golpecitos en la mesa
  | "chips" // apostar o igualar
  | "raise" // subir
  | "fold" // retirarse
  | "allIn"
  | "win" // gano yo el bote
  | "winOther" // lo gana otro jugador
  | "turn"; // aviso suave: me toca

interface Target {
  ctx: BaseAudioContext;
  out: AudioNode;
}

const noiseBuffers = new WeakMap<BaseAudioContext, AudioBuffer>();

/** Un segundo de ruido blanco, compartido por todos los efectos del contexto. */
function noise(ctx: BaseAudioContext): AudioBuffer {
  let buffer = noiseBuffers.get(ctx);
  if (!buffer) {
    buffer = ctx.createBuffer(1, ctx.sampleRate, ctx.sampleRate);
    const samples = buffer.getChannelData(0);
    for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
    noiseBuffers.set(ctx, buffer);
  }
  return buffer;
}

/** Volumen que sube enseguida y cae hasta el silencio. */
function envelope(target: Target, at: number, attack: number, duration: number, peak: number) {
  const gain = target.ctx.createGain();
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.linearRampToValueAtTime(peak, at + attack);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + duration);
  gain.connect(target.out);
  return gain;
}

interface HissOptions {
  duration: number;
  peak: number;
  type: BiquadFilterType;
  from: number; // frecuencia del filtro al empezar
  to?: number; // y al terminar, si barre
  q?: number;
  attack?: number;
}

/** Ráfaga de ruido filtrado: el roce de una carta, el chasquido de una ficha. */
function hiss(target: Target, at: number, options: HissOptions): void {
  const { ctx } = target;
  const source = ctx.createBufferSource();
  source.buffer = noise(ctx);
  const filter = ctx.createBiquadFilter();
  filter.type = options.type;
  filter.Q.value = options.q ?? 1;
  filter.frequency.setValueAtTime(options.from, at);
  if (options.to) filter.frequency.exponentialRampToValueAtTime(options.to, at + options.duration);
  source
    .connect(filter)
    .connect(envelope(target, at, options.attack ?? 0.003, options.duration, options.peak));
  source.start(at, Math.random() * 0.4);
  source.stop(at + options.duration + 0.05);
}

interface ToneOptions {
  from: number;
  to?: number;
  duration: number;
  peak: number;
  type?: OscillatorType;
  attack?: number;
}

/** Tono corto, con o sin caída de afinación: un golpe sordo, una nota de aviso. */
function tone(target: Target, at: number, options: ToneOptions): void {
  const oscillator = target.ctx.createOscillator();
  oscillator.type = options.type ?? "sine";
  oscillator.frequency.setValueAtTime(options.from, at);
  if (options.to) {
    oscillator.frequency.exponentialRampToValueAtTime(options.to, at + options.duration);
  }
  oscillator.connect(envelope(target, at, options.attack ?? 0.004, options.duration, options.peak));
  oscillator.start(at);
  oscillator.stop(at + options.duration + 0.05);
}

/** Choque de dos fichas: un "clac" seco con cuerpo alrededor de `pitch`. */
function clink(target: Target, at: number, pitch: number, level: number): void {
  hiss(target, at, { duration: 0.05, peak: 1.6 * level, type: "bandpass", from: pitch, q: 8, attack: 0.001 });
  hiss(target, at, { duration: 0.012, peak: 0.16 * level, type: "highpass", from: 6000, attack: 0.001 });
  tone(target, at, { from: pitch * 0.62, duration: 0.035, peak: 0.12 * level, type: "triangle", attack: 0.001 });
}

/** Varias fichas seguidas. `rising` las hace sonar cada vez más agudas. */
function cascade(target: Target, at: number, count: number, span: number, level: number, rising = false): void {
  for (let i = 0; i < count; i++) {
    const progress = count > 1 ? i / (count - 1) : 0;
    const pitch = rising ? 2500 + 1500 * progress : 2600 + Math.random() * 1400;
    clink(target, at + progress * span + Math.random() * 0.012, pitch, level * (0.75 + Math.random() * 0.25));
  }
}

/** Golpe de nudillos en el tapete. */
function knock(target: Target, at: number, level: number): void {
  tone(target, at, { from: 210, to: 105, duration: 0.085, peak: 0.45 * level, attack: 0.002 });
  hiss(target, at, { duration: 0.03, peak: 0.4 * level, type: "lowpass", from: 900, attack: 0.001 });
}

/** Nota suave de campanilla. */
function chime(target: Target, at: number, frequency: number, peak: number, duration: number): void {
  tone(target, at, { from: frequency, duration, peak, attack: 0.008 });
  tone(target, at, { from: frequency * 2, duration: duration * 0.6, peak: peak * 0.22, attack: 0.008 });
}

const EFFECTS: Record<EffectName, (target: Target, at: number) => void> = {
  deal: (target, at) =>
    hiss(target, at, { duration: 0.09, peak: 0.6, type: "bandpass", from: 1600, to: 5200, q: 0.8, attack: 0.004 }),
  flip: (target, at) => {
    hiss(target, at, { duration: 0.045, peak: 0.26, type: "highpass", from: 2400, attack: 0.002 });
    tone(target, at, { from: 260, to: 140, duration: 0.06, peak: 0.18, attack: 0.002 });
  },
  check: (target, at) => {
    knock(target, at, 1);
    knock(target, at + 0.115, 0.75);
  },
  chips: (target, at) => cascade(target, at, 3, 0.1, 0.8),
  raise: (target, at) => cascade(target, at, 5, 0.24, 0.85, true),
  fold: (target, at) =>
    hiss(target, at, { duration: 0.22, peak: 0.5, type: "lowpass", from: 1500, to: 300, q: 0.7, attack: 0.03 }),
  allIn: (target, at) => {
    tone(target, at, { from: 150, to: 70, duration: 0.24, peak: 0.4 });
    cascade(target, at, 9, 0.45, 0.9);
  },
  win: (target, at) => {
    cascade(target, at, 6, 0.36, 0.4);
    [523.25, 659.25, 783.99].forEach((note, index) => chime(target, at + index * 0.09, note, 0.2, 0.55));
    chime(target, at + 0.27, 1046.5, 0.12, 0.7);
  },
  winOther: (target, at) => cascade(target, at, 5, 0.3, 0.6),
  turn: (target, at) => {
    chime(target, at, 659.25, 0.16, 0.35);
    chime(target, at + 0.13, 880, 0.14, 0.45);
  },
};

export const EFFECT_NAMES = Object.keys(EFFECTS) as EffectName[];

/** Programa el efecto `name` para que suene en el instante `at` del contexto. */
export function playEffect(ctx: BaseAudioContext, out: AudioNode, name: EffectName, at: number): void {
  EFFECTS[name]({ ctx, out }, at);
}
