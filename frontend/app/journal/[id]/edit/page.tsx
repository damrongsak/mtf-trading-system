"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { getJournalEntry, updateJournalEntry } from "@/lib/api/journal";
import { CreateJournalEntryDto, JournalEntry } from "@/lib/api/types";
import JournalWizard from "@/components/journal/JournalWizard";
import { useAsync } from "@/lib/hooks";
import { Modal } from "@/components/common";

export default function EditJournalPage() {
  const router = useRouter();
  const params = useParams();
  const id = params?.id as string;

  const { execute: fetchEntry, loading: loadingEntry, error: fetchError } = useAsync(getJournalEntry);
  const { execute: updateEntry, loading: updating } = useAsync((data: Partial<CreateJournalEntryDto>) => updateJournalEntry(id, data));
  
  const [initialData, setInitialData] = useState<Partial<JournalEntry> | undefined>(undefined);
  const [showSuccessModal, setShowSuccessModal] = useState(false);

  useEffect(() => {
    if (id) {
      fetchEntry(id).then((data) => {
        if (data) {
           setInitialData(data);
        }
      });
    }
  }, [id, fetchEntry]);

  const handleSubmit = async (data: CreateJournalEntryDto) => {
    const result = await updateEntry(data);
    if (result) {
      setShowSuccessModal(true);
    }
  };

  const handleCloseModal = () => {
    setShowSuccessModal(false);
    router.push("/journal");
  };

  if (loadingEntry) {
      return <div className="flex justify-center items-center min-h-screen text-emerald-500">Loading entry...</div>;
  }

  if (fetchError) {
      return <div className="flex justify-center items-center min-h-screen text-red-500">Error: {fetchError}</div>;
  }

  return (
    <div className="min-h-screen bg-gray-950">
        {initialData && (
            <JournalWizard 
                initialData={initialData} 
                onSubmit={handleSubmit} 
                isSubmitting={updating} 
            />
        )}
        
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
                <p className="text-lg">Journal entry updated successfully!</p>
            </div>
        </Modal>
    </div>
  );
}
