import Section from "./Section";

const POINTS = [
  {
    title: "Sweat only cools when it evaporates",
    body: "Sweat cools the body only when it evaporates. Humid air already holds a lot of water vapour, so sweat evaporates more slowly and more of it drips off without cooling. The same pace costs more heat than it would in dry air.",
  },
  {
    title: "WBGT measures what the body feels",
    body: "Wet bulb globe temperature weights three readings: 70 percent a wet wick in moving air, which tracks how well sweat can evaporate; 20 percent a black globe in the sun, which tracks radiant heat; and 10 percent the air temperature. Race medicine sets its flags on WBGT.",
  },
  {
    title: "The heat index assumes shade and rest",
    body: "The heat index behind the PAGASA scale assumes shade and a light wind. A Manila morning at 29 C and 85 percent humidity reads Caution on that scale, while the same air with sun on it gives a WBGT in the red or black flag band. Blagden shows both and says why they disagree.",
  },
] as const;

export default function Problem() {
  return (
    <Section
      id="problem"
      kicker="The problem"
      title="Humid heat is a different problem from hot weather."
    >
      <div className="grid gap-8 md:grid-cols-3">
        {POINTS.map((p, i) => (
          <article key={p.title} className="border-t-2 border-heat-warm pt-5">
            <p className="tabular font-serif text-3xl text-heat-warm">
              0{i + 1}
            </p>
            <h3 className="mt-3 text-lg font-semibold">{p.title}</h3>
            <p className="mt-3 leading-relaxed text-muted">{p.body}</p>
          </article>
        ))}
      </div>
    </Section>
  );
}
