import type { Metadata } from "next";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

export const metadata: Metadata = {
  title: "DevProbe — Code quality before the merge",
  description:
    "Review pull requests, understand risk, and improve code quality.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
