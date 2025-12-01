"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import WizardLayout from "@/components/journal/WizardLayout";
import Step1Technical from "@/components/journal/Step1Technical";
import Step2GameLevel from "@/components/journal/Step2GameLevel";
import Step3MentalPattern from "@/components/journal/Step3MentalPattern";
import Step4RootCause from "@/components/journal/Step4RootCause";

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

  // Step 3 Data
  const [timelineEvents, setTimelineEvents] = useState<any[]>([]);
  const [mentalState, setMentalState] = useState({
    greed_level: 0,
    fear_level: 0,
    tilt_level: 0,
    confidence_level: 5,
    discipline_level: 5,
  });

  // Step 4 Data
  const [rootCause, setRootCause] = useState({
    problem: "",
    why_exist: "",
    flaw: "",
    correction: "",
    logic: "",
  });

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
      session: step1Data.session || null,
      entry_price: parseFloat(step1Data.entryPrice) || null,
      exit_price: parseFloat(step1Data.exitPrice) || null,
      pnl_amount: parseFloat(step1Data.pnl) || null,
      stop_loss_price: parseFloat(step1Data.stopLoss) || null,
      take_profit_price: parseFloat(step1Data.takeProfit) || null,
      risk_amount: parseFloat(step1Data.riskAmount) || null,
      context_score: step1Data.contextScore,
      game_level: gameLevel || null,
      mental_state: mentalState,
      timeline_events: timelineEvents,
      root_cause: {
        problem: rootCause.problem || null,
        why_exist: rootCause.why_exist || null,
        flaw: rootCause.flaw || null,
        correction: rootCause.correction || null,
        logic: rootCause.logic || null,
      },
    };

    try {
      const token = localStorage.getItem("token");
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${API_BASE_URL}/api/v1/journal/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        alert("Journal entry created successfully!");
        router.push("/");
      } else {
        const error = await res.json();
        alert(`Failed to create journal entry: ${JSON.stringify(error)}`);
      }
    } catch (error) {
      console.error("Error:", error);
      alert("Network error. Please try again.");
    }
  };

  return (
    <WizardLayout currentStep={currentStep} totalSteps={4}>
      {currentStep === 1 && (
        <Step1Technical data={step1Data} onChange={setStep1Data} onNext={handleNext} />
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
        <Step3MentalPattern
          timelineEvents={timelineEvents}
          mentalState={mentalState}
          onTimelineChange={setTimelineEvents}
          onMentalStateChange={setMentalState}
          onNext={handleNext}
          onBack={handleBack}
        />
      )}

      {currentStep === 4 && (
        <Step4RootCause
          rootCause={rootCause}
          onChange={setRootCause}
          onSubmit={handleSubmit}
          onBack={handleBack}
        />
      )}
    </WizardLayout>
  );
}
