"use client";

interface AIResponseParserProps {
  text: string;
}

export function AIResponseParser({ text }: AIResponseParserProps) {
  // Parse markdown-style formatting in AI responses
  const parseText = (input: string) => {
    // Split by code blocks first
    const parts = input.split(/```(\w+)?\n?([\s\S]*?)```/g);

    return parts.map((part, idx) => {
      // Odd indices are language specifiers, even+1 are code blocks
      if (idx % 3 === 2) {
        return (
          <pre key={idx} className="bg-slate-900 border border-slate-700 rounded p-3 my-2 overflow-x-auto">
            <code className="text-xs text-slate-300 font-mono">{part}</code>
          </pre>
        );
      }

      // Regular text - parse inline formatting
      if (idx % 3 === 0) {
        return (
          <span key={idx}>
            {part.split(/(\*\*.*?\*\*|\*.*?\*|`.*?`)/).map((segment, segIdx) => {
              // Bold
              if (segment.startsWith("**") && segment.endsWith("**")) {
                return (
                  <strong key={segIdx} className="font-semibold text-emerald-300">
                    {segment.slice(2, -2)}
                  </strong>
                );
              }

              // Italic
              if (segment.startsWith("*") && segment.endsWith("*") && !segment.startsWith("**")) {
                return (
                  <em key={segIdx} className="italic text-slate-300">
                    {segment.slice(1, -1)}
                  </em>
                );
              }

              // Inline code
              if (segment.startsWith("`") && segment.endsWith("`")) {
                return (
                  <code key={segIdx} className="bg-slate-800 px-1.5 py-0.5 rounded text-xs font-mono text-emerald-400">
                    {segment.slice(1, -1)}
                  </code>
                );
              }

              return <span key={segIdx}>{segment}</span>;
            })}
          </span>
        );
      }

      return null;
    });
  };

  // Split by paragraphs
  const paragraphs = text.split(/\n\n+/);

  return (
    <div className="space-y-2">
      {paragraphs.map((para, idx) => {
        // Check if it's a list
        if (para.trim().startsWith("•") || para.trim().startsWith("-") || para.trim().startsWith("*")) {
          const items = para.split("\n").filter((line) => line.trim());
          return (
            <ul key={idx} className="space-y-1 ml-4 list-disc marker:text-emerald-500">
              {items.map((item, itemIdx) => (
                <li key={itemIdx} className="text-sm">
                  {parseText(item.replace(/^[•\-*]\s*/, ""))}
                </li>
              ))}
            </ul>
          );
        }

        // Regular paragraph
        return (
          <p key={idx} className="text-sm whitespace-pre-wrap">
            {parseText(para)}
          </p>
        );
      })}
    </div>
  );
}
