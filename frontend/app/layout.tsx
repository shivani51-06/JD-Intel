import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "JD Intel — AI Resume Intelligence",
  description: "Score resumes against job descriptions and real interview experiences.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b border-gray-200 bg-white">
          <div className="mx-auto max-w-6xl px-6 py-4">
            <a href="/" className="text-lg font-semibold text-indigo-600">JD Intel</a>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
