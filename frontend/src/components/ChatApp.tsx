"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { fetchSchemes, sendChatMessage } from "@/lib/api";
import type { ChatMessage, SchemeListItem } from "@/lib/types";
import { ChatInput } from "./ChatInput";
import { ChatMessage as ChatMessageBubble } from "./ChatMessage";
import { WelcomeMessage } from "./WelcomeMessage";

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function ChatApp() {
  const [schemes, setSchemes] = useState<SchemeListItem[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [schemesError, setSchemesError] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchSchemes()
      .then(setSchemes)
      .catch((error: Error) => setSchemesError(error.message));
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const submitMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      const userMessage: ChatMessage = {
        id: createId(),
        role: "user",
        content: trimmed,
      };

      setMessages((prev) => [...prev, userMessage]);
      setInput("");
      setLoading(true);

      try {
        const response = await sendChatMessage(trimmed);
        setMessages((prev) => [
          ...prev,
          {
            id: createId(),
            role: "assistant",
            content: response.answer,
            citationUrl: response.citation_url,
            lastUpdated: response.last_updated,
            isRefusal: response.is_refusal,
          },
        ]);
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Something went wrong.";
        setMessages((prev) => [
          ...prev,
          { id: createId(), role: "error", content: message },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [loading],
  );

  const fallbackSchemes: SchemeListItem[] = [
    {
      slug: "hdfc-mid-cap-fund-direct-growth",
      scheme_name: "HDFC Mid Cap Fund Direct Growth",
      category: "Equity — Mid Cap",
      source_url: "https://groww.in/mutual-funds/hdfc-mid-cap-fund-direct-growth",
      aliases: [],
    },
    {
      slug: "hdfc-small-cap-fund-direct-growth",
      scheme_name: "HDFC Small Cap Fund Direct Growth",
      category: "Equity — Small Cap",
      source_url: "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
      aliases: [],
    },
    {
      slug: "hdfc-large-cap-fund-direct-growth",
      scheme_name: "HDFC Large Cap Fund Direct Growth",
      category: "Equity — Large Cap",
      source_url: "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
      aliases: [],
    },
    {
      slug: "hdfc-gold-etf-fund-of-fund-direct-plan-growth",
      scheme_name: "HDFC Gold ETF Fund of Fund Direct Plan Growth",
      category: "Fund of Fund",
      source_url:
        "https://groww.in/mutual-funds/hdfc-gold-etf-fund-of-fund-direct-plan-growth",
      aliases: [],
    },
    {
      slug: "hdfc-defence-fund-direct-growth",
      scheme_name: "HDFC Defence Fund Direct Growth",
      category: "Equity — Thematic",
      source_url: "https://groww.in/mutual-funds/hdfc-defence-fund-direct-growth",
      aliases: [],
    },
  ];

  const displaySchemes = schemes.length > 0 ? schemes : fallbackSchemes;

  return (
    <>
      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-4 py-6">
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto pb-4">
          <WelcomeMessage
            schemes={displaySchemes}
            onExampleClick={submitMessage}
          />

          {schemesError && (
            <p className="text-xs text-amber-400/90">
              Could not load schemes from API. Using defaults. ({schemesError})
            </p>
          )}

          {messages.map((message) => (
            <ChatMessageBubble key={message.id} message={message} />
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="rounded-xl border border-slate-700/80 bg-slate-800/90 px-4 py-3">
                <p className="text-sm italic text-slate-400">Thinking…</p>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>
      </main>

      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={() => submitMessage(input)}
        disabled={loading}
      />
    </>
  );
}
