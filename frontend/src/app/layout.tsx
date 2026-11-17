import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Autonomos Text-to-SQL Analytics",
  description: "Autonomous Text-to-SQL Analytics Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="min-h-screen bg-slate-950 text-slate-100" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
