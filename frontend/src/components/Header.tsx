import { Bot, CircleUser } from "lucide-react";

export function Header() {
  return (
    <header className="sticky top-0 z-10 border-b border-slate-800 bg-[#0f172a]/95 backdrop-blur-sm">
      <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400">
            <Bot className="h-5 w-5" aria-hidden />
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-blue-100">
            FundFacts Assistant
          </h1>
        </div>
        <div
          className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-700 bg-slate-800 text-slate-400"
          aria-hidden
        >
          <CircleUser className="h-5 w-5" />
        </div>
      </div>
    </header>
  );
}
