import { Suspense } from "react";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";
import { HeaderSettings } from "@/components/header-settings";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Badminton Ratings",
  description: "Advanced analytics and ratings for badminton players.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${geistSans.variable} ${geistMono.variable}`}>
      <body className="font-sans bg-zinc-950 text-zinc-100 min-h-screen flex flex-col transition-colors duration-300">
        {/* Navbar */}
        <nav className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <Link href="/" className="text-xl font-black tracking-tighter italic text-white flex items-center gap-2 group">
                  <div className="w-8 h-8 bg-cyan-500 rounded-lg flex items-center justify-center text-black font-black not-italic group-hover:scale-110 transition-transform shadow-[0_0_15px_rgba(34,211,238,0.3)]">B</div>
                  BADMINTON <span className="text-cyan-400">PRO</span>
                </Link>
                <div className="hidden md:block ml-10">
                  <div className="flex space-x-2">
                    <Link href="/leaderboard" className="text-zinc-400 hover:text-white px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all hover:bg-zinc-900">
                      Leaderboard
                    </Link>
                    <Link href="/predict" className="text-zinc-400 hover:text-white px-4 py-2 rounded-xl text-xs font-black uppercase tracking-widest transition-all hover:bg-zinc-900">
                      Simulator
                    </Link>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-sm text-zinc-500">v2.0-alpha</div>
                <Suspense fallback={<div className="w-8 h-8 rounded-lg bg-zinc-900 animate-pulse border border-zinc-800" />}>
                  <HeaderSettings />
                </Suspense>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <main className="flex-grow max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 space-y-6">
          {children}
        </main>

        {/* Footer */}
        <footer className="border-t border-zinc-800 bg-zinc-950 py-6 mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-zinc-500">
            © 2026 Badminton Pro. All rights reserved.
          </div>
        </footer>
      </body>
    </html>
);
}
