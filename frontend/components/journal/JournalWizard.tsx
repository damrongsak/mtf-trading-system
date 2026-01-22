import { useState, useEffect, useRef } from "react";
import { logger } from "@/lib/api/app-logger";
import type { JournalEntry, CreateJournalEntryDto, TimelineEvent } from "@/lib/api/types";
import { getPreferences } from "@/lib/api";
import WizardLayout from "@/components/journal/WizardLayout";
import Step1Technical from "@/components/journal/Step1Technical";
import Step2GameLevel from "@/components/journal/Step2GameLevel";
import Step3MentalPattern from "@/components/journal/Step3MentalPattern";
import Step4RootCause from "@/components/journal/Step4RootCause";

interface JournalWizardProps {
  initialData?: Partial<JournalEntry> & {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mental_state?: any;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    timeline_events?: any[];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
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
            if (prefs.default_symbol) {
                setSupportedSymbols(prev => Array.from(new Set([prefs.default_symbol, "XAU_USD", "EUR_USD", "BTC_USD", ...prev])));
            }
        } catch (error) {
            logger.error('Failed to load supported symbols', error);
        }
    };
    fetchSymbols();
  }, []);

  // Helper functions for state initialization
  // Use any for data to handle the intersection type easily
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getInitialStep1Data = (data?: any) => ({
    symbol: data?.symbol || "XAU/USD",
    direction: (data?.direction || "LONG"), // Allow string to match Step1Technical
    session: data?.session || "",
    entryPrice: data?.entry_price?.toString() || "",
    stopLoss: data?.stop_loss_price?.toString() || "",
    takeProfit: data?.take_profit_price?.toString() || "",
    riskAmount: data?.risk_amount?.toString() || "",
    exitPrice: data?.exit_price?.toString() || "",
    pnl: data?.pnl_amount?.toString() || "",
    contextScore: data?.context_score || 5,
  });

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getInitialGameLevel = (data?: any) => data?.game_level || "";
  
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getInitialTimelineEvents = (data?: any) => data?.timeline_events || [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getInitialMentalState = (data?: any) => data?.mental_state || {
    greed_level: 0,
    fear_level: 0,
    tilt_level: 0,
    confidence_level: 5,
    discipline_level: 5,
  };

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getInitialRootCause = (data?: any) => {
    if (data?.root_cause) {
        return {
          problem: data.root_cause.problem || "",
          why_exist: data.root_cause.why_exist || "",
          flaw: data.root_cause.flaw || "",
          correction: data.root_cause.correction || "",
          logic: data.root_cause.logic || "",
        };
    }
    return {
        problem: "",
        why_exist: "",
        flaw: "",
        correction: "",
        logic: "",
    };
  };

  // Step 1 Data
  const [step1Data, setStep1Data] = useState(() => getInitialStep1Data(initialData));

  // Step 2 Data
  const [gameLevel, setGameLevel] = useState(() => getInitialGameLevel(initialData));

  // Step 3 Data
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>(() => getInitialTimelineEvents(initialData));
  const [mentalState, setMentalState] = useState(() => getInitialMentalState(initialData));

  // Step 4 Data
  const [rootCause, setRootCause] = useState(() => getInitialRootCause(initialData));
  
  // Track previous initialData to detect changes
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const prevInitialDataRef = useRef<any>(initialData);

  // Initialize data if provided (for edit mode)
  useEffect(() => {
    // Only update if initialData has effectively changed from what we used to initialize
    // This simple check prevents the effect from running on mount if data is same
    if (initialData && initialData !== prevInitialDataRef.current) {
       // eslint-disable-next-line
       setStep1Data(getInitialStep1Data(initialData));
       setGameLevel(getInitialGameLevel(initialData));
       setTimelineEvents(getInitialTimelineEvents(initialData));
       setMentalState(getInitialMentalState(initialData));
       setRootCause(getInitialRootCause(initialData));
       // Update ref
       prevInitialDataRef.current = initialData;
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
