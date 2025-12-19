"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createJournalEntry } from "@/lib/api/journal";
import { CreateJournalEntryDto } from "@/lib/api/types";
import JournalWizard from "@/components/journal/JournalWizard";
import { useAsync } from "@/lib/hooks";
import { Modal } from "@/components/common";

export default function NewJournalPage() {
  const router = useRouter();
  const { execute: createEntry, loading } = useAsync(createJournalEntry);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  const handleSubmit = async (data: CreateJournalEntryDto) => {
    const result = await createEntry(data);
    if (result) {
      setShowSuccessModal(true);
    }
  };

  const handleCloseModal = () => {
      setShowSuccessModal(false);
      router.push("/journal");
  };

  return (
    <div className="min-h-screen bg-gray-950">
        <JournalWizard onSubmit={handleSubmit} isSubmitting={loading} />
        
        <Modal
            isOpen={showSuccessModal}
            onClose={handleCloseModal}
            title="Success"
            footer={
                <button 
                    onClick={handleCloseModal}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
                >
                    Return to Journal
                </button>
            }
        >
            <div className="flex flex-col items-center text-center">
                <div className="w-16 h-16 bg-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center mb-4">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                </div>
                <p className="text-lg">Journal entry created successfully!</p>
            </div>
        </Modal>
    </div>
  );
}
