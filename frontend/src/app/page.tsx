"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { createAssessment, subscribeToProgress, type ProgressUpdate } from "@/lib/api";

type Step = "landing" | "business" | "questionnaire" | "processing" | "report" | "schedule";

interface AssessmentFormData {
  company_name: string;
  website_url: string;
  email: string;
  phone: string;
  industry: string;
  target_audience: string;
  content_frequency: string;
  traffic_sources: string[];
  competitors: string[];
  goals: string[];
  consent: boolean;
}

const INDUSTRIES = [
  { value: "saas", label: "SaaS / Software" },
  { value: "agency", label: "Marketing Agency" },
  { value: "ecommerce", label: "E-commerce" },
  { value: "professional_services", label: "Professional Services" },
  { value: "healthcare", label: "Healthcare" },
  { value: "finance", label: "Finance" },
  { value: "manufacturing", label: "Manufacturing" },
  { value: "other", label: "Other" },
];

const TRAFFIC_SOURCES = [
  { value: "google_search", label: "Google search" },
  { value: "social_media", label: "Social media" },
  { value: "referrals", label: "Referrals / word of mouth" },
  { value: "paid_ads", label: "Paid ads" },
  { value: "email", label: "Email marketing" },
  { value: "direct", label: "Direct traffic" },
  { value: "ai_tools", label: "AI tools (ChatGPT, etc.)" },
];

const GOALS = [
  { value: "get_found_by_ai", label: "Get found by more AI tools" },
  { value: "get_quoted_in_ai", label: "Get quoted in AI answers" },
  { value: "understand_visibility", label: "Understand my current visibility" },
  { value: "compare_to_competitors", label: "See how I compare to competitors" },
  { value: "improve_website_for_ai", label: "Improve my website for AI discovery" },
];

