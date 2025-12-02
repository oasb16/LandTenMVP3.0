"use client";

import { createContext, useContext, ReactNode } from "react";
import type { IntentType } from "@/types/ai-support";

interface AISupportFlowContextValue {
  sendIntent: (intent: IntentType, payload: Record<string, unknown>) => Promise<void>;
}

const AISupportFlowContext = createContext<AISupportFlowContextValue | undefined>(undefined);

export function AISupportFlowProvider({
  children,
  sendIntent,
}: {
  children: ReactNode;
  sendIntent: (intent: IntentType, payload: Record<string, unknown>) => Promise<void>;
}) {
  return (
    <AISupportFlowContext.Provider value={{ sendIntent }}>
      {children}
    </AISupportFlowContext.Provider>
  );
}

export function useAISupportFlowContext() {
  const context = useContext(AISupportFlowContext);
  if (!context) {
    // Return a no-op if not inside AISupportFlowProvider (e.g., in /dashboard)
    return {
      sendIntent: async () => {
        console.warn("[AISupportFlowContext] sendIntent called outside of provider - no-op");
      },
    };
  }
  return context;
}
