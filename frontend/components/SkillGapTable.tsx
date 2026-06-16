import type { SkillMatch } from "@/lib/api";

const STATUS_DISPLAY: Record<SkillMatch["status"], { icon: string; className: string }> = {
  matched: { icon: "✓", className: "text-green-600" },
  partial: { icon: "⚠", className: "text-amber-600" },
  missing: { icon: "✗", className: "text-red-600" },
};

export function SkillGapTable({ matches }: { matches: SkillMatch[] }) {
  if (matches.length === 0) {
    return <p className="text-sm text-gray-500">No required skills were extracted from the JD.</p>;
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-gray-200 text-left text-gray-500">
          <th className="py-2">Skill</th>
          <th className="py-2">Status</th>
          <th className="py-2">Similarity</th>
        </tr>
      </thead>
      <tbody>
        {matches.map((m) => {
          const display = STATUS_DISPLAY[m.status];
          return (
            <tr key={m.skill} className="border-b border-gray-100">
              <td className="py-2 font-medium text-gray-800">{m.skill}</td>
              <td className={`py-2 ${display.className}`}>
                {display.icon} {m.status}
              </td>
              <td className="py-2 text-gray-500">{m.similarity.toFixed(2)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
