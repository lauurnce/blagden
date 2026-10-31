import Section from "./Section";

const SOURCE_1 = "https://doi.org/10.1098/rstl.1775.0013";
const SOURCE_2 = "https://doi.org/10.1098/rstl.1775.0048";
const SCAN_2 = "https://archive.org/details/jstor-106218";

/** Every figure here was read from the two 1775 papers linked below. */
export default function Story() {
  return (
    <Section id="story" kicker="The name" title="A heated room, 1775">
      <div className="grid gap-10 md:grid-cols-[1fr_16rem]">
        <div className="max-w-2xl space-y-5 font-serif text-xl leading-relaxed">
          <p>
            In January and April 1775 the physician Charles Blagden and a few
            other gentlemen walked into a room heated by an iron stove. On 3
            April a thermometer rose one or two degrees above 260&nbsp;F, about
            127&nbsp;C. Eggs set near it roasted hard in about twenty minutes. A
            beefsteak, with bellows blowing the hot air across it, was
            &ldquo;pretty well done in thirteen minutes.&rdquo; Blagden stayed
            eight minutes and walked out.
          </p>
          <p>
            He credited part of the body&rsquo;s defence to perspiration,
            &ldquo;that cooling evaporation.&rdquo; His host, George Fordyce,
            had found the catch. In a damp room at 130&nbsp;F, vapour condensed
            on his skin instead of evaporating, and his pulse reached 139. Dry
            air, he concluded, was easier to bear.
          </p>
          <p className="text-heat-hot">
            A Manila race morning is the damp room.
          </p>
        </div>
        <aside className="self-end text-sm leading-relaxed text-muted">
          <p>Sources</p>
          <ul className="mt-2 space-y-2">
            <li>
              <a className="underline" href={SOURCE_1}>
                Blagden C. Experiments and observations in an heated room. Phil.
                Trans. 1775;65:111-123.
              </a>
            </li>
            <li>
              <a className="underline" href={SOURCE_2}>
                Blagden C. Further experiments and observations in an heated
                room. Phil. Trans. 1775;65:484-494.
              </a>{" "}
              (
              <a className="underline" href={SCAN_2}>
                free scan
              </a>
              )
            </li>
          </ul>
        </aside>
      </div>
    </Section>
  );
}
