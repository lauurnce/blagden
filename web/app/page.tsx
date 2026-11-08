import Link from "next/link";

export default function Home() {
  return (
    <main
      id="main"
      className="mx-auto flex max-w-2xl flex-1 flex-col justify-center gap-4 px-4 py-16"
    >
      <h1 className="text-4xl font-semibold tracking-tight">Blagden</h1>
      <p className="text-lg">Heat intelligence for runners in the tropics.</p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          <Link className="underline" href="/demo">
            Estimate core temperature from a run file
          </Link>
          , processed on your device.
        </li>
        <li>
          <Link className="underline" href="/forecast">
            See the race-morning WBGT and heat index
          </Link>{" "}
          for a Metro Manila venue.
        </li>
      </ul>
      <p className="text-sm text-muted">
        Training insight, not medical advice.
      </p>
    </main>
  );
}
