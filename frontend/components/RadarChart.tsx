"use client";

import {
  Radar,
  RadarChart as ReRadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import type { AnalysisReport } from "@/lib/api";

/** 5-axis radar: JD Match, Interview Coverage, Projects, Experience, Skills. */
export function SkillRadarChart({ report }: { report: AnalysisReport }) {
  const data = [
    { axis: "JD Match", value: report.jd_match_score },
    { axis: "Interview Coverage", value: report.interview_coverage_score },
    { axis: "Projects", value: report.section_scores?.projects ?? 0 },
    { axis: "Experience", value: report.section_scores?.experience ?? 0 },
    { axis: "Skills", value: report.section_scores?.skills ?? 0 },
  ];

  return (
    <div className="h-80 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ReRadarChart data={data} outerRadius="75%">
          <PolarGrid />
          <PolarAngleAxis dataKey="axis" tick={{ fontSize: 12 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fontSize: 10 }} />
          <Radar name="Score" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.4} />
        </ReRadarChart>
      </ResponsiveContainer>
    </div>
  );
}
