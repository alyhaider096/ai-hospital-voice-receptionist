import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Hospital Voice Receptionist Admin",
  description: "Admin dashboard for the AI hospital voice receptionist system."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
