import type { Metadata } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "WebPulse AI Visibility Assessment",
  description: "See how AI tools discover your business. Free AI visibility assessment with personalized report.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-webpulse-dark text-white antialiased">{children}      <Script
        src="https://assets.calendly.com/assets/external/widget.js"
        strategy="afterInteractive"
      />
    </body>
    </html>
  );
}
