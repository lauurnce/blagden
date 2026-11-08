import type { Metadata } from "next";

import DemoClient from "./DemoClient";

export const metadata: Metadata = {
  title: "Run file demo · Blagden",
  description:
    "Estimate core temperature and strain from a run file, processed on your device.",
};

export default function DemoPage() {
  return (
    <main id="main" className="mx-auto w-full max-w-4xl flex-1 px-4 py-10">
      <h1 className="mb-2 text-3xl font-semibold">Run file demo</h1>
      <p className="mb-6 max-w-2xl">
        Estimate core temperature minute by minute from heart rate with the
        ECTemp method, and the Physiological Strain Index. Training insight, not
        medical advice.
      </p>
      <DemoClient />
    </main>
  );
}
