import { SCIENCE_URL } from "@/lib/site";

import Section from "./Section";

const METHODS = [
  {
    name: "ECTemp",
    what: "Core temperature from heart rate, one minute at a time, with an extended Kalman filter.",
    cite: "Buller MJ et al. Physiological Measurement 2013;34(7):781-798.",
    href: "https://doi.org/10.1088/0967-3334/34/7/781",
    anchor: "1-ectemp-core-temperature-from-sequential-heart-rate",
  },
  {
    name: "Validation in heat",
    what: "Independent check in 101 elite athletes exercising in heat, including the 39.0 C limit.",
    cite: "de Korte JQ et al. Frontiers in Sports and Active Living 2022;4:882254.",
    href: "https://doi.org/10.3389/fspor.2022.882254",
    anchor: "2-ectemp-validation-in-elite-athletes",
  },
  {
    name: "Physiological Strain Index",
    what: "Core temperature and heart rate combined on a 0 to 10 scale.",
    cite: "Moran DS, Shitzer A, Pandolf KB. Am J Physiol 1998;275:R129-R134.",
    href: "https://doi.org/10.1152/ajpregu.1998.275.1.R129",
    anchor: "3-physiological-strain-index",
  },
  {
    name: "WBGT",
    what: "Wet bulb globe temperature from forecast weather, with the sun and wind at the venue.",
    cite: "Liljegren JC et al. J Occup Environ Hyg 2008;5(10):645-655.",
    href: "https://doi.org/10.1080/15459620802310770",
    anchor: "4-outdoor-wbgt-from-forecast-weather",
  },
  {
    name: "Heat risk",
    what: "Race flag bands, the ACSM 2007 table, and the heat index on the PAGASA scale.",
    cite: "Armstrong LE et al. Med Sci Sports Exerc 2007;39(3):556-572.",
    href: "https://doi.org/10.1249/MSS.0b013e31802fa199",
    anchor:
      "5-heat-risk-categories-for-endurance-events-and-the-pagasa-heat-index",
  },
  {
    name: "Performance in heat",
    what: "How much finish times slow per degree of WBGT, and where the data run out.",
    cite: "Ely MR et al. Med Sci Sports Exerc 2007; Mantzios K et al. 2022.",
    href: "https://doi.org/10.1249/mss.0b013e31802d3aba",
    anchor: "6-running-performance-in-heat",
  },
] as const;

export default function Science() {
  return (
    <Section
      id="science"
      kicker="The science"
      title="Every number has a source."
    >
      <p className="max-w-2xl leading-relaxed text-muted">
        Each equation, parameter and threshold is recorded with its source in{" "}
        <a className="underline" href={SCIENCE_URL}>
          docs/SCIENCE.md
        </a>
        . Anything that could not be checked against a source is marked
        unverified and does not ship.
      </p>
      <ul className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
        {METHODS.map((m) => (
          <li key={m.name}>
            <h3 className="font-serif text-xl">{m.name}</h3>
            <p className="mt-2 leading-relaxed text-muted">{m.what}</p>
            <p className="mt-3 text-sm">
              <a className="underline" href={m.href}>
                {m.cite}
              </a>
            </p>
            <p className="mt-1 text-sm">
              <a className="underline" href={`${SCIENCE_URL}#${m.anchor}`}>
                Method notes<span className="sr-only"> for {m.name}</span>
              </a>
            </p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
