"use client";
import { useState } from "react";
import Loader from "@/components/Loader";
import { copilotQuery } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function CopilotPage() {
  const [question, setQuestion] = useState<string>("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    const q = question.trim();
    setMessages((m) => [...m, { role: "user", text: q }]);
    setQuestion("");
    setLoading(true);
    try {
      const answers = await copilotQuery(q);
      setMessages((prev) => [
        ...prev,
        ...answers.map((a): Message => ({ role: "assistant", text: a })),
      ]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Error: ${errMsg}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Copilot Chat</h1>
      <div className="border rounded-lg p-4 h-[60vh] overflow-y-auto bg-gray-50 dark:bg-gray-900 dark:border-gray-700">
        {messages.length === 0 && (
          <p className="text-center text-gray-400">Ask a question to get started.</p>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`mb-4 ${
              msg.role === "user" ? "text-right" : "text-left"
            }`}
          >
            <span
              className={`inline-block px-3 py-2 rounded-lg max-w-[75%] whitespace-pre-line ${
                msg.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 dark:bg-gray-800 dark:text-gray-100"
              }`}
            >
              {msg.text}
            </span>
          </div>
        ))}
        {loading && <Loader />}
      </div>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Your question..."
          className="flex-1 border rounded px-3 py-2 dark:bg-gray-800 dark:border-gray-700"
        />
        <button
          type="submit"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          Send
        </button>
      </form>
    </div>
  );
}
