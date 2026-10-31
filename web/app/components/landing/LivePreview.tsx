import Link from "next/link";

import { estimateCoreTemp } from "@/lib/ectemp";
import { REPORT_THRESHOLD_C, SENSITIVITY_LIMIT_C } from "@/lib/strain";
import { syntheticMarathonHr } from "@/lib/syntheticRun";

import DrawOnView from "./DrawOnView";
import Section from "./Section";

const T_MIN = 36.8;
const T_MAX = 39.8;

interface Frame {
  w: number;
  h: number;
  fs: number;
  pad: { l: number; r: number; t: number; b: number };
}

/** Wide frame for tablets and up; compact frame keeps text legible on phones. */
const WIDE: Frame = {
  w: 720,
  h: 300,
  fs: 12,
  pad: { l: 44, r: 16, t: 16, b: 36 },
};
const COMPACT: Frame = {
  w: 360,
  h: 260,
  fs: 13,
  pad: { l: 38, r: 10, t: 12, b: 34 },
};

function Chart({
  f,
  tcC,
  id,
  className,
  peak,
  at385,
  at390,
}: {
  f: Frame;
  tcC: readonly number[];
  id: string;
  className: string;
  peak: number;
  at385: number;
  at390: number;
}) {
  const { w: W, h: H, fs, pad: PAD } = f;
  const n = tcC.length;
  const xOf = (i: number) => PAD.l + ((W - PAD.l - PAD.r) * i) / (n - 1);
  const yOf = (v: number) =>
    PAD.t + ((H - PAD.t - PAD.b) * (T_MAX - v)) / (T_MAX - T_MIN);
  const d = tcC
    .map((v, i) => `${i ? "L" : "M"}${xOf(i).toFixed(1)},${yOf(v).toFixed(1)}`)
    .join("");
  const ticks = [37, 37.5, 38, 38.5, 39, 39.5];
  const xTicks = [0, 60, 120, 180, 240];
  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={`h-auto w-full ${className}`}
      role="img"
      aria-labelledby={`${id}-title ${id}-desc`}
    >
      <title id={`${id}-title`}>
        Estimated core temperature for a synthetic 4-hour run
      </title>
      <desc id={`${id}-desc`}>
        {`Starts at 37.0 C, passes 38.5 C at minute ${at385} and 39.0 C at minute ${at390}, and peaks at ${peak.toFixed(2)} C.`}
      </desc>
      <defs>
        <linearGradient id={`${id}-heat`} x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="var(--heat-cool)" />
          <stop offset="50%" stopColor="var(--heat-warm)" />
          <stop offset="100%" stopColor="var(--heat-hot)" />
        </linearGradient>
      </defs>
      {ticks.map((t) => (
        <g key={t}>
          <line
            x1={PAD.l}
            x2={W - PAD.r}
            y1={yOf(t)}
            y2={yOf(t)}
            stroke="currentColor"
            strokeOpacity={0.12}
          />
          <text
            x={PAD.l - 6}
            y={yOf(t) + 4}
            fontSize={fs}
            textAnchor="end"
            fill="currentColor"
            className="tabular"
          >
            {t.toFixed(1)}
          </text>
        </g>
      ))}
      {xTicks.map((m) => (
        <text
          key={m}
          x={xOf(Math.min(m, n - 1))}
          y={H - 12}
          fontSize={fs}
          textAnchor={m === 0 ? "start" : m === 240 ? "end" : "middle"}
          fill="currentColor"
          className="tabular"
        >
          {m === 0 ? "0 min" : `${m}`}
        </text>
      ))}
      <rect
        x={PAD.l}
        y={PAD.t}
        width={W - PAD.l - PAD.r}
        height={yOf(SENSITIVITY_LIMIT_C) - PAD.t}
        fill="var(--heat-hot)"
        fillOpacity={0.08}
      />
      <line
        x1={PAD.l}
        x2={W - PAD.r}
        y1={yOf(SENSITIVITY_LIMIT_C)}
        y2={yOf(SENSITIVITY_LIMIT_C)}
        stroke="var(--heat-hot)"
        strokeDasharray="6 4"
      />
      <text
        x={W - PAD.r - 4}
        y={yOf(SENSITIVITY_LIMIT_C) + fs + 6}
        fontSize={fs}
        textAnchor="end"
        fill="currentColor"
      >
        Less sensitive above 39.0 C
      </text>
      <path
        d={d}
        pathLength={1}
        fill="none"
        stroke={`url(#${id}-heat)`}
        strokeWidth={3}
        strokeLinecap="round"
        className="draw-line"
      />
    </svg>
  );
}

/** Rendered on the server at build time; only the drawing animation runs in the browser. */
export default function LivePreview() {
  const hr = syntheticMarathonHr();
  const { tcC } = estimateCoreTemp(hr);
  const peak = Math.max(...tcC);
  const firstAbove = (t: number) => tcC.findIndex((v) => v > t);
  const at385 = firstAbove(REPORT_THRESHOLD_C);
  const at390 = firstAbove(SENSITIVITY_LIMIT_C);
  return (
    <Section
      id="preview"
      kicker="Live preview"
      title="Four hours of heart rate, read as core temperature."
    >
      <div className="grid gap-8 lg:grid-cols-[1fr_15rem]">
        <figure className="rounded-2xl border border-border bg-panel p-4 sm:p-6">
          <DrawOnView>
            <Chart
              f={COMPACT}
              id="pv-sm"
              className="sm:hidden"
              {...{ tcC, peak, at385, at390 }}
            />
            <Chart
              f={WIDE}
              id="pv-lg"
              className="hidden sm:block"
              {...{ tcC, peak, at385, at390 }}
            />
          </DrawOnView>
          <figcaption className="mt-3 text-sm text-muted">
            Synthetic trace built from a formula, not a real run. The same trace
            is a golden test fixture shared by the Python and browser code.
          </figcaption>
        </figure>
        <div className="self-start">
          <dl className="grid grid-cols-3 gap-4 lg:grid-cols-1">
            {[
              ["Peak estimate", `${peak.toFixed(2)} C`],
              ["Past 38.5 C", `${at385} min`],
              ["Past 39.0 C", `${at390} min`],
            ].map(([k, v]) => (
              <div key={k} className="border-l-2 border-heat-warm pl-3">
                <dt className="text-xs text-muted sm:text-sm">{k}</dt>
                <dd className="tabular mt-1 font-serif text-xl sm:text-2xl">
                  {v}
                </dd>
              </div>
            ))}
            <div className="col-span-3 lg:col-span-1">
              <Link className="font-medium underline" href="/demo">
                Try it with your own run file
              </Link>
            </div>
          </dl>
        </div>
      </div>
    </Section>
  );
}
