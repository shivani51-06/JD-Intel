"use client";

const STAGE_LABELS: Record<string, string> = {
  starting: "Starting analysis",
  jd_parser: "Parsing job description",
  interview_scraper: "Scraping interview experiences",
  signal_aggregator: "Aggregating interview signals",
  scorer: "Computing scores",
  done: "Done",
  error: "Error",
};

export interface ProgressStep {
  stage: string;
  progress: number;
}

export function ProgressStream({ steps, error }: { steps: ProgressStep[]; error?: string | null }) {
  if (steps.length === 0) return null;
  const latest = steps[steps.length - 1];

  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <div className="mb-2 h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div
          className="h-2 rounded-full bg-indigo-500 transition-all"
          style={{ width: `${Math.round(latest.progress * 100)}%` }}
        />
      </div>
      <ul className="space-y-1 text-sm">
        {steps.map((step, i) => (
          <li key={i} className="flex items-center gap-2 text-gray-600">
            <span className={i === steps.length - 1 ? "font-medium text-indigo-600" : ""}>
              {STAGE_LABELS[step.stage] ?? step.stage}
            </span>
            <span className="text-xs text-gray-400">{Math.round(step.progress * 100)}%</span>
          </li>
        ))}
      </ul>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
