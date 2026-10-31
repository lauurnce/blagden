import Link from "next/link";

import Section from "./Section";

const STEPS = [
  {
    n: "1",
    title: "Heart rate becomes core temperature",
    body: "Your run file is resampled to one-minute heart rate. A Kalman filter (ECTemp) turns that series into an estimate of core temperature, minute by minute, and the Physiological Strain Index puts it on a 0 to 10 scale.",
    href: "/demo",
    cta: "Open the run file demo",
  },
  {
    n: "2",
    title: "The forecast becomes WBGT",
    body: "For a venue such as BGC, UP Diliman or the MOA grounds, Blagden fetches the hourly forecast and computes WBGT with the Liljegren model, the flag band, and the heat index on the PAGASA scale for each hour of race morning.",
    href: "/forecast",
    cta: "See race-morning WBGT",
  },
  {
    n: "3",
    title: "Both become a pace plan",
    body: "A baseline finish time (Riegel, or PaceBrain if installed) is slowed for the WBGT you will run through, with a range and a flag when the conditions are beyond the published data. This step runs in the Python command line tool today.",
    href: "https://github.com/lauurnce/blagden",
    cta: "See the CLI on GitHub",
  },
] as const;

export default function HowItWorks() {
  return (
    <Section
      id="how"
      kicker="How it works"
      title="Three steps, all on your side."
    >
      <ol className="grid gap-6 md:grid-cols-3">
        {STEPS.map((s) => (
          <li
            key={s.n}
            className="flex flex-col rounded-2xl border border-border bg-panel p-6"
          >
            <span
              aria-hidden="true"
              className="tabular flex h-9 w-9 items-center justify-center rounded-full bg-accent font-semibold text-accent-contrast"
            >
              {s.n}
            </span>
            <h3 className="mt-5 text-lg font-semibold">{s.title}</h3>
            <p className="mt-3 flex-1 leading-relaxed text-muted">{s.body}</p>
            {s.href.startsWith("/") ? (
              <Link className="mt-5 font-medium underline" href={s.href}>
                {s.cta}
              </Link>
            ) : (
              <a className="mt-5 font-medium underline" href={s.href}>
                {s.cta}
              </a>
            )}
          </li>
        ))}
      </ol>
    </Section>
  );
}
