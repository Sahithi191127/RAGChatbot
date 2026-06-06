interface ExamplePillsProps {
  questions: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
}

export function ExamplePills({
  questions,
  onSelect,
  disabled = false,
}: ExamplePillsProps) {
  return (
    <div className="mt-3 flex flex-col gap-2">
      {questions.map((question) => (
        <button
          key={question}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(question)}
          className="rounded-lg border border-blue-500/60 bg-transparent px-3 py-2.5 text-left text-sm text-blue-300 transition hover:border-blue-400 hover:bg-blue-500/10 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {question}
        </button>
      ))}
    </div>
  );
}
