import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "VANTA",
  description: "VANTA Symbolic Operating System Interface",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} font-sans`}>
      <body className="bg-[#1A1A1A] text-[#DCDCDC] antialiased">
        <div className="flex h-screen">
          {/* Sidebar Placeholder */}
          <aside className="w-64 bg-[#0A0A0A] p-4 hidden md:block">
            {/* VANTA Logo Placeholder */}
            <div className="mb-8 h-8 text-2xl font-bold text-[#E0B050]">
              VANTA
            </div>
            {/* Navigation Links Placeholder */}
            <nav className="space-y-2">
              <a href="#" className="block rounded px-2 py-1 hover:bg-[#3C3C3C]">
                Dashboard
              </a>
              <a href="#" className="block rounded px-2 py-1 hover:bg-[#3C3C3C]">
                Agents
              </a>
              <a href="#" className="block rounded px-2 py-1 hover:bg-[#3C3C3C]">
                Memory
              </a>
              <a href="#" className="block rounded px-2 py-1 hover:bg-[#3C3C3C]">
                Rituals
              </a>
              {/* Add more placeholders based on interface.png sidebar items */}
            </nav>
            {/* User/Settings Placeholder at bottom */}
            <div className="mt-auto">
              {/* Placeholder for user info/settings link */}
            </div>
          </aside>

          {/* Main Content Area */}
          <main className="flex-1 overflow-y-auto p-4 md:p-8">
            {children} {/* Page content will be rendered here */}
          </main>
        </div>
      </body>
    </html>
  );
}
