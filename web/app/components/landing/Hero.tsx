import Link from "next/link";

import { REPO_URL, SITE_TAGLINE } from "@/lib/site";

export default function Hero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden">
      <div className="mx-auto max-w-5xl px-4 pb-20 pt-16 sm:pb-28 sm:pt-24">
        <p className="text-sm font-medium text-muted">{SITE_TAGLINE}</p>
        <h1
          id="hero-title"
          className="mt-4 max-w-4xl font-serif text-5xl leading-[1.05] tracking-tight sm:text-7xl"
        >
          The steak cooked.{" "}
          <span className="whitespace-nowrap italic text-heat-hot">
            He didn&rsquo;t.
          </span>
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted">
          Blagden turns the heart rate from your run into an estimate of core
          temperature, forecasts heat stress for race morning at Metro Manila
          venues, and puts both behind a pace plan. Your run file stays on your
          device.
        </p>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            href="/demo"
            className="rounded-full bg-accent px-6 py-3 font-medium text-accent-contrast transition-opacity hover:opacity-90"
          >
            Try the demo
          </Link>
          <a
            href={REPO_URL}
            className="rounded-full border border-border px-6 py-3 font-medium transition-colors hover:bg-panel"
          >
            View on GitHub
          </a>
        </div>
      </div>
      <div
        aria-hidden="true"
        className="h-1.5 w-full bg-gradient-to-r from-heat-cool via-heat-warm to-heat-hot"
      />
    </section>
  );
}
