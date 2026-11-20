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
      <body className="min-h-screen bg-[#F8F9F8] text-[#18221D] antialiased selection:bg-sage-100 selection:text-forest-900" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
