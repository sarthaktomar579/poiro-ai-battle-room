import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Poiro Battle Room",
  description:
    "A real-time AI creative battle room. Host a brief, invite contestants, watch jobs race, and crown a winner.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
