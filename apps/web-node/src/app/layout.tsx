import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Docstream — AI-Powered PDF to LaTeX Converter",
  description:
    "Convert any PDF to publication-quality LaTeX using AI. Open source, free, supports IEEE, Report, and Resume templates.",
  openGraph: {
    title: "Docstream — AI-Powered PDF to LaTeX Converter",
    description:
      "Convert any PDF to publication-quality LaTeX using AI. Open source, free, supports IEEE, Report, and Resume templates.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" style={{ backgroundColor: '#050810' }}>
      <body
        className={`${inter.variable} ${jetbrainsMono.variable} antialiased`}
      >
        <div className="mesh-bg" aria-hidden="true" />
        {children}
      </body>
    </html>
  );
}
