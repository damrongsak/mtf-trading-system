"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { login } from "@/lib/api/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const { login: loginUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Backend expects 'username' field, but we use email as username
      const data = await login(email, password);
      loginUser(data.access_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    // Primary Background and Default Text Color
    <div className="min-h-screen flex items-center justify-center p-4 bg-[#0B0F19] text-[#e2e8f0] font-sans">
      
      {/* Glassmorphic Card Container */}
      <div className="w-full max-w-md bg-[#2d3748]/50 backdrop-blur-sm border border-[#1f2937] rounded-xl p-8 space-y-8 
                    transition-all duration-300 hover:scale-[1.005] 
                    shadow-[0_0_20px_-5px_rgba(59,130,246,0.1)]">
        
        {/* Header Section */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-[#e2e8f0]">
            Welcome Back <span role="img" aria-label="waving hand">👋</span>
          </h1>
          <p className="text-[#9ca3af] mt-2 text-sm">
            Today is a new day. It&apos;s your day. You shape it. Sign in to start managing your projects.
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="p-3 text-[#ef4444] bg-[#ef4444]/10 rounded-lg border border-[#ef4444]/20">
            {error}
          </div>
        )}

        {/* Sign In Form */}
        <form className="space-y-6" onSubmit={handleSubmit}>
          
          {/* Email/Username Field */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-[#e2e8f0]">
              Email or Username
            </label>
            <div className="mt-1">
              <input
                id="email"
                name="email"
                type="text"
                autoComplete="username"
                required
                value={email}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                placeholder="username or email@example.com"
                className="appearance-none block w-full px-3 py-3 border border-[#1f2937] rounded-lg shadow-sm 
                           placeholder-[#6b7280] text-[#e2e8f0] bg-transparent
                           focus:outline-none focus:ring-1 focus:ring-[#3b82f6] focus:border-[#3b82f6] 
                           sm:text-sm transition duration-150 ease-in-out"
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-[#e2e8f0]">
              Password
            </label>
            <div className="mt-1">
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                placeholder="at least 8 characters"
                className="appearance-none block w-full px-3 py-3 border border-[#1f2937] rounded-lg shadow-sm 
                           placeholder-[#6b7280] text-[#e2e8f0] bg-transparent
                           focus:outline-none focus:ring-1 focus:ring-[#3b82f6] focus:border-[#3b82f6] 
                           sm:text-sm transition duration-150 ease-in-out"
              />
            </div>
          </div>

          <div className="flex justify-end">
            <a href="#" className="text-sm font-medium text-[#3b82f6] hover:text-[#3b82f6]/80 transition duration-200">
              Forgot Password?
            </a>
          </div>

          {/* Sign In Button (Primary CTA) */}
          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-md text-sm font-medium text-white 
                         bg-[#3b82f6] hover:bg-[#3b82f6]/90 
                         focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#3b82f6] focus:ring-offset-[#0B0F19]
                         transition-all duration-300 ease-in-out hover:scale-[1.01]
                         shadow-[0_0_20px_-5px_rgba(59,130,246,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : null}
              {isLoading ? 'Signing in...' : 'Sign in'}
            </button>
          </div>
        </form>

        {/* Footer/Sign Up Link */}
        <div className="text-center mt-6">
          <p className="text-sm text-[#9ca3af]">
            Don&apos;t you have an account?{' '}
            <a href="#" className="font-medium text-[#3b82f6] hover:text-[#3b82f6]/80 transition duration-200">
              Sign up
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
