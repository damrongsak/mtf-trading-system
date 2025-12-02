'use client';

import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { usePathname } from "next/navigation";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AuthProvider } from "@/context/AuthContext";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();
  
  // Pages that should not show Sidebar/Header
  const isAuthPage = pathname === '/login';

  // Auth pages (login) render without Sidebar/Header
  if (isAuthPage) {
    return (
      <html lang="en">
        <head>
          <title>MTF Trading System - Login</title>
          <meta name="description" content="Algorithmic Trading Dashboard" />
        </head>
        <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-background text-foreground`}>
          <AuthProvider>
            {children}
          </AuthProvider>
        </body>
      </html>
    );
  }

  // Authenticated pages render with Sidebar/Header
  return (
    <html lang="en">
      <head>
        <title>MTF Trading System</title>
        <meta name="description" content="Algorithmic Trading Dashboard" />
      </head>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-background text-foreground`}>
        <AuthProvider>
          <div className="flex h-screen overflow-hidden">
            <Sidebar />
            <div className="flex-1 flex flex-col overflow-hidden ml-64">
              <Header />
              <main className="flex-1 overflow-y-auto p-6">
                {children}
              </main>
            </div>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
