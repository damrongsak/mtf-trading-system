'use client';

import { Inter, JetBrains_Mono } from "next/font/google";
import { usePathname } from "next/navigation";
import "./globals.css";
import { Sidebar } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { AuthProvider } from "@/context/AuthContext";
import { SidebarProvider } from "@/context/SidebarContext";

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
  const isAuthPage = pathname === '/login' || pathname === '/register';
  const isGuestPage = pathname === '/';

  // Guest/Auth pages render without Sidebar/Header
  if (isAuthPage || isGuestPage) {
    const pageTitle = isAuthPage ? 'MTF Trading System - Auth' : 'MTF Trading System - AI-Powered Gold Trading';
    
    return (
      <html lang="en">
        <head>
          <title>{pageTitle}</title>
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
    <html lang="en" suppressHydrationWarning>
      <head>
        <title>MTF Trading System</title>
        <meta name="description" content="Algorithmic Trading Dashboard" />
      </head>
      <body suppressHydrationWarning className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased bg-background text-foreground`}>
        <AuthProvider>
          <SidebarProvider>
            <div className="flex h-screen overflow-hidden">
              <Sidebar />
              {/* Main Content Wrapper - Use md:ml-64 to offset sidebar only on desktop */}
              <div className="flex-1 flex flex-col overflow-hidden w-full md:ml-64">
                <Header />
                <main className="flex-1 overflow-y-auto p-6">
                  {children}
                </main>
              </div>
            </div>
          </SidebarProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
