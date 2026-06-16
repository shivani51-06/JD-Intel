/** Large composite-score display, color-coded red (<50) / amber (50-75) / green (>75). */
export function scoreColor(score: number): string {
  if (score < 50) return "text-score-low";
  if (score <= 75) return "text-score-mid";
  return "text-score-high";
}

export function scoreBgColor(score: number): string {
  if (score < 50) return "bg-score-low";
  if (score <= 75) return "bg-score-mid";
  return "bg-score-high";
}

export function ScoreCard({ label, score }: { label: string; score: number }) {
  return (
    <div className="rounded-lg border border-gray-200 p-6 text-center shadow-sm">
      <div className={`text-6xl font-bold ${scoreColor(score)}`}>{Math.round(score)}</div>
      <div className="mt-2 text-sm font-medium text-gray-500">{label}</div>
    </div>
  );
}

export function SectionScoreBar({ label, score }: { label: string; score: number }) {
  return (
    <div className="mb-2">
      <div className="mb-1 flex justify-between text-sm">
        <span className="font-medium text-gray-700">{label}</span>
        <span className="text-gray-500">{Math.round(score)}</span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-100">
        <div
          className={`h-2 rounded-full ${scoreBgColor(score)}`}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}
