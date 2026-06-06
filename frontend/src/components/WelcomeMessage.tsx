import type { SchemeListItem } from "@/lib/types";
import { EXAMPLE_QUESTIONS } from "@/lib/types";
import { ExamplePills } from "./ExamplePills";

interface WelcomeMessageProps {
  schemes: SchemeListItem[];
  onExampleClick: (question: string) => void;
}

export function WelcomeMessage({ schemes, onExampleClick }: WelcomeMessageProps) {
  return (
    <div className="rounded-xl border border-slate-700/80 bg-slate-800/80 p-5 text-slate-200 shadow-lg">
      <p className="text-[15px] leading-relaxed text-slate-300">
        Welcome. Ask factual questions about expense ratio, exit load, minimum SIP,
        benchmark, tax, or fund managers for the five supported HDFC schemes on
        Groww.
      </p>

      <div className="mt-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Supported schemes
        </h2>
        <ul className="mt-2 space-y-1.5 text-sm text-slate-300">
          {schemes.map((scheme) => (
            <li key={scheme.slug} className="flex gap-2">
              <span className="text-blue-400" aria-hidden>
                •
              </span>
              <span>{scheme.scheme_name}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-5">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Example questions
        </h2>
        <ExamplePills
          questions={[...EXAMPLE_QUESTIONS]}
          onSelect={onExampleClick}
        />
      </div>
    </div>
  );
}
