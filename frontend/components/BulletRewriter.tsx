"use client";

import { useState } from "react";
import type { BulletSuggestion } from "@/lib/api";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="ml-2 rounded border border-gray-200 px-2 py-1 text-xs text-gray-500 hover:bg-gray-50"
    >
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

export function BulletRewriter({ suggestions }: { suggestions: BulletSuggestion[] }) {
  if (suggestions.length === 0) {
    return <p className="text-sm text-gray-500">No bullets fell below the rewrite threshold — nice work.</p>;
  }

  return (
    <div className="space-y-6">
      {suggestions.map((s, i) => (
        <div key={i} className="rounded-lg border border-gray-200 p-4">
          <p className="text-sm font-medium text-gray-800">Original</p>
          <p className="mt-1 text-sm text-gray-600">{s.original}</p>
          <p className="mt-2 text-xs text-amber-600">Issue: {s.issue}</p>
          <p className="mt-3 text-sm font-medium text-gray-800">Rewrite options</p>
          <ul className="mt-1 space-y-2">
            {s.rewrites.map((r, j) => (
              <li key={j} className="flex items-start justify-between rounded bg-gray-50 p-2 text-sm text-gray-700">
                <span>{r}</span>
                <CopyButton text={r} />
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
