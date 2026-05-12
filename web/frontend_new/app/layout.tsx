import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

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
                <Link href="/" className="text-xl font-bold text-cyan-400">
                  Badminton Pro
                </Link>
                <div className="hidden md:block ml-10">
                  <div className="flex space-x-4">
                    <Link href="/" className="text-zinc-100 hover:text-cyan-400 px-3 py-2 rounded-md text-sm font-medium transition-colors">
                      Leaderboard
                    </Link>
                    <Link href="#" className="text-zinc-600 px-3 py-2 rounded-md text-sm font-medium cursor-not-allowed">
                      Analytics
                    </Link>
                    <Link href="#" className="text-zinc-600 px-3 py-2 rounded-md text-sm font-medium cursor-not-allowed">
                      Matches
                    </Link>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-sm text-zinc-500">v2.0-alpha</div>
                <button className="px-4 py-2 bg-zinc-100 text-zinc-900 hover:bg-zinc-300 shadow-[0_0_15px_rgba(255,255,255,0.1)] transition-all font-semibold rounded-lg">
                  Connect
                </button>
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
