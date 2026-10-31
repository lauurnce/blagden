import Section from "./Section";

const ITEMS = [
  {
    title: "Not medical advice",
    body: "Blagden gives training insight. It is not a diagnosis, and it is not a go or no-go decision for a race. If you feel unwell in the heat, stop and get help.",
  },
  {
    title: "Less sensitive above 39.0 C",
    body: "In 101 elite athletes exercising in heat, the heart-rate method agreed with measured core temperature within about 0.45 C on average, but detected fewer than half of the readings above 39.0 C (de Korte et al. 2022). A high reading can be missed.",
  },
  {
    title: "Estimates, not measurements",
    body: "Core temperature comes from heart rate alone, and WBGT comes from a forecast. Both carry error. Recreational runners on a humid Manila morning sit outside most of the published data, and every prediction says when that is the case.",
  },
] as const;

export default function Limitations() {
  return (
    <Section
      id="limits"
      kicker="Limitations"
      title="What Blagden cannot tell you."
    >
      <ul className="grid gap-6 md:grid-cols-3">
        {ITEMS.map((i) => (
          <li
            key={i.title}
            className="rounded-2xl border border-heat-hot/40 p-6"
          >
            <h3 className="text-lg font-semibold">{i.title}</h3>
            <p className="mt-3 leading-relaxed text-muted">{i.body}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}
