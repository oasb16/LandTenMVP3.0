"use client";

import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Calendar,
  Clock,
  CheckCircle2,
  User,
  MapPin,
  AlertCircle,
  ThumbsUp,
  MessageSquare,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface ProposedTimeSlot {
  id: string;
  date: string;
  startTime: string;
  endTime: string;
  notes?: string;
}

interface ScheduleApprovalPanelProps {
  jobId: string;
  jobTitle: string;
  propertyAddress?: string;
  contractorName: string;
  contractorAvatar?: string;
  proposedSlots: ProposedTimeSlot[];
  onSubmit: (intent: string, payload: any) => Promise<void>;
  onRequestChange?: () => void;
}

export default function ScheduleApprovalPanel({
  jobId,
  jobTitle,
  propertyAddress,
  contractorName,
  contractorAvatar,
  proposedSlots,
  onSubmit,
  onRequestChange,
}: ScheduleApprovalPanelProps) {
  const [selectedSlotId, setSelectedSlotId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    const options: Intl.DateTimeFormatOptions = {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    };
    return date.toLocaleDateString("en-US", options);
  };

  const formatTime = (timeString: string): string => {
    const [hours, minutes] = timeString.split(":");
    const hour = parseInt(hours, 10);
    const period = hour >= 12 ? "PM" : "AM";
    const displayHour = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${displayHour}:${minutes} ${period}`;
  };

  const getDayOfWeek = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", { weekday: "short" });
  };

  const getRelativeDate = (dateString: string): string => {
    const date = new Date(dateString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    today.setHours(0, 0, 0, 0);
    tomorrow.setHours(0, 0, 0, 0);
    date.setHours(0, 0, 0, 0);

    if (date.getTime() === today.getTime()) {
      return "Today";
    } else if (date.getTime() === tomorrow.getTime()) {
      return "Tomorrow";
    }

    const daysUntil = Math.ceil(
      (date.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
    );
    if (daysUntil <= 7) {
      return `In ${daysUntil} days`;
    }
    return "";
  };

  const handleApprove = async () => {
    if (!selectedSlotId) {
      setError("Please select a time slot");
      return;
    }

    const selectedSlot = proposedSlots.find(
      (slot) => slot.id === selectedSlotId
    );
    if (!selectedSlot) {
      setError("Invalid time slot selected");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      await onSubmit("approve_schedule", {
        job_id: jobId,
        selected_slot: {
          date: selectedSlot.date,
          start_time: selectedSlot.startTime,
          end_time: selectedSlot.endTime,
        },
      });
    } catch (err) {
      console.error("Error approving schedule:", err);
      setError("Failed to approve schedule. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const sortedSlots = [...proposedSlots].sort((a, b) => {
    const dateCompare = a.date.localeCompare(b.date);
    if (dateCompare !== 0) return dateCompare;
    return a.startTime.localeCompare(b.startTime);
  });

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
        <div className="flex items-start gap-3 mb-4">
          <div className="p-2 bg-emerald-500/10 rounded-lg">
            <Calendar className="w-6 h-6 text-emerald-400" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-semibold">Approve Visit Schedule</h2>
            <p className="text-sm text-slate-400 mt-1">
              Select the time slot that works best for you
            </p>
          </div>
        </div>

        {/* Job & Contractor Info */}
        <Card className="p-4 bg-slate-900 border-slate-800 space-y-3">
          <div className="flex items-start gap-3">
            <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200">{jobTitle}</p>
              {propertyAddress && (
                <p className="text-xs text-slate-500 mt-0.5">
                  {propertyAddress}
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2 border-t border-slate-800">
            <div className="flex items-center gap-2">
              {contractorAvatar ? (
                <img
                  src={contractorAvatar}
                  alt={contractorName}
                  className="w-8 h-8 rounded-full"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                  <User className="w-4 h-4 text-blue-400" />
                </div>
              )}
              <div>
                <p className="text-xs text-slate-400">Contractor</p>
                <p className="text-sm font-medium text-slate-200">
                  {contractorName}
                </p>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Time Slots */}
      <div className="flex-1 overflow-y-auto p-6 space-y-3">
        <p className="text-sm font-medium text-slate-300 mb-3">
          Proposed Time Slots ({proposedSlots.length}{" "}
          {proposedSlots.length === 1 ? "option" : "options"})
        </p>

        {sortedSlots.map((slot) => {
          const isSelected = selectedSlotId === slot.id;
          const relativeDate = getRelativeDate(slot.date);

          return (
            <motion.div
              key={slot.id}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
            >
              <Card
                onClick={() => setSelectedSlotId(slot.id)}
                className={`p-4 cursor-pointer transition-all duration-200 ${
                  isSelected
                    ? "bg-emerald-500/10 border-emerald-500 ring-2 ring-emerald-500/30"
                    : "bg-slate-900 border-slate-800 hover:border-slate-700 hover:bg-slate-800/50"
                }`}
              >
                <div className="flex items-start gap-4">
                  {/* Date Display */}
                  <div className="flex flex-col items-center justify-center p-3 bg-slate-800 rounded-lg min-w-[70px]">
                    <span className="text-xs font-medium text-slate-400 uppercase">
                      {getDayOfWeek(slot.date)}
                    </span>
                    <span className="text-2xl font-bold text-slate-100 mt-1">
                      {new Date(slot.date).getDate()}
                    </span>
                    <span className="text-xs text-slate-500 mt-1">
                      {new Date(slot.date).toLocaleDateString("en-US", {
                        month: "short",
                      })}
                    </span>
                  </div>

                  {/* Time & Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <p className="font-medium text-slate-200">
                        {formatTime(slot.startTime)} -{" "}
                        {formatTime(slot.endTime)}
                      </p>
                    </div>

                    {relativeDate && (
                      <div className="inline-block px-2 py-1 bg-blue-500/10 rounded text-xs font-medium text-blue-400 mb-2">
                        {relativeDate}
                      </div>
                    )}

                    <p className="text-xs text-slate-400">
                      {formatDate(slot.date)}
                    </p>

                    {slot.notes && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <div className="flex items-start gap-2">
                          <MessageSquare className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
                          <p className="text-xs text-slate-400 italic">
                            {slot.notes}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Selection Indicator */}
                  <div className="flex-shrink-0">
                    <div
                      className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
                        isSelected
                          ? "border-emerald-500 bg-emerald-500"
                          : "border-slate-600"
                      }`}
                    >
                      {isSelected && (
                        <CheckCircle2 className="w-4 h-4 text-white" />
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          );
        })}

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {/* Info Banner */}
        <div className="mt-6 p-4 bg-blue-500/5 border border-blue-500/10 rounded-lg">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-slate-300">
              <p className="font-medium mb-1">Confirmation Required</p>
              <p className="text-slate-400">
                Once you approve a time slot, the contractor will be notified
                and the visit will be scheduled. You can reschedule later if
                needed.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Footer Actions */}
      <div className="p-6 border-t border-slate-800 bg-slate-900/50">
        <div className="flex gap-3">
          {onRequestChange && (
            <Button
              type="button"
              variant="outline"
              onClick={onRequestChange}
              disabled={isSubmitting}
              className="border-slate-700 text-slate-300 hover:bg-slate-800"
            >
              Request Different Times
            </Button>
          )}
          <Button
            type="button"
            onClick={handleApprove}
            disabled={!selectedSlotId || isSubmitting}
            className="flex-1 bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                Approving...
              </>
            ) : (
              <>
                <ThumbsUp className="w-4 h-4 mr-2" />
                Approve Selected Time
              </>
            )}
          </Button>
        </div>
      </div>
    </motion.div>
  );
}
