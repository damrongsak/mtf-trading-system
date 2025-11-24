"use client";

import { ReactNode } from "react";

interface WizardLayoutProps {
  currentStep: number;
  totalSteps: number;
  children: ReactNode;
}

export default function WizardLayout({ currentStep, totalSteps, children }: WizardLayoutProps) {
  const steps = [
    { number: 1, title: "Technical Context" },
    { number: 2, title: "Game Level" },
    { number: 3, title: "Mental Pattern" },
    { number: 4, title: "Root Cause" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Progress Header */}
      <div className="sticky top-0 z-10 bg-gray-900/80 backdrop-blur border-b border-gray-800">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-emerald-400">Trading Journal</h1>
            <span className="text-sm text-gray-400">Step {currentStep} of {totalSteps}</span>
          </div>
          
          {/* Step Indicator */}
          <div className="flex items-center gap-2">
            {steps.map((step, idx) => (
              <div key={step.number} className="flex items-center flex-1">
                <div className="flex flex-col items-center w-full">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                    currentStep === step.number 
                      ? "bg-emerald-500 text-gray-900" 
                      : currentStep > step.number 
                      ? "bg-emerald-700 text-white" 
                      : "bg-gray-700 text-gray-400"
                  }`}>
                    {step.number}
                  </div>
                  <span className={`text-xs mt-1 ${currentStep === step.number ? "text-emerald-400" : "text-gray-500"}`}>
                    {step.title}
                  </span>
                </div>
                {idx < steps.length - 1 && (
                  <div className={`h-1 flex-1 mx-2 rounded ${currentStep > step.number ? "bg-emerald-700" : "bg-gray-700"}`} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        {children}
      </div>
    </div>
  );
}
