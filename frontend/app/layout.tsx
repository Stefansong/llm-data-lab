import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { AppShell } from "@/components/layout/AppShell";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "LLM Data Lab",
  description:
    "Research co-pilot for working with multi-LLM code generation, execution, and analytics."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full bg-slate-950 text-slate-100">
      <body className={`${inter.className} h-full`}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
