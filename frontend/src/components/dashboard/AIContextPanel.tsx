"use client";

interface FlowState {
  type: string | null;
  stage: string | null;
  incident_id?: string;
  job_id?: string;
  metadata?: Record<string, any>;
}

interface ReasoningState {
  intent: string | null;
  confidence: number | null;
  entities: Record<string, any>;
  last_updated: string | null;
}

interface AIContextPanelProps {
  flowState: FlowState;
  reasoningState: ReasoningState;
}

export function AIContextPanel({ flowState, reasoningState }: AIContextPanelProps) {
  return (
    <div className="h-full flex flex-col overflow-y-auto">
      {/* Header */}
      <div className="p-4 border-b border-slate-800">
        <h2 className="text-lg font-semibold text-white">AI Context & Insights</h2>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        {/* Flow State Section */}
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <h3 className="text-sm font-semibold text-emerald-400 mb-3 flex items-center gap-2">
            <span>🎯</span>
            <span>Current Flow</span>
          </h3>

          {flowState.type ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-400">Type:</span>
                <span className="text-slate-200 font-medium capitalize">{flowState.type}</span>
              </div>
              {flowState.stage && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Stage:</span>
                  <span className="text-slate-200 font-medium capitalize">{flowState.stage}</span>
                </div>
              )}
              {flowState.incident_id && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Incident:</span>
                  <span className="text-slate-200 font-mono text-xs">{flowState.incident_id}</span>
                </div>
              )}
              {flowState.job_id && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Job:</span>
                  <span className="text-slate-200 font-mono text-xs">{flowState.job_id}</span>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">No active flow</p>
          )}
        </div>

        {/* Reasoning State Section */}
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <h3 className="text-sm font-semibold text-blue-400 mb-3 flex items-center gap-2">
            <span>🧠</span>
            <span>AI Reasoning</span>
          </h3>

          {reasoningState.intent ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Intent:</span>
                <span className="text-slate-200 font-medium">{reasoningState.intent}</span>
              </div>
              {reasoningState.confidence !== null && (
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Confidence:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 transition-all duration-300"
                        style={{ width: `${reasoningState.confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-slate-200 font-medium text-xs">
                      {(reasoningState.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}
              {reasoningState.last_updated && (
                <div className="text-xs text-slate-500 mt-2">
                  Updated: {new Date(reasoningState.last_updated).toLocaleTimeString()}
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-slate-400 italic">No reasoning data yet</p>
          )}
        </div>

        {/* Extracted Entities Section */}
        {Object.keys(reasoningState.entities).length > 0 && (
          <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
            <h3 className="text-sm font-semibold text-purple-400 mb-3 flex items-center gap-2">
              <span>🏷️</span>
              <span>Extracted Entities</span>
            </h3>

            <div className="space-y-2 text-sm">
              {Object.entries(reasoningState.entities).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-slate-400 capitalize">{key.replace(/_/g, " ")}:</span>
                  <span className="text-slate-200 font-medium">
                    {typeof value === "object" ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* System Stats */}
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <h3 className="text-sm font-semibold text-yellow-400 mb-3 flex items-center gap-2">
            <span>📊</span>
            <span>System Info</span>
          </h3>

          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Status:</span>
              <span className="text-emerald-400 font-medium">● Active</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">AI Model:</span>
              <span className="text-slate-200 font-mono text-xs">GPT-4o-mini</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Context TTL:</span>
              <span className="text-slate-200">24h</span>
            </div>
          </div>
        </div>

        {/* Help Section */}
        <div className="bg-emerald-900/20 rounded-lg p-4 border border-emerald-900/50">
          <h3 className="text-sm font-semibold text-emerald-400 mb-2">💡 AI Features</h3>
          <ul className="text-xs text-slate-300 space-y-1.5 ml-4 list-disc">
            <li>Intent detection from natural language</li>
            <li>Conversational context (24h retention)</li>
            <li>Persona-based policy enforcement</li>
            <li>Automated incident → job → approval flow</li>
            <li>Real-time reasoning updates</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
