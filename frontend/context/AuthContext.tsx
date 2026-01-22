"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { getProfile } from "@/lib/api/auth";
import { UserResponse } from "@/lib/api/types";
import { logger } from "@/lib/api/app-logger";

interface AuthContextType {
  user: UserResponse | null;
  authToken: string | null;
  loading: boolean;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  refetchProfile: () => Promise<void>;
  setUser: (user: UserResponse | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Initialize with null to ensure server/client match during hydration
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [user, setUser] = useState<UserResponse | null>(null);
  const [loading, setLoading] = useState(true);
  
  const router = useRouter();
  const pathname = usePathname();

  // Fetch user profile from backend
  const fetchProfile = React.useCallback(async () => {
    try {
      const userData = await getProfile();
      setUser(userData);
    } catch (error) {
      logger.error("Failed to fetch user profile:", error);
      // If profile fetch fails, clear token and redirect to login
      localStorage.removeItem("token");
      setAuthToken(null);
      setUser(null);
      if (pathname !== "/login") {
        router.push("/login");
      }
    } finally {
      setLoading(false);
    }
  }, [pathname, router]);

  const refetchProfile = async () => {
    if (authToken) {
      await fetchProfile();
    }
  };

  useEffect(() => {
    // Check localStorage only on the client after mount
    const token = localStorage.getItem("token");
    if (token) {
      setAuthToken(token);
      fetchProfile();
    } else {
      setLoading(false);
    }
  }, [fetchProfile]);

  // Redirect unauthenticated users from protected routes
  useEffect(() => {
    if (!loading && !authToken && pathname !== "/login") {
      const protectedRoutes = ['/dashboard', '/journal', '/signals', '/backtest', '/ai-analyst', '/settings'];
      const isProtectedRoute = protectedRoutes.some(route => pathname.startsWith(route));
      
      if (isProtectedRoute) {
        router.push("/login");
      }
    }
  }, [loading, authToken, pathname, router]);

  const login = (token: string) => {
    localStorage.setItem("token", token);
    setAuthToken(token);
    setLoading(true);
    fetchProfile().then(() => {
      router.push("/dashboard");
    });
  };

  const logout = () => {
    localStorage.removeItem("token");
    setAuthToken(null);
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, authToken, loading, login, logout, isAuthenticated: !!user, refetchProfile, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
