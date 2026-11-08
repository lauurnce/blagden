import type { Metadata } from "next";
import "./globals.css";

import SiteHeader from "./components/SiteHeader";

export const metadata: Metadata = {
  title: "Blagden",
  description: "Heat intelligence for runners in the tropics.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="flex min-h-full flex-col">
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
