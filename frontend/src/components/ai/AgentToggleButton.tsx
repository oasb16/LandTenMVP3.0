"use client";

import { useState, useEffect } from "react";

type AgentToggleProps = {
  initialState?: boolean;
  onChange?: (enabled: boolean) => void;
};

export function AgentToggleButton({ initialState = true, onChange }: AgentToggleProps) {
  const [agentEnabled, setAgentEnabled] = useState(initialState);

  useEffect(() => {
    // Load from localStorage
    const saved = localStorage.getItem("landten_agent_enabled");
    if (saved !== null) {
      const enabled = saved === "true";
      setAgentEnabled(enabled);
      onChange?.(enabled);
    }
  }, [onChange]);

  const toggleAgent = () => {
    const newState = !agentEnabled;
    setAgentEnabled(newState);
    localStorage.setItem("landten_agent_enabled", String(newState));
    onChange?.(newState);
  };

  return (
    <button
      onClick={toggleAgent}
      className={`
        w-full flex items-center justify-between gap-2 rounded px-3 py-2 text-sm font-semibold
        transition-all duration-200
        ${agentEnabled
          ? 'bg-emerald-600 text-white hover:bg-emerald-700'
          : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
        }
      `}
      title={agentEnabled ? "AI Agent is ON - Messages will be analyzed for incidents" : "AI Agent is OFF - Direct messaging only"}
    >
      <span className="flex items-center gap-2">
        <span className="text-lg">{agentEnabled ? '🤖' : '💬'}</span>
        <span>Agent: {agentEnabled ? 'ON' : 'OFF'}</span>
      </span>
      <div className={`
        w-10 h-5 rounded-full relative transition-colors duration-200
        ${agentEnabled ? 'bg-emerald-800' : 'bg-slate-600'}
      `}>
        <div className={`
          absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200
          ${agentEnabled ? 'translate-x-5' : 'translate-x-0.5'}
        `} />
      </div>
    </button>
  );
}
