import type { ChatResponse, SchemeListItem } from "./types";

/** Same-origin API routes proxy to Railway via `API_URL` on Vercel. */
async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail.map((item: { msg?: string }) => item.msg).join(" ");
    }
  } catch {
    /* ignore */
  }
  return `Request failed (${res.status})`;
}

export async function fetchSchemes(): Promise<SchemeListItem[]> {
  const res = await fetch("/api/schemes", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    throw new Error(await parseError(res));
  }

  return res.json();
}
