export interface ChatResponse {
  answer: string;
  citation_url: string | null;
  last_updated: string;
  is_refusal: boolean;
  disclaimer: string;
}

export interface SchemeListItem {
  slug: string;
  scheme_name: string;
  category: string;
  source_url: string;
  aliases: string[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  citationUrl?: string | null;
  lastUpdated?: string;
  isRefusal?: boolean;
}

export const EXAMPLE_QUESTIONS = [
  "What is the expense ratio of HDFC Mid Cap Fund Direct Growth?",
  "What is the exit load on HDFC Defence Fund Direct Growth?",
  "Who manages HDFC Small Cap Fund Direct Growth?",
] as const;