export default function Home() {
  const [step, setStep] = useState<Step>("landing");
  const [formData, setFormData] = useState<AssessmentFormData>({
    company_name: "", website_url: "", email: "", phone: "",
    industry: "", target_audience: "", content_frequency: "",
    traffic_sources: [], competitors: [], goals: [], consent: false,
  });
  const [assessmentId, setAssessmentId] = useState<string>("");
  const [progress, setProgress] = useState<ProgressUpdate>({ progress: 0, step: "" });
  const [error, setError] = useState<string>("");
  const [questionStep, setQuestionStep] = useState(0);

  const handleSubmit = async () => {
    setError("");
    setStep("processing");
    setProgress({ progress: 0, step: "Starting..." });

    try {
      const assessment = await createAssessment(formData as unknown as Record<string, unknown>);
      setAssessmentId(assessment.id);

      // Subscribe to progress updates
      subscribeToProgress(
        assessment.id,
        (data) => setProgress(data),
        () => setTimeout(() => setStep("report"), 500),
        (err: Error) => setError(err.message),
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setStep("business");
    }
  };

  const toggleArrayItem = (field: "traffic_sources" | "goals" | "competitors", value: string) => {
    setFormData((prev) => {
      const arr = prev[field] as string[];
      return {
        ...prev,
        [field]: arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value],
      };
    });
  };

  // --- Landing Screen ---
  if (step === "landing") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center max-w-3xl">
          <h1 className="text-5xl md:text-6xl font-bold mb-6">
            See How <span className="gradient-text">AI Tools</span><br />Discover Your Business
          </h1>
          <p className="text-xl text-gray-400 mb-8 leading-relaxed">
            ChatGPT, Gemini, Claude, Perplexity, and Google AI are changing how customers find you.
            Get your free AI Visibility Assessment and see how you stack up — with a personalized report and actionable steps.
          </p>
          <button
            onClick={() => setStep("business")}
            className="px-8 py-4 bg-gradient-to-r from-webpulse-pink to-webpulse-purple text-white text-lg font-bold rounded-xl hover:scale-105 transition-transform shadow-lg shadow-webpulse-purple/30"
          >
            Start Free Assessment →
          </button>
          <p className="text-sm text-gray-600 mt-4">No credit card required · Results in 60 seconds</p>
        </motion.div>
      </div>
    );
  }

  // --- Business Info Screen ---
  if (step === "business") {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} className="w-full max-w-xl">
          <h2 className="text-3xl font-bold mb-2">Tell us about your business</h2>
          <p className="text-gray-400 mb-8">We&apos;ll analyze your website and show you how AI tools discover it.</p>

          <div className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Company name *</label>
              <input
                type="text" required value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                className="w-full px-4 py-3 bg-webpulse-card border border-gray-700 rounded-lg focus:border-webpulse-teal focus:outline-none text-white"
                placeholder="Acme Corp"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Website URL *</label>
              <input
                type="url" required value={formData.website_url}
                onChange={(e) => setFormData({ ...formData, website_url: e.target.value })}
                className="w-full px-4 py-3 bg-webpulse-card border border-gray-700 rounded-lg focus:border-webpulse-teal focus:outline-none text-white"
                placeholder="https://acmecorp.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Work email *</label>
              <input
                type="email" required value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full px-4 py-3 bg-webpulse-card border border-gray-700 rounded-lg focus:border-webpulse-teal focus:outline-none text-white"
                placeholder="you@acmecorp.com"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Phone (optional)</label>
              <input
                type="tel" value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="w-full px-4 py-3 bg-webpulse-card border border-gray-700 rounded-lg focus:border-webpulse-teal focus:outline-none text-white"
                placeholder="+1-555-0100"
              />
            </div>
            <div className="flex items-start gap-3">
              <input
                type="checkbox" id="consent" checked={formData.consent}
                onChange={(e) => setFormData({ ...formData, consent: e.target.checked })}
                className="mt-1 w-5 h-5 accent-webpulse-teal"
              />
              <label htmlFor="consent" className="text-sm text-gray-400">
                I agree to receive my assessment results and follow-up communications from WebPulse. I can unsubscribe at any time.
              </label>
            </div>
          </div>

          <div className="flex gap-3 mt-8">
            <button
              onClick={() => setStep("landing")}
              className="px-6 py-3 text-gray-400 hover:text-white transition"
            >← Back</button>
            <button
              onClick={() => setStep("questionnaire")}
              disabled={!formData.company_name || !formData.website_url || !formData.email || !formData.consent}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-webpulse-pink to-webpulse-purple text-white font-bold rounded-lg disabled:opacity-40 disabled:cursor-not-allowed hover:scale-[1.02] transition"
            >Continue →</button>
          </div>
          {error && <p className="text-red-400 mt-4 text-sm">{error}</p>}
        </motion.div>
      </div>
    );
  }

  // --- Questionnaire Screen ---
  if (step === "questionnaire") {
    const questions = [
      { title: "What industry are you in?", content: (
        <div className="grid grid-cols-2 gap-3">
          {INDUSTRIES.map((ind) => (
            <button key={ind.value} onClick={() => { setFormData({ ...formData, industry: ind.value }); setQuestionStep(1); }}
              className={`px-4 py-3 rounded-lg border text-left transition ${formData.industry === ind.value ? "border-webpulse-teal bg-webpulse-teal/10 text-white" : "border-gray-700 text-gray-400 hover:border-gray-500"}`}>
              {ind.label}
            </button>
          ))}
        </div>
      )},
      { title: "Who are your customers?", content: (
        <div>
          <textarea value={formData.target_audience}
            onChange={(e) => setFormData({ ...formData, target_audience: e.target.value })}
            className="w-full px-4 py-3 bg-webpulse-card border border-gray-700 rounded-lg focus:border-webpulse-teal focus:outline-none text-white min-h-[120px]"
            placeholder="Describe your ideal customer — who they are, what they need, what they're looking for..." />
          <button onClick={() => setQuestionStep(2)} disabled={formData.target_audience.length < 5}
            className="mt-4 px-6 py-2 bg-webpulse-purple text-white rounded-lg disabled:opacity-40">Continue →</button>
        </div>
      )},
      { title: "How often do you publish new content?", content: (
        <div className="space-y-3">
          {["weekly", "monthly", "rarely", "never"].map((freq) => (
            <button key={freq} onClick={() => { setFormData({ ...formData, content_frequency: freq }); setQuestionStep(3); }}
              className={`w-full px-4 py-3 rounded-lg border text-left capitalize transition ${formData.content_frequency === freq ? "border-webpulse-teal bg-webpulse-teal/10" : "border-gray-700 hover:border-gray-500"}`}>
              {freq}
            </button>
          ))}
        </div>
      )},
      { title: "Where do your customers find you today?", content: (
        <div>
          <div className="space-y-3">
            {TRAFFIC_SOURCES.map((src) => (
              <label key={src.value} className="flex items-center gap-3 px-4 py-3 bg-webpulse-card rounded-lg cursor-pointer hover:bg-webpulse-card/80">
                <input type="checkbox" checked={formData.traffic_sources.includes(src.value)}
                  onChange={() => toggleArrayItem("traffic_sources", src.value)}
                  className="w-5 h-5 accent-webpulse-teal" />
                <span>{src.label}</span>
              </label>
            ))}
          </div>
          <button onClick={() => setQuestionStep(4)} disabled={formData.traffic_sources.length === 0}
            className="mt-4 px-6 py-2 bg-webpulse-purple text-white rounded-lg disabled:opacity-40">Continue →</button>
        </div>
      )},
      { title: "Who are your top competitors?", content: (
        <div>
          <div className="space-y-3">
            {[0, 1, 2].map((i) => (
              <input key={i} type="text" placeholder={`Competitor ${i + 1} (website or name)`}
                onChange={(e) => {
                  const comps = [...formData.competitors];
                  comps[i] = e.target.value;
                  setFormData({ ...formData, competitors: comps.filter((c) => c.trim()) });
                }}
                className="w-full px-4 py-3 bg-webpulse-card border border-gray-700 rounded-lg focus:border-webpulse-teal focus:outline-none text-white" />
            ))}
          </div>
          <button onClick={() => setQuestionStep(5)} className="mt-4 px-6 py-2 bg-webpulse-purple text-white rounded-lg">Continue →</button>
        </div>
      )},
      { title: "What's your main goal?", content: (
        <div>
          <div className="space-y-3">
            {GOALS.map((goal) => (
              <label key={goal.value} className="flex items-center gap-3 px-4 py-3 bg-webpulse-card rounded-lg cursor-pointer hover:bg-webpulse-card/80">
                <input type="checkbox" checked={formData.goals.includes(goal.value)}
                  onChange={() => toggleArrayItem("goals", goal.value)}
                  className="w-5 h-5 accent-webpulse-teal" />
                <span>{goal.label}</span>
              </label>
            ))}
          </div>
          <button onClick={handleSubmit} disabled={formData.goals.length === 0}
            className="mt-6 w-full px-8 py-4 bg-gradient-to-r from-webpulse-pink to-webpulse-purple text-white text-lg font-bold rounded-xl disabled:opacity-40 hover:scale-[1.02] transition">
            Get My AI Visibility Score →
          </button>
        </div>
      )},
    ];

    const q = questions[questionStep];
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <motion.div key={questionStep} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} className="w-full max-w-xl">
          <div className="mb-6 flex items-center gap-2">
            {questions.map((_, i) => (
              <div key={i} className={`h-1 flex-1 rounded-full ${i <= questionStep ? "bg-webpulse-teal" : "bg-gray-700"}`} />
            ))}
          </div>
          <h2 className="text-2xl font-bold mb-6">{q.title}</h2>
          {q.content}
        </motion.div>
      </div>
    );
  }

  // --- Processing Screen ---
  if (step === "processing") {
    const stepText = progress.step || "Starting...";
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center max-w-md">
          <div className="relative w-32 h-32 mx-auto mb-8">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              className="w-32 h-32 rounded-full border-4 border-webpulse-card border-t-webpulse-pink border-r-webpulse-purple" />
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-2xl font-bold text-webpulse-teal">{progress.progress}%</span>
            </div>
          </div>
          <motion.h2 key={stepText} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
            className="text-xl text-gray-300 mb-2">{stepText}</motion.h2>
          <p className="text-gray-500 text-sm">This usually takes 30-60 seconds</p>
          {error && <p className="text-red-400 mt-4 text-sm">{error}</p>}
        </motion.div>
      </div>
    );
  }

  // --- Report Screen ---
  if (step === "report") {
    return (
      <ReportPage assessmentId={assessmentId} onSchedule={() => setStep("schedule")} />
    );
  }

  // --- Schedule Screen ---
  if (step === "schedule") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center max-w-lg">
          <h1 className="text-4xl font-bold mb-4">Let&apos;s turn insights into action</h1>
          <p className="text-gray-400 text-lg mb-8">
            Book a free 30-minute strategy session. We&apos;ll walk through your AI Visibility Score,
            your top opportunities, and a plan to get AI tools discovering and recommending your business.
          </p>
          {/* Calendly embed */}
          <div className="bg-webpulse-card rounded-2xl p-2">
            <div className="calendly-inline-widget" data-url="https://calendly.com/gerald-webpulse/30min"
              style={{ minWidth: 320, height: 700 }} />
          </div>
          <p className="text-gray-500 text-sm mt-4">
            Prefer email? Your full report has been sent to your inbox.
          </p>
        </motion.div>
      </div>
    );
  }

  return null;
}

