"use client";

import { useState } from "react";

interface TimelineEvent {
  type: string;
  description: string;
  order_index: number;
}

interface MentalState {
  greed_level: number;
  fear_level: number;
  tilt_level: number;
  confidence_level: number;
  discipline_level: number;
}

interface Step3Props {
  timelineEvents: TimelineEvent[];
  mentalState: MentalState;
  onTimelineChange: (events: TimelineEvent[]) => void;
  onMentalStateChange: (state: MentalState) => void;
  onNext: () => void;
  onBack: () => void;
}

export default function Step3MentalPattern({ 
  timelineEvents, 
  mentalState, 
  onTimelineChange, 
  onMentalStateChange, 
  onNext, 
  onBack 
}: Step3Props) {
  const [newEvent, setNewEvent] = useState({ type: "TRIGGER", description: "" });

  const eventTypes = [
    { value: "TRIGGER", label: "🎯 Trigger", color: "text-yellow-400" },
    { value: "THOUGHT", label: "💭 Thought", color: "text-blue-400" },
    { value: "EMOTION", label: "❤️ Emotion", color: "text-red-400" },
    { value: "BEHAVIOR", label: "⚡ Behavior", color: "text-purple-400" },
  ];

  const addEvent = () => {
    if (newEvent.description.trim()) {
      onTimelineChange([
        ...timelineEvents,
        { ...newEvent, order_index: timelineEvents.length }
      ]);
      setNewEvent({ type: "TRIGGER", description: "" });
    }
  };

  const removeEvent = (index: number) => {
    onTimelineChange(timelineEvents.filter((_, i) => i !== index));
  };

  const updateMentalLevel = (key: keyof MentalState, value: number) => {
    onMentalStateChange({ ...mentalState, [key]: value });
  };

  const getSliderColor = (value: number) => {
    if (value <= 3) return "from-green-500 to-green-600";
    if (value <= 6) return "from-yellow-500 to-yellow-600";
    if (value <= 8) return "from-orange-500 to-orange-600";
    return "from-red-500 to-red-600";
  };

  return (
    <div className="space-y-6">
      {/* Timeline Builder */}
      <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-xl font-bold text-emerald-400 mb-4">Mental Timeline (The MRI)</h2>
        <p className="text-gray-400 text-sm mb-4">Build the sequence of events that led to the mistake</p>

        {/* Event List */}
        <div className="space-y-3 mb-4">
          {timelineEvents.map((event, idx) => {
            const eventType = eventTypes.find(t => t.value === event.type);
            return (
              <div key={idx} className="flex items-start gap-3 p-3 bg-gray-800 rounded-lg">
                <span className={`text-sm font-medium ${eventType?.color}`}>{eventType?.label}</span>
                <p className="flex-1 text-white text-sm">{event.description}</p>
                <button
                  onClick={() => removeEvent(idx)}
                  className="text-red-400 hover:text-red-300 text-sm"
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>

        {/* Add Event */}
        <div className="flex gap-2">
          <select
            value={newEvent.type}
            onChange={(e) => setNewEvent({ ...newEvent, type: e.target.value })}
            className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          >
            {eventTypes.map(type => (
              <option key={type.value} value={type.value}>{type.label}</option>
            ))}
          </select>
          <input
            type="text"
            value={newEvent.description}
            onChange={(e) => setNewEvent({ ...newEvent, description: e.target.value })}
            onKeyPress={(e) => e.key === 'Enter' && addEvent()}
            placeholder="Describe what happened..."
            className="flex-1 px-4 py-2 bg-gray-800 border border-gray-700 rounded text-sm focus:ring-2 focus:ring-emerald-500 focus:outline-none"
          />
          <button
            onClick={addEvent}
            className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-medium rounded text-sm"
          >
            Add
          </button>
        </div>
      </div>

      {/* Severity Sliders */}
      <div className="bg-gray-900 p-6 rounded-xl border border-gray-800">
        <h2 className="text-xl font-bold text-emerald-400 mb-4">Emotional Severity (1-10)</h2>
        
        <div className="space-y-4">
          {[
            { key: "greed_level" as keyof MentalState, label: "Greed", desc: "Urgency to prove, unreasonable expectations" },
            { key: "fear_level" as keyof MentalState, label: "Fear", desc: "Fear of losing, FOMO" },
            { key: "tilt_level" as keyof MentalState, label: "Tilt (Anger)", desc: "Injustice, hating to lose, mistake tilt" },
            { key: "confidence_level" as keyof MentalState, label: "Confidence", desc: "1=Give up, 5=Ideal, 10=Invincible" },
            { key: "discipline_level" as keyof MentalState, label: "Discipline", desc: "1=Worst, 10=Optimal" }
          ].map(({ key, label, desc }) => (
            <div key={key}>
              <div className="flex justify-between mb-2">
                <div>
                  <span className="text-white font-medium">{label}</span>
                  <span className="text-gray-400 text-xs ml-2">{desc}</span>
                </div>
                <span className={`text-lg font-bold bg-gradient-to-r ${getSliderColor(mentalState[key])} bg-clip-text text-transparent`}>
                  {mentalState[key]}
                </span>
              </div>
              <input
                type="range"
                min="0"
                max="10"
                value={mentalState[key]}
                onChange={(e) => updateMentalLevel(key, parseInt(e.target.value))}
                className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-emerald-500"
                style={{
                  background: `linear-gradient(to right, 
                    rgb(34 197 94) 0%, 
                    rgb(234 179 8) 33%, 
                    rgb(249 115 22) 66%, 
                    rgb(239 68 68) 100%)`
                }}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-4">
        <button
          onClick={onBack}
          className="flex-1 py-3 bg-gray-800 hover:bg-gray-700 text-white font-bold rounded-lg transition-colors"
        >
          ← Back
        </button>
        <button
          onClick={onNext}
          className="flex-1 py-3 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-bold rounded-lg transition-colors"
        >
          Next: Root Cause →
        </button>
      </div>
    </div>
  );
}
