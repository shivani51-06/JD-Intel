"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { analyzeResume, type AgentProgressEvent, type AnalysisReport } from "@/lib/api";
import { ProgressStream, type ProgressStep } from "@/components/ProgressStream";

const formSchema = z.object({
  resumeText: z.string().optional(),
  jdMode: z.enum(["paste", "url"]),
  jd: z.string().min(1, "Job description is required"),
  company: z.string().min(1, "Company is required"),
  role: z.string().min(1, "Role is required"),
});

type FormValues = z.infer<typeof formSchema>;

export default function UploadPage() {
  const router = useRouter();
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [inputMode, setInputMode] = useState<"file" | "paste">("file");
  const [steps, setSteps] = useState<ProgressStep[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: { jdMode: "paste" },
  });

  const jdMode = watch("jdMode");

  const onSubmit = async (values: FormValues) => {
    if (inputMode === "file" && !resumeFile) {
      setError("Upload a resume file or switch to paste mode.");
      return;
    }
    if (inputMode === "paste" && !values.resumeText?.trim()) {
      setError("Paste your resume text or switch to file upload.");
      return;
    }

    setError(null);
    setSubmitting(true);
    setSteps([]);

    let finalReport: AnalysisReport | null = null;
    let streamError: string | null = null;

    try {
      await analyzeResume(
        {
          resumeFile: inputMode === "file" ? resumeFile : null,
          resumeText: inputMode === "paste" ? values.resumeText : undefined,
          jd: values.jd,
          company: values.company,
          role: values.role,
        },
        (event: AgentProgressEvent) => {
          if (event.type === "error") {
            streamError = event.detail ?? "Analysis failed";
            setError(streamError);
            return;
          }
          if (event.type === "done") {
            finalReport = event.report ?? null;
            return;
          }
          setSteps((prev) => [...prev, { stage: event.agent ?? "starting", progress: event.progress ?? 0 }]);
        }
      );

      if (finalReport) {
        sessionStorage.setItem("jd-intel-report", JSON.stringify(finalReport));
        router.push("/results");
      } else if (!streamError) {
        setError("Analysis finished without producing a report.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error during analysis");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-semibold">Analyze your resume</h1>
      <p className="mt-1 text-sm text-gray-500">
        Score your resume against a job description and real interview experiences from Glassdoor, LeetCode, and Reddit.
      </p>

      <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-6">
        <div>
          <div className="mb-2 flex gap-2">
            <button
              type="button"
              onClick={() => setInputMode("file")}
              className={`rounded px-3 py-1.5 text-sm ${inputMode === "file" ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600"}`}
            >
              Upload file
            </button>
            <button
              type="button"
              onClick={() => setInputMode("paste")}
              className={`rounded px-3 py-1.5 text-sm ${inputMode === "paste" ? "bg-indigo-600 text-white" : "bg-gray-100 text-gray-600"}`}
            >
              Paste text
            </button>
          </div>

          {inputMode === "file" ? (
            <label className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 hover:border-indigo-400">
              <span>{resumeFile ? resumeFile.name : "Click or drag a PDF/DOCX/TXT resume here"}</span>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                className="hidden"
                onChange={(e) => setResumeFile(e.target.files?.[0] ?? null)}
              />
            </label>
          ) : (
            <textarea
              {...register("resumeText")}
              rows={8}
              placeholder="Paste your resume text here..."
              className="w-full rounded-lg border border-gray-300 p-3 text-sm"
            />
          )}
        </div>

        <div>
          <div className="mb-2 flex gap-2 text-sm">
            <label className="flex items-center gap-1">
              <input type="radio" value="paste" {...register("jdMode")} defaultChecked /> Paste JD text
            </label>
            <label className="flex items-center gap-1">
              <input type="radio" value="url" {...register("jdMode")} /> JD URL
            </label>
          </div>
          {jdMode === "url" ? (
            <input
              {...register("jd")}
              placeholder="https://company.com/careers/job-id"
              className="w-full rounded-lg border border-gray-300 p-3 text-sm"
            />
          ) : (
            <textarea
              {...register("jd")}
              rows={6}
              placeholder="Paste the job description here..."
              className="w-full rounded-lg border border-gray-300 p-3 text-sm"
            />
          )}
          {errors.jd && <p className="mt-1 text-xs text-red-600">{errors.jd.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <input
              {...register("company")}
              placeholder="Company name (e.g. Google)"
              className="w-full rounded-lg border border-gray-300 p-3 text-sm"
            />
            {errors.company && <p className="mt-1 text-xs text-red-600">{errors.company.message}</p>}
          </div>
          <div>
            <input
              {...register("role")}
              placeholder="Role title (e.g. ML Engineer)"
              className="w-full rounded-lg border border-gray-300 p-3 text-sm"
            />
            {errors.role && <p className="mt-1 text-xs text-red-600">{errors.role.message}</p>}
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {submitting ? "Analyzing..." : "Analyze Resume"}
        </button>
      </form>

      {steps.length > 0 && (
        <div className="mt-6">
          <ProgressStream steps={steps} error={error} />
        </div>
      )}
      {error && steps.length === 0 && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}
