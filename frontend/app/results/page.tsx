"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import * as Tabs from "@radix-ui/react-tabs";
import type { AnalysisReport } from "@/lib/api";
import { ScoreCard, SectionScoreBar } from "@/components/ScoreCard";
import { SkillRadarChart } from "@/components/RadarChart";
import { SkillGapTable } from "@/components/SkillGapTable";
import { BulletRewriter } from "@/components/BulletRewriter";

const TABS = [
  { id: "gaps", label: "Skill Gaps" },
  { id: "blindspots", label: "Interview Blindspots" },
  { id: "rewrites", label: "Bullet Rewrites" },
  { id: "parsability", label: "Parsability" },
];

export default function ResultsPage() {
  const router = useRouter();
  const [report, setReport] = useState<AnalysisReport | null>(null);

  useEffect(() => {
    const stored = sessionStorage.getItem("jd-intel-report");
    if (stored) {
      setReport(JSON.parse(stored));
    }
  }, []);

  if (!report) {
    return (
      <div className="text-center text-sm text-gray-500">
        <p>No report found for this session.</p>
        <button onClick={() => router.push("/")} className="mt-3 text-indigo-600 underline">
          Run a new analysis
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-5">
      <div className="space-y-6 lg:col-span-2">
        <ScoreCard label="Composite Score" score={report.composite_score} />
        <div className="grid grid-cols-3 gap-3 text-center text-xs text-gray-500">
          <div>
            <div className="text-lg font-semibold text-gray-800">{Math.round(report.jd_match_score)}</div>
            JD Match
          </div>
          <div>
            <div className="text-lg font-semibold text-gray-800">{Math.round(report.interview_coverage_score)}</div>
            Interview Coverage
          </div>
          <div>
            <div className="text-lg font-semibold text-gray-800">{Math.round(report.formatting_score)}</div>
            Formatting
          </div>
        </div>

        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Skill Coverage Radar</h2>
          <SkillRadarChart report={report} />
        </div>

        <div className="rounded-lg border border-gray-200 p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Section Scores</h2>
          {Object.entries(report.section_scores).map(([section, score]) => (
            <SectionScoreBar key={section} label={section} score={score} />
          ))}
        </div>

        {report.warnings.length > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-700">
            {report.warnings.map((w, i) => (
              <p key={i}>{w}</p>
            ))}
          </div>
        )}
      </div>

      <div className="lg:col-span-3">
        <Tabs.Root defaultValue="gaps">
          <Tabs.List className="mb-4 flex gap-1 border-b border-gray-200">
            {TABS.map((tab) => (
              <Tabs.Trigger
                key={tab.id}
                value={tab.id}
                className="rounded-t-md px-4 py-2 text-sm text-gray-500 data-[state=active]:border-b-2 data-[state=active]:border-indigo-600 data-[state=active]:text-indigo-600"
              >
                {tab.label}
              </Tabs.Trigger>
            ))}
          </Tabs.List>

          <Tabs.Content value="gaps">
            <SkillGapTable matches={report.skill_matches} />
            {report.missing_skills.length > 0 && (
              <p className="mt-3 text-xs text-gray-500">
                Missing: {report.missing_skills.join(", ")}
              </p>
            )}
          </Tabs.Content>

          <Tabs.Content value="blindspots">
            {report.interview_blindspots.length === 0 ? (
              <p className="text-sm text-gray-500">No interview blindspots detected.</p>
            ) : (
              <ul className="space-y-2">
                {report.interview_blindspots.map((topic) => (
                  <li key={topic} className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                    {topic} — frequently asked by real interviewers but not addressed in your JD or resume.
                  </li>
                ))}
              </ul>
            )}
            <div className="mt-4">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">Top interview topics</h3>
              <div className="flex flex-wrap gap-2">
                {report.top_interview_topics.map((topic) => (
                  <span key={topic} className="rounded-full bg-gray-100 px-3 py-1 text-xs text-gray-600">
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          </Tabs.Content>

          <Tabs.Content value="rewrites">
            <BulletRewriter suggestions={report.bullet_suggestions} />
          </Tabs.Content>

          <Tabs.Content value="parsability">
            {report.parsability_issues.length === 0 ? (
              <p className="text-sm text-gray-500">No parsability issues detected.</p>
            ) : (
              <ul className="space-y-2">
                {report.parsability_issues.map((issue, i) => (
                  <li key={i} className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                    {issue}
                  </li>
                ))}
              </ul>
            )}
          </Tabs.Content>
        </Tabs.Root>
      </div>
    </div>
  );
}
