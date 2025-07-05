"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/auth/token`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: new URLSearchParams({
            username: email,
            password,
          }).toString(),
        }
      );
      if (!res.ok) {
        throw new Error("Invalid credentials");
      }
      const data = await res.json();
      if (typeof window !== "undefined") {
        localStorage.setItem("token", data.access_token);
      }
      router.push("/portfolio");
    } catch (err: unknown) {
      const error = err as Error;
      setError(error.message || "Login failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100 dark:bg-gray-900">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md space-y-6 rounded-lg bg-white p-8 shadow-md dark:bg-gray-800"
      >
        <h2 className="text-center text-2xl font-bold text-gray-900 dark:text-gray-100">
          Login
        </h2>
        {error && (
          <p className="rounded bg-red-100 p-2 text-center text-red-700 dark:bg-red-800 dark:text-red-100">
            {error}
          </p>
        )}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded border border-gray-300 p-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="w-full rounded border border-gray-300 p-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
          />
        </div>
        <button
          type="submit"
          className="w-full rounded bg-blue-600 p-2 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
        >
          Sign In
        </button>
        <p className="text-center text-sm text-gray-600 dark:text-gray-400">
          Don&apos;t have an account?{" "}
          <a href="/register" className="text-blue-600 hover:underline dark:text-blue-400">
            Register
          </a>
        </p>
      </form>
    </div>
  );
}
