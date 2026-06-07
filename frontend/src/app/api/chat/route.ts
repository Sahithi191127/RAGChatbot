import { backendBaseUrl, missingBackendConfigResponse } from "@/lib/backend";

export async function POST(request: Request) {
  const base = backendBaseUrl();
  if (!base) return missingBackendConfigResponse();

  const payload = await request.text();
  const res = await fetch(`${base}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload,
  });
  const body = await res.text();

  return new Response(body, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
