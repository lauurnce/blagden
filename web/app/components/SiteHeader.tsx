import Link from "next/link";

const LINKS = [
  { href: "/demo", label: "Run file demo", short: "Demo" },
  { href: "/forecast", label: "Race-morning forecast", short: "Forecast" },
] as const;

export default function SiteHeader() {
  return (
    <header className="border-b border-border">
      <a href="#main" className="skip-link underline">
        Skip to content
      </a>
      <nav
        aria-label="Main"
        className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3"
      >
        <Link
          href="/"
          className="mr-auto font-serif text-xl font-semibold tracking-tight"
        >
          Blagden
        </Link>
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            className="text-sm underline-offset-4 hover:underline"
          >
            <span className="sm:hidden">{l.short}</span>
            <span className="hidden sm:inline">{l.label}</span>
          </Link>
        ))}
      </nav>
    </header>
  );
}
