/**
 * Core temperature (solid line) with heart rate on a second axis (dashed line), drawn as SVG.
 * Lines differ by pattern as well as colour; the reference lines are labelled in text.
 */
import { REPORT_THRESHOLD_C, SENSITIVITY_LIMIT_C } from "@/lib/strain";

const W = 720;
const H = 320;
const PAD = { l: 52, r: 56, t: 16, b: 40 };

function path(
  values: (number | null)[],
  x: (i: number) => number,
  y: (v: number) => number,
): string {
  let d = "";
  let pen = false;
  values.forEach((v, i) => {
    if (v === null || Number.isNaN(v)) {
      pen = false;
      return;
    }
    d += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    pen = true;
  });
  return d;
}

export default function CoreTempChart({
  tcC,
  hr,
}: {
  tcC: number[];
  hr: (number | null)[];
}) {
  const n = tcC.length;
  const tMin = Math.min(36.5, ...tcC.map((t) => t - 0.2));
  const tMax = Math.max(39.5, ...tcC.map((t) => t + 0.2));
  const hrValues = hr.filter((h): h is number => h !== null);
  const hMin = Math.floor((Math.min(...hrValues) - 5) / 10) * 10;
  const hMax = Math.ceil((Math.max(...hrValues) + 5) / 10) * 10;
  const x = (i: number) =>
    PAD.l + ((W - PAD.l - PAD.r) * i) / Math.max(1, n - 1);
  const yT = (v: number) =>
    PAD.t + ((H - PAD.t - PAD.b) * (tMax - v)) / (tMax - tMin);
  const yH = (v: number) =>
    PAD.t + ((H - PAD.t - PAD.b) * (hMax - v)) / (hMax - hMin);
  const tTicks = Array.from(
    { length: Math.floor((tMax - tMin) / 0.5) + 1 },
    (_, k) => Math.ceil(tMin * 2) / 2 + k * 0.5,
  ).filter((v) => v <= tMax);
  const hTicks = Array.from(
    { length: (hMax - hMin) / 20 + 1 },
    (_, k) => hMin + k * 20,
  );
  const xTicks = Array.from(
    { length: Math.floor(n / 10) + 1 },
    (_, k) => k * 10,
  ).filter((m) => m < n);
  const peak = Math.max(...tcC);
  return (
    <figure className="w-full">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-labelledby="ct-title ct-desc"
        data-testid="core-temp-chart"
      >
        <title id="ct-title">
          Estimated core temperature and heart rate by minute
        </title>
        <desc id="ct-desc">
          {`${n} minutes. Estimated core temperature from ${tcC[0]!.toFixed(2)} C to a peak of ${peak.toFixed(2)} C. Heart rate from ${Math.min(...hrValues).toFixed(0)} to ${Math.max(...hrValues).toFixed(0)} bpm.`}
        </desc>
        <rect
          x={PAD.l}
          y={PAD.t}
          width={W - PAD.l - PAD.r}
          height={H - PAD.t - PAD.b}
          fill="none"
          stroke="currentColor"
          strokeOpacity={0.3}
        />
        {tTicks.map((v) => (
          <g key={`t${v}`}>
            <line
              x1={PAD.l - 4}
              x2={PAD.l}
              y1={yT(v)}
              y2={yT(v)}
              stroke="currentColor"
            />
            <text
              x={PAD.l - 6}
              y={yT(v) + 4}
              fontSize={11}
              textAnchor="end"
              fill="currentColor"
            >
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {hTicks.map((v) => (
          <g key={`h${v}`}>
            <line
              x1={W - PAD.r}
              x2={W - PAD.r + 4}
              y1={yH(v)}
              y2={yH(v)}
              stroke="currentColor"
            />
            <text
              x={W - PAD.r + 6}
              y={yH(v) + 4}
              fontSize={11}
              fill="currentColor"
            >
              {v}
            </text>
          </g>
        ))}
        {xTicks.map((m) => (
          <text
            key={`x${m}`}
            x={x(m)}
            y={H - PAD.b + 16}
            fontSize={11}
            textAnchor="middle"
            fill="currentColor"
          >
            {m}
          </text>
        ))}
        <text
          x={(W + PAD.l - PAD.r) / 2}
          y={H - 6}
          fontSize={12}
          textAnchor="middle"
          fill="currentColor"
        >
          minutes from start
        </text>
        <text
          x={14}
          y={H / 2}
          fontSize={12}
          textAnchor="middle"
          fill="currentColor"
          transform={`rotate(-90 14 ${H / 2})`}
        >
          core temperature (C)
        </text>
        <text
          x={W - 10}
          y={H / 2}
          fontSize={12}
          textAnchor="middle"
          fill="currentColor"
          transform={`rotate(90 ${W - 10} ${H / 2})`}
        >
          heart rate (bpm)
        </text>
        {[REPORT_THRESHOLD_C, SENSITIVITY_LIMIT_C].map((v) => (
          <g key={`ref${v}`}>
            <line
              x1={PAD.l}
              x2={W - PAD.r}
              y1={yT(v)}
              y2={yT(v)}
              stroke="currentColor"
              strokeOpacity={0.6}
              strokeDasharray={v === SENSITIVITY_LIMIT_C ? "6 4" : "2 4"}
            />
            <text x={PAD.l + 6} y={yT(v) - 4} fontSize={11} fill="currentColor">
              {v === SENSITIVITY_LIMIT_C
                ? "39.0 C: method less sensitive above"
                : "38.5 C summary threshold"}
            </text>
          </g>
        ))}
        <path
          d={path(hr, x, yH)}
          fill="none"
          stroke="#2563eb"
          strokeWidth={1.5}
          strokeDasharray="5 3"
          data-testid="hr-line"
        />
        <path
          d={path(tcC, x, yT)}
          fill="none"
          stroke="#b91c1c"
          strokeWidth={2.5}
          data-testid="ct-line"
        />
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-4 text-sm">
        <span>
          <svg width="28" height="8" aria-hidden="true">
            <line
              x1="0"
              x2="28"
              y1="4"
              y2="4"
              stroke="#b91c1c"
              strokeWidth="2.5"
            />
          </svg>{" "}
          estimated core temperature (solid)
        </span>
        <span>
          <svg width="28" height="8" aria-hidden="true">
            <line
              x1="0"
              x2="28"
              y1="4"
              y2="4"
              stroke="#2563eb"
              strokeWidth="1.5"
              strokeDasharray="5 3"
            />
          </svg>{" "}
          heart rate, minute mean (dashed)
        </span>
      </figcaption>
    </figure>
  );
}
