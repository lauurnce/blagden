import type { Metadata } from "next";

import ForecastClient from "./ForecastClient";

export const metadata: Metadata = {
  title: "Race-morning forecast",
  description: "Hourly WBGT, heat index and risk for a race venue and morning.",
};

export default function ForecastPage() {
  return (
    <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-10">
      <h1 className="mb-2 text-3xl font-semibold">Race-morning forecast</h1>
      <p className="mb-6 max-w-2xl">
        Hourly WBGT from the Liljegren model and the heat index on the PAGASA
        scale, computed in your browser from the Open-Meteo forecast. Only the
        place and date are sent to Open-Meteo.
      </p>
      <ForecastClient />
    </main>
  );
}