// --- Report Page Component ---
function ReportPage({ assessmentId, onSchedule }: { assessmentId: string; onSchedule: () => void }) {
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    // Poll for report
    const poll = async () => {
      for (let i = 0; i < 30; i++) {
        try {
          const r = await fetch(`/api/v1/assessments/${assessmentId}/report`);
          if (r.ok) { setReport(await r.json()); setLoading(false); return; }
        } catch (e) { /* retry */ }
        await new Promise((res) => setTimeout(res, 2000));
      }
      setError("Report is still generating. Check your email — we'll send it when it's ready.");
      setLoading(false);
    };
    poll();
  }, [assessmentId]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 border-4 border-webpulse-card border-t-webpulse-teal rounded-full animate-spin" />
          <p className="text-gray-400">Loading your report...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <p className="text-gray-400 mb-4">{error || "Unable to load report"}</p>
          <p className="text-gray-500 text-sm">We&apos;ve emailed your report to you. Check your inbox!</p>
        </div>
      </div>
    );
  }

  const score = report.visibility_score;
  const scoreColor = score >= 70 ? "#00d4a1" : score >= 40 ? "#7209B7" : "#F72585";
  const categoryLabels: Record<string, string> = {
    ai_crawler_access: "Can AI Tools Find Your Site?",
    llms_txt: "AI Content Guide",
    structured_data: "Content Structure",
    content_inventory: "Content Volume & Depth",
    homepage_messaging: "Clear Business Description",
    entity_signals: "Credibility Signals",
    offsite_authority: "External Recognition",
    contact_nap: "Contact Consistency",
    page_speed: "Technical Performance",
    ai_search_presence: "AI Search Presence",
  };
  const statusColors: Record<string, string> = {
    good: "text-webpulse-teal", warning: "text-yellow-400", critical: "text-red-400",
  };
  const difficultyColors: Record<string, string> = {
    easy: "bg-green-500/20 text-green-400", medium: "bg-yellow-500/20 text-yellow-400", hard: "bg-red-500/20 text-red-400",
  };
  const impactColors: Record<string, string> = {
    low: "bg-gray-500/20 text-gray-400", medium: "bg-blue-500/20 text-blue-400", high: "bg-webpulse-teal/20 text-webpulse-teal",
  };

  return (
    <div className="min-h-screen px-4 py-12">
      <div className="max-w-4xl mx-auto">
        {/* Score */}
        <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="text-center mb-12">
          <h1 className="text-3xl font-bold mb-2">Your AI Visibility Score</h1>
          <div className="relative w-48 h-48 mx-auto my-8">
            <div className="score-gauge w-48 h-48 flex items-center justify-center"
              style={{ "--score-percentage": score, "--score-color": scoreColor } as any}>
              <div className="w-40 h-40 bg-webpulse-dark rounded-full flex items-center justify-center flex-col">
                <span className="text-6xl font-bold" style={{ color: scoreColor }}>{score}</span>
                <span className="text-gray-500 text-sm">out of 100</span>
              </div>
            </div>
          </div>
          <p className="text-lg text-gray-300 max-w-2xl mx-auto">{report.summary}</p>
        </motion.div>

        {/* Category Scores */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          {Object.entries(report.category_scores || {}).map(([key, val]: [string, any]) => (
            <div key={key} className="bg-webpulse-card rounded-xl p-5">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-400">{categoryLabels[key] || key}</span>
                <span className="text-2xl font-bold" style={{ color: val >= 7 ? "#00d4a1" : val >= 4 ? "#7209B7" : "#F72585" }}>{val}<span className="text-sm text-gray-600">/10</span></span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div className="h-2 rounded-full" style={{ width: `${val * 10}%`, background: val >= 7 ? "#00d4a1" : val >= 4 ? "#7209B7" : "#F72585" }} />
              </div>
            </div>
          ))}
        </div>

        {/* Prioritized Actions */}
        <h2 className="text-2xl font-bold mb-6">Top Actions to Improve Your AI Discovery</h2>
        <div className="space-y-4 mb-12">
          {(report.actions || []).map((action: any, i: number) => (
            <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}
              className="bg-webpulse-card rounded-xl p-6 border-l-4" style={{ borderColor: i === 0 ? "#F72585" : i === 1 ? "#7209B7" : "#00d4a1" }}>
              <div className="flex justify-between items-start mb-3">
                <h3 className="text-lg font-bold">{action.priority}. {action.title}</h3>
                <div className="flex gap-2">
                  <span className={`px-2 py-1 text-xs rounded-full ${difficultyColors[action.difficulty] || ""}`}>{action.difficulty}</span>
                  <span className={`px-2 py-1 text-xs rounded-full ${impactColors[action.impact] || ""}`}>{action.impact} impact</span>
                </div>
              </div>
              <p className="text-gray-400">{action.description}</p>
            </motion.div>
          ))}
        </div>

        {/* Findings */}
        <h2 className="text-2xl font-bold mb-6">What We Found</h2>
        <div className="space-y-3 mb-12">
          {(report.findings || []).map((finding: any, i: number) => (
            <div key={i} className="bg-webpulse-card rounded-xl p-5">
              <div className="flex items-center gap-2 mb-2">
                <span className={`text-xl ${statusColors[finding.status] || "text-gray-400"}`}>
                  {finding.status === "good" ? "✓" : finding.status === "warning" ? "⚠" : "✗"}
                </span>
                <span className="text-sm font-medium text-gray-300">{categoryLabels[finding.category] || finding.category}</span>
              </div>
              <p className="text-gray-400 text-sm">{finding.observation}</p>
              <p className="text-gray-500 text-sm mt-1">{finding.what_it_means}</p>
            </div>
          ))}
        </div>

        {/* Unknowns */}
        {(report.unknowns || []).length > 0 && (
          <div className="mb-12">
            <h2 className="text-2xl font-bold mb-6">What We Couldn&apos;t Determine</h2>
            <div className="bg-webpulse-card rounded-xl p-6 border border-gray-700">
              <ul className="space-y-2">
                {report.unknowns.map((unknown: string, i: number) => (
                  <li key={i} className="text-gray-400 text-sm flex items-start gap-2">
                    <span className="text-gray-600">•</span> {unknown}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* Methodology */}
        <details className="mb-12">
          <summary className="text-gray-400 cursor-pointer hover:text-white">How we tested this</summary>
          <p className="text-gray-500 text-sm mt-4 max-w-2xl">{report.methodology}</p>
        </details>

        {/* CTA */}
        <div className="bg-gradient-to-br from-webpulse-darker to-webpulse-card rounded-2xl p-8 text-center border border-webpulse-purple/30">
          <h2 className="text-2xl font-bold mb-4">Ready to improve your AI visibility?</h2>
          <p className="text-gray-400 mb-6">Book a free strategy session. We&apos;ll walk through your results and build an action plan.</p>
          <button onClick={onSchedule}
            className="px-8 py-4 bg-gradient-to-r from-webpulse-pink to-webpulse-purple text-white text-lg font-bold rounded-xl hover:scale-105 transition shadow-lg shadow-webpulse-purple/30">
            Book Your Strategy Session →
          </button>
        </div>
      </div>
    </div>
  );
}
