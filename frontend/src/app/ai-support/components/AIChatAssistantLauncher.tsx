/**
 * AIChatAssistantLauncher
 *
 * Floating button and drawer for AI Support Assistant
 */

"use client";

import { useState, useEffect } from "react";
import { MessageSquare, X, Minimize2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface AIChatAssistantLauncherProps {
  children: React.ReactNode;
  autoOpen?: boolean;
  onClose?: () => void;
}

export default function AIChatAssistantLauncher({
  children,
  autoOpen = true,
  onClose,
}: AIChatAssistantLauncherProps) {
  const [isOpen, setIsOpen] = useState(autoOpen);
  const [isMinimized, setIsMinimized] = useState(false);

  // Auto-open on mount if specified
  useEffect(() => {
    if (autoOpen) {
      setIsOpen(true);
    }
  }, [autoOpen]);

  // Handle close
  const handleClose = () => {
    setIsOpen(false);
    onClose?.();
  };

  return (
    <>
      {/* Floating Action Button */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-full shadow-2xl hover:shadow-blue-500/50 transition-shadow z-50 flex items-center justify-center group"
            aria-label="Open AI Support Assistant"
          >
            <MessageSquare className="w-7 h-7 group-hover:scale-110 transition-transform" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-green-500 rounded-full border-2 border-white animate-pulse" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Chat Drawer - ChatGPT-style right-side panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, x: 480 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 480 }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed right-0 bottom-0 top-0 w-full sm:w-[480px] h-full bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-700 shadow-2xl overflow-hidden z-50 flex flex-col"
            style={{ minWidth: '320px', maxWidth: '100vw' }}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-blue-600 to-purple-600 text-white">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center backdrop-blur-sm">
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-semibold text-base">AI Support Assistant</h2>
                  <p className="text-xs opacity-90">We&apos;re here to help</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setIsMinimized(!isMinimized)}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                  aria-label="Minimize"
                >
                  <Minimize2 className="w-4 h-4" />
                </button>
                <button
                  onClick={handleClose}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                  aria-label="Close"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Content */}
            <AnimatePresence mode="wait">
              {!isMinimized && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="flex-1 overflow-hidden"
                >
                  {children}
                </motion.div>
              )}
            </AnimatePresence>

            {/* Minimized State */}
            {isMinimized && (
              <div className="flex-1 flex items-center justify-center p-6 bg-gray-50 dark:bg-gray-800">
                <button
                  onClick={() => setIsMinimized(false)}
                  className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                >
                  Click to expand
                </button>
              </div>
            )}

            {/* Footer Badge */}
            <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 text-center">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Powered by{" "}
                <span className="font-semibold text-blue-600 dark:text-blue-400">
                  LandTen AI
                </span>
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40"
          />
        )}
      </AnimatePresence>
    </>
  );
}
