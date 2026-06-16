"use client";

import { useEffect, useState } from "react";
import { fetchSignals } from "@/lib/api";

interface SignalsData {
  top_topics: string[];
  skill_frequencies: Record<string, number>;
  interview_format: { rounds: number | null; oa_mentioned: boolean; take_home: boolean };
  recency: string;
  sources: Record<string, number>;
}

export default function SignalsPage({ params }: { params: { company: string; role: string } }) {
  const [signals, setSignals] = useState<SignalsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSignals(params.company, params.role)
      .then(setSignals)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load signals"));
  }, [params.company, params.role]);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold">
        Interview signals — {decodeURIComponent(params.company)} / {decodeURIComponent(params.role)}
      </h1>

      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}

      {signals && (
        <div className="mt-6 space-y-6">
          <p className="text-xs text-gray-400">{signals.recency}</p>

          <div className="rounded-lg border border-gray-200 p-4">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">Source breakdown</h2>
            <div className="flex gap-4 text-sm text-gray-600">
              {Object.entries(signals.sources).map(([source, count]) => (
                <span key={source} className="rounded-full bg-gray-100 px-3 py-1">
                  {source}: {count}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 p-4">
            <h2 className="mb-2 text-sm font-semibold text-gray-700">Interview format</h2>
            <ul className="text-sm text-gray-600">
              <li>Typical rounds: {signals.interview_format.rounds ?? "unknown"}</li>
              <li>Online assessment mentioned: {signals.interview_format.oa_mentioned ? "Yes" : "No"}</li>
              <li>Take-home assignment mentioned: {signals.interview_format.take_home ? "Yes" : "No"}</li>
            </ul>
          </div>

          <div className="rounded-lg border border-gray-200 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-700">Top topics</h2>
            <div className="flex flex-wrap gap-2">
              {signals.top_topics.map((topic) => (
                <span key={topic} className="rounded-full bg-indigo-50 px-3 py-1 text-xs text-indigo-700">
                  {topic}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 p-4">
            <h2 className="mb-3 text-sm font-semibold text-gray-700">Skill frequencies</h2>
            <ul className="space-y-1 text-sm text-gray-600">
              {Object.entries(signals.skill_frequencies)
                .slice(0, 15)
                .map(([skill, freq]) => (
                  <li key={skill} className="flex justify-between">
                    <span>{skill}</span>
                    <span className="text-gray-400">{freq.toFixed(1)}</span>
                  </li>
                ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
