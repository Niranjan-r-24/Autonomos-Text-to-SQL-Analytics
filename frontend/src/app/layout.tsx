import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Enterprise Autonomous Text-to-SQL Analytics Platform",
  description: "Production-ready Autonomous Text-to-SQL Analytics Platform featuring multi-agent AI pipeline, self-healing queries, and dark obsidian executive UI.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-obsidian-900 text-slate-100 min-h-screen selection:bg-indigo-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
