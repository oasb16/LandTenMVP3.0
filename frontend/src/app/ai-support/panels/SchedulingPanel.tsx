"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import { Calendar, Clock, Plus, X, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface TimeSlot {
  id: string;
  date: string;
  startTime: string;
  endTime: string;
  notes?: string;
}

interface SchedulingPanelProps {
  jobId: string;
  jobTitle: string;
  propertyAddress?: string;
  onSubmit: (intent: string, payload: any) => Promise<void>;
  onCancel?: () => void;
}

export default function SchedulingPanel({
  jobId,
  jobTitle,
  propertyAddress,
  onSubmit,
  onCancel,
}: SchedulingPanelProps) {
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([
    { id: "1", date: "", startTime: "", endTime: "", notes: "" },
  ]);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const addTimeSlot = () => {
    const newSlot: TimeSlot = {
      id: Date.now().toString(),
      date: "",
      startTime: "",
      endTime: "",
      notes: "",
    };
    setTimeSlots([...timeSlots, newSlot]);
  };

  const removeTimeSlot = (id: string) => {
    if (timeSlots.length > 1) {
      setTimeSlots(timeSlots.filter((slot) => slot.id !== id));
      // Clear errors for removed slot
      const newErrors = { ...errors };
      delete newErrors[`${id}-date`];
      delete newErrors[`${id}-startTime`];
      delete newErrors[`${id}-endTime`];
      setErrors(newErrors);
    }
  };

  const updateTimeSlot = (id: string, field: keyof TimeSlot, value: string) => {
    setTimeSlots(
      timeSlots.map((slot) =>
        slot.id === id ? { ...slot, [field]: value } : slot
      )
    );
    // Clear error for this field when user starts typing
    if (errors[`${id}-${field}`]) {
      const newErrors = { ...errors };
      delete newErrors[`${id}-${field}`];
      setErrors(newErrors);
    }
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    timeSlots.forEach((slot, index) => {
      // Validate date
      if (!slot.date) {
        newErrors[`${slot.id}-date`] = "Date is required";
      } else {
        const selectedDate = new Date(slot.date);
        if (selectedDate < today) {
          newErrors[`${slot.id}-date`] = "Date cannot be in the past";
        }
      }

      // Validate start time
      if (!slot.startTime) {
        newErrors[`${slot.id}-startTime`] = "Start time is required";
      }

      // Validate end time
      if (!slot.endTime) {
        newErrors[`${slot.id}-endTime`] = "End time is required";
      } else if (slot.startTime && slot.endTime <= slot.startTime) {
        newErrors[`${slot.id}-endTime`] = "End time must be after start time";
      }

      // Check for duplicate time slots
      timeSlots.forEach((otherSlot, otherIndex) => {
        if (
          index !== otherIndex &&
          slot.date === otherSlot.date &&
          slot.startTime === otherSlot.startTime
        ) {
          newErrors[`${slot.id}-duplicate`] =
            "This time slot is duplicated";
        }
      });
    });

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit("propose_schedule", {
        job_id: jobId,
        proposed_slots: timeSlots.map((slot) => ({
          date: slot.date,
          start_time: slot.startTime,
          end_time: slot.endTime,
          notes: slot.notes,
        })),
      });
    } catch (error) {
      console.error("Error submitting schedule:", error);
      setErrors({ submit: "Failed to submit schedule. Please try again." });
    } finally {
      setIsSubmitting(false);
    }
  };

  const getMinDate = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split("T")[0];
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col h-full bg-slate-950 text-slate-100"
    >
      {/* Header */}
      <div className="p-6 border-b border-slate-800">
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Calendar className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <h2 className="text-xl font-semibold">Propose Visit Schedule</h2>
              <p className="text-sm text-slate-400 mt-1">
                Select multiple time slots that work for you
              </p>
            </div>
          </div>
        </div>

        {/* Job Info */}
        <Card className="mt-4 p-4 bg-slate-900 border-slate-800">
          <div className="space-y-1">
            <p className="text-sm font-medium text-slate-300">{jobTitle}</p>
            {propertyAddress && (
              <p className="text-xs text-slate-500">{propertyAddress}</p>
            )}
          </div>
        </Card>
      </div>

      {/* Time Slots Form */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {/* Info Banner */}
        <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-slate-300">
            <p className="font-medium mb-1">Propose 2-3 options</p>
            <p className="text-slate-400">
              The property owner will select the time slot that works best for them
            </p>
          </div>
        </div>

        {/* Time Slot Cards */}
        {timeSlots.map((slot, index) => (
          <Card
            key={slot.id}
            className="p-5 bg-slate-900 border-slate-800 space-y-4"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-400" />
                <h3 className="font-medium text-slate-200">
                  Option {index + 1}
                </h3>
              </div>
              {timeSlots.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeTimeSlot(slot.id)}
                  className="text-slate-400 hover:text-red-400 hover:bg-red-500/10"
                >
                  <X className="w-4 h-4" />
                </Button>
              )}
            </div>

            {/* Date Input */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Date
              </label>
              <input
                type="date"
                value={slot.date}
                onChange={(e) => updateTimeSlot(slot.id, "date", e.target.value)}
                min={getMinDate()}
                className={`w-full px-4 py-2.5 bg-slate-800 border rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                  errors[`${slot.id}-date`]
                    ? "border-red-500"
                    : "border-slate-700"
                }`}
              />
              {errors[`${slot.id}-date`] && (
                <p className="mt-1.5 text-sm text-red-400">
                  {errors[`${slot.id}-date`]}
                </p>
              )}
            </div>

            {/* Time Range */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Start Time
                </label>
                <input
                  type="time"
                  value={slot.startTime}
                  onChange={(e) =>
                    updateTimeSlot(slot.id, "startTime", e.target.value)
                  }
                  className={`w-full px-4 py-2.5 bg-slate-800 border rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors[`${slot.id}-startTime`]
                      ? "border-red-500"
                      : "border-slate-700"
                  }`}
                />
                {errors[`${slot.id}-startTime`] && (
                  <p className="mt-1.5 text-sm text-red-400">
                    {errors[`${slot.id}-startTime`]}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  End Time
                </label>
                <input
                  type="time"
                  value={slot.endTime}
                  onChange={(e) =>
                    updateTimeSlot(slot.id, "endTime", e.target.value)
                  }
                  className={`w-full px-4 py-2.5 bg-slate-800 border rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    errors[`${slot.id}-endTime`]
                      ? "border-red-500"
                      : "border-slate-700"
                  }`}
                />
                {errors[`${slot.id}-endTime`] && (
                  <p className="mt-1.5 text-sm text-red-400">
                    {errors[`${slot.id}-endTime`]}
                  </p>
                )}
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Notes (Optional)
              </label>
              <textarea
                value={slot.notes}
                onChange={(e) => updateTimeSlot(slot.id, "notes", e.target.value)}
                placeholder="e.g., Prefer morning slots, need 2 hours for completion"
                rows={2}
                className="w-full px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            {/* Duplicate Error */}
            {errors[`${slot.id}-duplicate`] && (
              <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <p className="text-sm text-red-400">
                  {errors[`${slot.id}-duplicate`]}
                </p>
              </div>
            )}
          </Card>
        ))}

        {/* Add Slot Button */}
        {timeSlots.length < 5 && (
          <Button
            type="button"
            variant="outline"
            onClick={addTimeSlot}
            className="w-full border-slate-700 text-slate-300 hover:bg-slate-800 hover:text-slate-100"
          >
            <Plus className="w-4 h-4 mr-2" />
            Add Another Time Slot
          </Button>
        )}

        {/* Submit Error */}
        {errors.submit && (
          <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-400" />
            <p className="text-sm text-red-400">{errors.submit}</p>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-6 border-t border-slate-800 bg-slate-900/50">
        <div className="flex gap-3">
          {onCancel && (
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
              className="flex-1 border-slate-700 text-slate-300 hover:bg-slate-800"
            >
              Cancel
            </Button>
          )}
          <Button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || timeSlots.length === 0}
            className="flex-1 bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                Submitting...
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4 mr-2" />
                Propose Schedule ({timeSlots.length}{" "}
                {timeSlots.length === 1 ? "option" : "options"})
              </>
            )}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
