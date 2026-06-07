/** Railway / FastAPI origin for server-side proxy (set on Vercel as API_URL). */
export function backendBaseUrl(): string | null {
  const raw = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (raw?.trim()) {
    return raw.trim().replace(/\/$/, "");
  }
  if (process.env.NODE_ENV === "development") {
    return "http://127.0.0.1:8000";
  }
  return null;
}

export function missingBackendConfigResponse() {
  return Response.json(
    {
      detail:
        "API_URL is not set on Vercel. Add API_URL=https://your-app.up.railway.app in Project Settings → Environment Variables, then redeploy.",
    },
    { status: 503 },
  );
}
