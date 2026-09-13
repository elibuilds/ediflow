import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EdiFlow | Good food, better neighbors",
  description: "A local rescue network connecting stores, food banks, and residents."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
