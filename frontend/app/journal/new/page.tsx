"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import WizardLayout from "@/components/journal/WizardLayout";
import Step1Technical from "@/components/journal/Step1Technical";
import Step2GameLevel from "@/components/journal/Step2GameLevel";

export default function NewJournalPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);

  // Step 1 Data
  const [step1Data, setStep1Data] = useState({
    symbol: "XAU/USD",
    direction: "LONG",
    session: "",
    entryPrice: "",
    stopLoss: "",
    takeProfit: "",
    riskAmount: "",
    exitPrice: "",
    pnl: "",
    contextScore: 5,
  });

  // Step 2 Data
  const [gameLevel, setGameLevel] = useState("");

  const handleNext = () => {
    if (currentStep < 4) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    const payload = {
      symbol: step1Data.symbol,
      direction: step1Data.direction,
      session: step1Data.session,
      entry_price: parseFloat(step1Data.entryPrice) || null,
      exit_price: parseFloat(step1Data.exitPrice) || null,
      pnl_amount: parseFloat(step1Data.pnl) || null,
      stop_loss_price: parseFloat(step1Data.stopLoss) || null,
      take_profit_price: parseFloat(step1Data.takeProfit) || null,
      risk_amount: parseFloat(step1Data.riskAmount) || null,
      context_score: step1Data.contextScore,
      game_level: gameLevel || null,
    };

    try {
      const token = localStorage.getItem("token");
      const res = await fetch("http://localhost:8000/api/v1/journal/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        router.push("/journal");
      } else {
        console.error("Failed to create journal entry");
      }
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    <WizardLayout currentStep={currentStep} totalSteps={4}>
      {currentStep === 1 && (
        <Step1Technical
          data={step1Data}
          onChange={setStep1Data}
          onNext={handleNext}
        />
      )}

      {currentStep === 2 && (
        <Step2GameLevel
          gameLevel={gameLevel}
          onChange={setGameLevel}
          onNext={handleNext}
          onBack={handleBack}
        />
      )}

      {currentStep === 3 && (
        <div className="text-center">
          <p className="text-gray-400">Mental Pattern (Timeline) - Coming Soon</p>
          <div className="flex gap-4 mt-8">
            <button onClick={handleBack} className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg">
              ← Back
            </button>
            <button onClick={handleNext} className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-bold rounded-lg">
              Next: Root Cause →
            </button>
          </div>
        </div>
      )}

      {currentStep === 4 && (
        <div className="text-center">
          <p className="text-gray-400">Root Cause Analysis - Coming Soon</p>
          <div className="flex gap-4 mt-8">
            <button onClick={handleBack} className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg">
              ← Back
            </button>
            <button
              onClick={handleSubmit}
              className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-bold rounded-lg"
            >
              Submit Journal Entry
            </button>
          </div>
        </div>
      )}
    </WizardLayout>
  );
}
