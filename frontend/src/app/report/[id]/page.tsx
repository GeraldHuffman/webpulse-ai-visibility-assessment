"use client";

import { useEffect, useState } from "react";
import { use } from "react";
import { getReport, type ReportData } from "@/lib/api";

export default function ReportRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      for (let i = 0; i < 30; i++) {
        try {
          const r = await getReport(id);
          setReport(r);
          setLoading(false);
          return;
        } catch {
          await new Promise((res) => setTimeout(res, 2000));
        }
      }
      setError("Report not ready yet. Check your email — we sent it there too.");
      setLoading(false);
    };
    load();
  }, [id]);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="text-gray-400">Loading report...</div></div>;
  if (error || !report) return <div className="min-h-screen flex items-center justify-center"><div className="text-gray-400">{error || "Not found"}</div></div>;

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold mb-4">Your AI Visibility Score</h1>
          <div className="text-6xl font-bold" style={{ color: report.visibility_score >= 70 ? "#00d4a1" : report.visibility_score >= 40 ? "#7209B7" : "#F72585" }}>
            {report.visibility_score}<span className="text-2xl text-gray-600">/100</span>
          </div>
          <p className="text-gray-400 max-w-2xl mx-auto mt-4">{report.summary}</p>
        </div>

        <div className="bg-gradient-to-br from-webpulse-darker to-webpulse-card rounded-2xl p-8 text-center border border-webpulse-purple/30 mt-12">
          <h2 className="text-2xl font-bold mb-4">Book Your Strategy Session</h2>
          <p className="text-gray-400 mb-6">Walk through your results with a WebPulse AI visibility expert.</p>
          <a href={`/schedule?id=${id}`} className="inline-block px-8 py-4 bg-gradient-to-r from-webpulse-pink to-webpulse-purple text-white text-lg font-bold rounded-xl hover:scale-105 transition">
            Schedule a Call →
          </a>
        </div>
      </div>
    </div>
  );
}
