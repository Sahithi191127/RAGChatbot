import { Link2 } from "lucide-react";
import type { ChatMessage as ChatMessageType } from "@/lib/types";

interface ChatMessageProps {
  message: ChatMessageType;
}

function citationLabel(isRefusal: boolean | undefined): string {
  return isRefusal ? "Learn more" : "Source";
}

function citationHost(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

function formatDate(isoDate: string): string {
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString("en-IN", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function AnswerBody({ content }: { content: string }) {
  const paragraphs = content.split(/\n\n+/);

  return (
    <div className="space-y-3 text-[15px] leading-relaxed">
      {paragraphs.map((paragraph, index) => {
        const lines = paragraph.split("\n");
        const isBulletBlock = lines.every(
          (line) => line.trim().startsWith("*") || line.trim() === "",
        );

        if (isBulletBlock && lines.some((line) => line.trim().startsWith("*"))) {
          return (
            <ul key={index} className="list-none space-y-1 pl-1">
              {lines
                .filter((line) => line.trim().startsWith("*"))
                .map((line, lineIndex) => (
                  <li key={lineIndex} className="flex gap-2">
                    <span className="text-blue-400" aria-hidden>
                      •
                    </span>
                    <span>{line.replace(/^\*\s*/, "")}</span>
                  </li>
                ))}
            </ul>
          );
        }

        return (
          <p key={index} className="whitespace-pre-wrap">
            {paragraph}
          </p>
        );
      })}
    </div>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[90%] rounded-xl bg-blue-600 px-4 py-3 text-white shadow-md">
          <p className="text-[15px] leading-relaxed">{message.content}</p>
        </div>
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="flex justify-start">
        <div className="max-w-full rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-red-200">
          <p className="text-sm">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div
        className={`max-w-full rounded-xl border px-4 py-4 shadow-lg ${
          message.isRefusal
            ? "border-amber-500/30 bg-slate-800/90"
            : "border-slate-700/80 bg-slate-800/90"
        }`}
      >
        <AnswerBody content={message.content} />

        {message.citationUrl && (
          <a
            href={message.citationUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-blue-400 hover:text-blue-300"
          >
            <Link2 className="h-4 w-4 shrink-0" aria-hidden />
            {citationLabel(message.isRefusal)} ({citationHost(message.citationUrl)})
          </a>
        )}

        {message.lastUpdated && (
          <p className="mt-3 text-xs italic text-slate-500">
            Last updated from sources: {formatDate(message.lastUpdated)}
          </p>
        )}
      </div>
    </div>
  );
}
