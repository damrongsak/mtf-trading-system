"use client";

import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { login } from "@/lib/api/auth";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const { login: loginUser } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    try {
      const data = await login(username, password);
      // Call the login function from AuthContext which handles token storage
      // and user state management
      loginUser(data.access_token);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Invalid credentials");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-900 text-white">
      <div className="w-full max-w-md p-8 space-y-6 bg-gray-800 rounded-xl shadow-lg border border-gray-700">
        <h2 className="text-3xl font-bold text-center text-emerald-400">Sign In</h2>
        {error && <div className="p-3 text-red-400 bg-red-900/20 rounded border border-red-900">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-400">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 mt-1 bg-gray-900 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-400">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 mt-1 bg-gray-900 border border-gray-700 rounded focus:ring-2 focus:ring-emerald-500 focus:outline-none text-white"
              required
            />
          </div>
          <button
            type="submit"
            className="w-full py-2 font-bold text-gray-900 bg-emerald-400 rounded hover:bg-emerald-300 transition-colors"
          >
            Login
          </button>
        </form>
      </div>
    </div>
  );
}
