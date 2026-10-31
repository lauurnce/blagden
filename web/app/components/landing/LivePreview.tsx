import Link from "next/link";

import { estimateCoreTemp } from "@/lib/ectemp";
import { REPORT_THRESHOLD_C, SENSITIVITY_LIMIT_C } from "@/lib/strain";
import { syntheticMarathonHr } from "@/lib/syntheticRun";

import DrawOnView from "./DrawOnView";
import Section from "./Section";

const W = 720;
const H = 300;
const PAD = { l: 44, r: 16, t: 16, b: 36 };
const T_MIN = 36.8;
const T_MAX = 39.8;

function linePath(values: readonly number[]): string {
  const n = values.length;
  return values
    .map((v, i) => {
      const x = PAD.l + ((W - PAD.l - PAD.r) * i) / (n - 1);
      const y = PAD.t + ((H - PAD.t - PAD.b) * (T_MAX - v)) / (T_MAX - T_MIN);
      return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join("");
}

const yOf = (v: number) =>
  PAD.t + ((H - PAD.t - PAD.b) * (T_MAX - v)) / (T_MAX - T_MIN);

/** Rendered on the server at build time; only the drawing animation runs in the browser. */
export default function LivePreview() {
  const hr = syntheticMarathonHr();
  const { tcC } = estimateCoreTemp(hr);
  const peak = Math.max(...tcC);
  const firstAbove = (t: number) => tcC.findIndex((v) => v > t);
  const at385 = firstAbove(REPORT_THRESHOLD_C);
  const at390 = firstAbove(SENSITIVITY_LIMIT_C);
  const ticks = [37, 37.5, 38, 38.5, 39, 39.5];
  const xTicks = [0, 60, 120, 180, 240];
  return (
    <Section
      id="preview"
      kicker="Live preview"
      title="Four hours of heart rate, read as core temperature."
    >
      <div className="grid gap-8 lg:grid-cols-[1fr_15rem]">
        <figure className="rounded-2xl border border-border bg-panel p-4 sm:p-6">
          <DrawOnView>
            <svg
              viewBox={`0 0 ${W} ${H}`}
              className="h-auto w-full"
              role="img"
              aria-labelledby="pv-title pv-desc"
            >
              <title id="pv-title">
                Estimated core temperature for a synthetic 4-hour run
              </title>
              <desc id="pv-desc">
                {`Starts at 37.0 C, passes 38.5 C at minute ${at385} and 39.0 C at minute ${at390}, and peaks at ${peak.toFixed(2)} C.`}
              </desc>
              <defs>
                <linearGradient id="pv-heat" x1="0" y1="1" x2="0" y2="0">
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
                    x={PAD.l - 8}
                    y={yOf(t) + 4}
                    fontSize={12}
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
                  x={PAD.l + ((W - PAD.l - PAD.r) * m) / 239}
                  y={H - 12}
                  fontSize={12}
                  textAnchor="middle"
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
                x={PAD.l + 8}
                y={yOf(SENSITIVITY_LIMIT_C) - 8}
                fontSize={12}
                fill="currentColor"
              >
                Above 39.0 C the method is less sensitive
              </text>
              <path
                d={linePath(tcC)}
                pathLength={1}
                fill="none"
                stroke="url(#pv-heat)"
                strokeWidth={3}
                strokeLinecap="round"
                className="draw-line"
              />
            </svg>
          </DrawOnView>
          <figcaption className="mt-3 text-sm text-muted">
            Synthetic trace built from a formula, not a real run. The same trace
            is a golden test fixture shared by the Python and browser code.
          </figcaption>
        </figure>
        <dl className="grid grid-cols-3 gap-4 self-start lg:grid-cols-1">
          {[
            ["Peak estimate", `${peak.toFixed(2)} C`],
            ["Past 38.5 C", `minute ${at385}`],
            ["Past 39.0 C", `minute ${at390}`],
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
    </Section>
  );
}
