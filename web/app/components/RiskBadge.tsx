/** A risk level shown with words and a symbol as well as colour, so it never relies on colour alone. */
const FLAG_STYLE: Record<string, { bg: string; fg: string; symbol: string }> = {
  white: { bg: "#ffffff", fg: "#111111", symbol: "○" },
  green: { bg: "#d9efd5", fg: "#0b3d16", symbol: "●" },
  yellow: { bg: "#fbf0bf", fg: "#4a3500", symbol: "▲" },
  red: { bg: "#f6c9c4", fg: "#5c0a03", symbol: "■" },
  black: { bg: "#1f1f1f", fg: "#ffffff", symbol: "◆" },
};

export function FlagBadge({ flag }: { flag: string | null }) {
  if (!flag) return <span>n/a</span>;
  const s = FLAG_STYLE[flag] ?? FLAG_STYLE.white!;
  return (
    <span
      className="inline-flex items-center gap-1 rounded border border-[#6b7280] px-2 py-0.5 text-sm font-medium"
      style={{ background: s.bg, color: s.fg }}
    >
      <span aria-hidden="true">{s.symbol}</span>
      {flag} flag
    </span>
  );
}

export const FLAG_LEGEND = Object.entries(FLAG_STYLE).map(([flag, s]) => ({
  flag,
  symbol: s.symbol,
}));
