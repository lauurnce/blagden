import Link from "next/link";

import { AUTHOR_NAME, AUTHOR_URL, REPO_URL, SCIENCE_URL } from "@/lib/site";

export default function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-border">
      <div className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-10 text-sm sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="font-serif text-lg">Blagden</p>
          <p className="mt-1 text-muted">
            Built by{" "}
            <a className="underline" href={AUTHOR_URL}>
              {AUTHOR_NAME}
            </a>
            . MIT licensed. Training insight, not medical advice.
          </p>
        </div>
        <nav aria-label="Footer">
          <ul className="flex flex-wrap gap-x-5 gap-y-2">
            <li>
              <Link className="underline-offset-4 hover:underline" href="/demo">
                Demo
              </Link>
            </li>
            <li>
              <Link
                className="underline-offset-4 hover:underline"
                href="/forecast"
              >
                Forecast
              </Link>
            </li>
            <li>
              <a
                className="underline-offset-4 hover:underline"
                href={SCIENCE_URL}
              >
                Science
              </a>
            </li>
            <li>
              <a className="underline-offset-4 hover:underline" href={REPO_URL}>
                GitHub
              </a>
            </li>
            <li>
              <a
                className="underline-offset-4 hover:underline"
                href={AUTHOR_URL}
              >
                lauurnce.is-a.dev
              </a>
            </li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
