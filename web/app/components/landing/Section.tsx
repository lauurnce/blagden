import type { ReactNode } from "react";

/** Shared frame for landing sections: a small label, a serif heading, then content. */
export default function Section({
  id,
  kicker,
  title,
  children,
}: {
  id: string;
  kicker: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="border-t border-border"
    >
      <div className="mx-auto max-w-5xl px-4 py-16 sm:py-24">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-heat-warm">
          {kicker}
        </p>
        <h2
          id={`${id}-title`}
          className="mt-3 max-w-3xl font-serif text-3xl leading-tight tracking-tight sm:text-4xl"
        >
          {title}
        </h2>
        <div className="mt-8">{children}</div>
      </div>
    </section>
  );
}
