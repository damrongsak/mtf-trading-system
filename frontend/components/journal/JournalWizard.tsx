"use client";

import { useState, useEffect } from "react";
import type { JournalEntry, CreateJournalEntryDto, TimelineEvent } from "@/lib/api/types";
import { getPreferences } from "@/lib/api";
import WizardLayout from "@/components/journal/WizardLayout";
import Step1Technical from "@/components/journal/Step1Technical";
import Step2GameLevel from "@/components/journal/Step2GameLevel";
import Step3MentalPattern from "@/components/journal/Step3MentalPattern";
import Step4RootCause from "@/components/journal/Step4RootCause";

interface JournalWizardProps {
  initialData?: Partial<JournalEntry> & {
    mental_state?: any;
    timeline_events?: any[];
    root_cause?: any;
  };
  onSubmit: (data: CreateJournalEntryDto) => Promise<void>;
  isSubmitting?: boolean;
}

export default function JournalWizard({ initialData, onSubmit, isSubmitting = false }: JournalWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [supportedSymbols, setSupportedSymbols] = useState<string[]>([]);

  useEffect(() => {
    const fetchSymbols = async () => {
        try {
            const prefs = await getPreferences();
            if (prefs.supported_symbols) {
                setSupportedSymbols(prefs.supported_symbols);
            }
        } catch (error) {
            console.error('Failed to load supported symbols', error);
        }
    };
    fetchSymbols();
  }, []);

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
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
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

  // Initialize data if provided (for edit mode)
  useEffect(() => {
    if (initialData) {
      setStep1Data({
        symbol: initialData.symbol || "XAU/USD",
        direction: initialData.direction || "LONG",
        session: initialData.session || "",
        entryPrice: initialData.entry_price?.toString() || "",
        stopLoss: initialData.stop_loss_price?.toString() || "",
        takeProfit: initialData.take_profit_price?.toString() || "",
        riskAmount: initialData.risk_amount?.toString() || "",
        exitPrice: initialData.exit_price?.toString() || "",
        pnl: initialData.pnl_amount?.toString() || "",
        contextScore: initialData.context_score || 5,
      });

      if (initialData.game_level) setGameLevel(initialData.game_level);
      
      // Note: These nested fields might need adjustment depending on how backend returns them
      // Assuming the backend returns them in a compatible format or we map them before passing initialData
      if (initialData.timeline_events) setTimelineEvents(initialData.timeline_events);
      if (initialData.mental_state) setMentalState(initialData.mental_state);
      if (initialData.root_cause) {
        setRootCause({
          problem: initialData.root_cause.problem || "",
          why_exist: initialData.root_cause.why_exist || "",
          flaw: initialData.root_cause.flaw || "",
          correction: initialData.root_cause.correction || "",
          logic: initialData.root_cause.logic || "",
        });
      }
    }
  }, [initialData]);

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
    const payload: CreateJournalEntryDto = {
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

    await onSubmit(payload);
  };

  return (
    <WizardLayout currentStep={currentStep} totalSteps={4}>
      {currentStep === 1 && (
        <Step1Technical 
            data={step1Data} 
            onChange={setStep1Data} 
            onNext={handleNext} 
            supportedSymbols={supportedSymbols}
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
          isSubmitting={isSubmitting}
        />
      )}
    </WizardLayout>
  );
}
