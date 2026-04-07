import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureAI Monitor",
  description: "AI-powered security monitoring platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
