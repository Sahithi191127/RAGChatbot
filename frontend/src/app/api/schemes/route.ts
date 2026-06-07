import { backendBaseUrl, missingBackendConfigResponse } from "@/lib/backend";

export async function GET() {
  const base = backendBaseUrl();
  if (!base) return missingBackendConfigResponse();

  const res = await fetch(`${base}/api/schemes`, { cache: "no-store" });
  const body = await res.text();

  return new Response(body, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
