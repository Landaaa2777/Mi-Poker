interface Props {
  name: string;
  size: number; // diámetro en píxeles
  ring: string; // clases del aro: cambia con el turno y al ganar
}

/** Tono propio de cada nombre: el mismo jugador sale siempre del mismo color. */
function hueOf(name: string): number {
  let hash = 0;
  for (const character of name) hash = (hash * 31 + character.codePointAt(0)!) % 360;
  return hash;
}

/** Avatar original: un disco de color con la inicial del jugador. */
export function Avatar({ name, size, ring }: Props) {
  const hue = hueOf(name);
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-full font-black text-white shadow-md ring-[3px] ${ring}`}
      style={{
        width: size,
        height: size,
        fontSize: size * 0.44,
        background: `linear-gradient(145deg, hsl(${hue} 62% 56%), hsl(${(hue + 28) % 360} 58% 34%))`,
      }}
      aria-hidden
    >
      {name.trim().charAt(0).toUpperCase()}
    </span>
  );
}
