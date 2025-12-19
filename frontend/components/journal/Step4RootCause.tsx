"use client";

interface RootCause {
  problem: string;
  why_exist: string;
  flaw: string;
  correction: string;
  logic: string;
}

interface Step4Props {
  rootCause: RootCause;
  onChange: (data: RootCause) => void;
  onSubmit: () => void;
  onBack: () => void;
}

export default function Step4RootCause({ rootCause, onChange, onSubmit, onBack }: Step4Props) {
  const updateField = (field: keyof RootCause, value: string) => {
    onChange({ ...rootCause, [field]: value });
  };

  const fields = [
    {
      key: "problem" as keyof RootCause,
      label: "1. What's the problem?",
      placeholder: "E.g., I have a need for a trade to be green right from the beginning",
      icon: "🎯"
    },
    {
      key: "why_exist" as keyof RootCause,
      label: "2. Why does the problem exist?",
      placeholder: "E.g., Every loss feels like a step backward, delaying my goals",
      icon: "❓"
    },
    {
      key: "flaw" as keyof RootCause,
      label: "3. What is flawed?",
      placeholder: "E.g., Unreasonable expectation, Black-and-white thinking, need to control every outcome",
      icon: "⚠️"
    },
    {
      key: "correction" as keyof RootCause,
      label: "4. What's the correction? (Real-time Strategy)",
      placeholder: "E.g., Stay focused on quality execution, build a productive routine",
      icon: "🔧"
    },
    {
      key: "logic" as keyof RootCause,
      label: "5. What logic confirms that correction?",
      placeholder: "E.g., Quality execution in the short term is how I get what I want in the long run. Losses and drawdowns are part of the game.",
      icon: "💡"
    }
  ];

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-white mb-2">Root Cause Analysis</h2>
        <p className="text-gray-400">The &ldquo;Mental Hand History&rdquo; - Structured self-coaching</p>
      </div>

      <div className="space-y-4">
        {fields.map(({ key, label, placeholder, icon }) => (
          <div key={key} className="bg-gray-900 p-6 rounded-xl border border-gray-800">
            <label className="flex items-center gap-2 text-lg font-bold text-emerald-400 mb-3">
              <span>{icon}</span>
              {label}
            </label>
            <textarea
              value={rootCause[key] || ''}
              onChange={(e) => updateField(key, e.target.value)}
              placeholder={placeholder}
              rows={3}
              className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none text-white placeholder-gray-500 resize-none"
            />
          </div>
        ))}
      </div>

      <div className="bg-emerald-900/20 border border-emerald-700 rounded-xl p-4 mt-6">
        <p className="text-emerald-400 text-sm">
          <strong>💡 Tip:</strong> The AI will use this structured data to identify patterns and help you build better habits over time.
        </p>
      </div>

      <div className="flex gap-4 mt-8">
        <button
          onClick={onBack}
          className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={onSubmit}
          className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-bold rounded-lg transition-colors"
        >
          Submit Journal Entry ✓
        </button>
      </div>
    </div>
  );
}
