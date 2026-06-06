import { Info } from "lucide-react";

export function DisclaimerFooter() {
  return (
    <footer className="mt-auto border-t border-red-900/40 bg-red-600 px-4 py-3">
      <p className="mx-auto flex max-w-3xl items-center justify-center gap-2 text-center text-sm font-bold uppercase tracking-wide text-white">
        <Info className="h-4 w-4 shrink-0" aria-hidden />
        Disclaimer: Facts-only. No investment advice.
      </p>
    </footer>
  );
}
