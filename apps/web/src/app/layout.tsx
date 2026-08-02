import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { AppShell } from "@/components/AppShell";
import { MockProvider } from "@/components/dev/MockProvider";
import { ScenarioSwitcher } from "@/components/dev/ScenarioSwitcher";
import "./globals.css";

export const metadata: Metadata = {
  title: "Portfolio Tracker",
  description: "Local Zerodha equity + Coin MF tracker",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`dark ${GeistSans.variable} ${GeistMono.variable}`}
    >
      <body className="font-sans antialiased">
        <MockProvider>
          <AppShell>{children}</AppShell>
          <ScenarioSwitcher />
        </MockProvider>
      </body>
    </html>
  );
}
