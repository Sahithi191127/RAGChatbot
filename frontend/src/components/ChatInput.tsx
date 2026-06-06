"use client";

import { FormEvent, KeyboardEvent, useRef } from "react";
import { Send } from "lucide-react";

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (!value.trim() || disabled) return;
    onSubmit();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!value.trim() || disabled) return;
      onSubmit();
    }
  };

  return (
    <div className="border-t border-slate-800 bg-[#0B1120] px-4 py-4">
      <form
        onSubmit={handleSubmit}
        className="mx-auto flex max-w-3xl items-end gap-2"
      >
        <label htmlFor="chat-input" className="sr-only">
          Your question
        </label>
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            id="chat-input"
            rows={1}
            value={value}
            maxLength={4000}
            disabled={disabled}
            placeholder="Ask a factual question about one of the supported schemes..."
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full resize-none rounded-xl border border-slate-700 bg-slate-900/80 px-4 py-3 pr-12 text-sm text-slate-100 placeholder:text-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className="absolute bottom-2.5 right-2 flex h-8 w-8 items-center justify-center rounded-lg text-blue-400 transition hover:bg-blue-500/10 hover:text-blue-300 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </form>
      <p className="mx-auto mt-2 max-w-3xl text-center text-xs text-slate-500">
        Do not enter PAN, Aadhaar, email addresses, phone numbers, account
        numbers, or OTPs.
      </p>
    </div>
  );
}
