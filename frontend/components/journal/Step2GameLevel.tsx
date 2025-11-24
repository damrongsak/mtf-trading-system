"use client";

interface Step2Props {
  gameLevel: string;
  onChange: (level: string) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Step2GameLevel({ gameLevel, onChange, onNext, onBack }: Step2Props) {
  const gameLevels = [
    {
      level: "A_GAME",
      emoji: "🟢",
      title: "A-Game (Learning Mistake)",
      description: "I did my best, but didn't know enough. This was a tactical learning opportunity."
    },
    {
      level: "B_GAME",
      emoji: "🟡",
      title: "B-Game (Marginal Mistake)",
      description: "I got sloppy or slightly emotional. Mix of tactical weakness and mental flaws."
    },
    {
      level: "C_GAME",
      emoji: "🔴",
      title: "C-Game (Obvious Mistake)",
      description: "I lost control / Tilted. Pure mental/emotional breakdown. Nothing to learn tactically."
    }
  ];

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">How was your execution?</h2>
        <p className="text-gray-400">Select the category that best describes this trade</p>
      </div>

      <div className="grid gap-4">
        {gameLevels.map((item) => (
          <button
            key={item.level}
            type="button"
            onClick={() => onChange(item.level)}
            className={`p-6 rounded-xl border-2 text-left transition-all ${
              gameLevel === item.level
                ? "border-emerald-500 bg-emerald-500/10 shadow-lg shadow-emerald-500/20"
                : "border-gray-800 bg-gray-900 hover:border-gray-700"
            }`}
          >
            <div className="flex items-start gap-4">
              <span className="text-4xl">{item.emoji}</span>
              <div className="flex-1">
                <h3 className={`text-lg font-bold mb-2 ${gameLevel === item.level ? "text-emerald-400" : "text-white"}`}>
                  {item.title}
                </h3>
                <p className="text-gray-400 text-sm">{item.description}</p>
              </div>
              {gameLevel === item.level && (
                <div className="flex-shrink-0">
                  <div className="w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center">
                    <svg className="w-4 h-4 text-gray-900" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              )}
            </div>
          </button>
        ))}
      </div>

      <div className="flex gap-4 mt-8">
        <button
          onClick={onBack}
          className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={onNext}
          disabled={!gameLevel}
          className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 disabled:bg-gray-800 disabled:text-gray-600 text-gray-900 font-bold rounded-lg transition-colors"
        >
          Next: Mental Pattern →
        </button>
      </div>
    </div>
  );
}
