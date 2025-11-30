import React, { useState, useEffect, useRef } from 'react';
import { ChevronLeft, X, MessageSquare, User, Package, AlertCircle, CheckCircle, Send, Loader2 } from 'lucide-react';

// ============================================================================
// TYPE DEFINITIONS (mirrors frontend/src/types/)
// ============================================================================

// AI Support Flow Types (from actual codebase)
type UIMode = 'cta_panel' | 'gallery' | 'selector' | 'summary' | 'chat' | 'resolution' | 'fallback';
type Stage = 'intro' | 'item_select' | 'issue_select' | 'summary' | 'diagnosis' | 'resolution';
type Persona = 'tenant' | 'landlord' | 'contractor' | 'property_manager';

interface SessionState {
  sessionId: string;
  channelId: string;
  persona: Persona;
  stage: Stage;
  uiMode: UIMode;
  selectedCTA?: string;
  selectedItem?: any;
  selectedReason?: string;
  flowState: {
    isComplete: boolean;
    canProceed: boolean;
    requiresInput: boolean;
  };
  context: Record<string, any>;
}

interface AIIntent {
  type: 'cta_selected' | 'item_selected' | 'reason_selected' | 'confirm_summary' | 'edit_summary' | 'send_message' | 'escalate_to_human' | 'select_resolution';
  payload: Record<string, any>;
  timestamp: string;
}

interface AIState {
  type: 'ai_state';
  stage: Stage;
  uiMode: UIMode;
  context: Record<string, any>;
  options?: any[];
}

interface Message {
  id: string;
  type: 'user' | 'ai' | 'system' | 'action_card';
  text?: string;
  card?: any;
  timestamp: string;
  user?: {
    id: string;
    name: string;
    role?: 'ai' | 'agent';
  };
}

// Incident Types (from backend models)
interface Incident {
  incident_id: string;
  property_id: string;
  unit_id?: string;
  category: string;
  subcategory?: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'detected' | 'discovery' | 'discovery_complete' | 'diagnosing' | 'work_order' | 'approved' | 'in_progress' | 'completed';
  description: string;
  created_at: string;
  updated_at: string;
}

// ============================================================================
// MOCK DATA (mirrors actual DynamoDB structure)
// ============================================================================

const MOCK_ITEMS = [
  {
    item_id: 'appliance_1',
    item_type: 'appliance',
    name: 'HVAC System',
    category: 'heating_cooling',
    location: 'Main Unit',
    status: 'operational',
    last_maintenance: '2024-10-15',
    icon: '❄️'
  },
  {
    item_id: 'appliance_2',
    item_type: 'appliance',
    name: 'Water Heater',
    category: 'plumbing',
    location: 'Utility Room',
    status: 'operational',
    last_maintenance: '2024-09-20',
    icon: '🔥'
  },
  {
    item_id: 'area_1',
    item_type: 'area',
    name: 'Kitchen',
    category: 'room',
    location: 'Main Floor',
    status: 'good',
    icon: '🍳'
  },
  {
    item_id: 'area_2',
    item_type: 'area',
    name: 'Bathroom',
    category: 'room',
    location: 'Main Floor',
    status: 'good',
    icon: '🚿'
  },
  {
    item_id: 'appliance_3',
    item_type: 'appliance',
    name: 'Refrigerator',
    category: 'appliance',
    location: 'Kitchen',
    status: 'operational',
    last_maintenance: '2024-11-01',
    icon: '🧊'
  }
];

const MOCK_CTAS = [
  { id: 'report_issue', label: 'Report Maintenance Issue', icon: '🔧', category: 'maintenance' },
  { id: 'emergency', label: 'Emergency Request', icon: '🚨', category: 'emergency' },
  { id: 'general_inquiry', label: 'General Question', icon: '💬', category: 'inquiry' },
  { id: 'track_request', label: 'Track My Request', icon: '📍', category: 'tracking' },
  { id: 'diy_help', label: 'DIY Troubleshooting', icon: '🛠️', category: 'diy' }
];

const MOCK_REASONS = {
  appliance: [
    { id: 'not_working', label: 'Not working at all', severity: 'high' },
    { id: 'strange_noise', label: 'Making strange noises', severity: 'medium' },
    { id: 'leaking', label: 'Leaking water/fluid', severity: 'high' },
    { id: 'reduced_performance', label: 'Not working as well as before', severity: 'medium' },
    { id: 'other', label: 'Other issue', severity: 'low' }
  ],
  area: [
    { id: 'water_damage', label: 'Water damage or leak', severity: 'high' },
    { id: 'pest_issue', label: 'Pest/rodent problem', severity: 'medium' },
    { id: 'electrical', label: 'Electrical issue', severity: 'high' },
    { id: 'cosmetic', label: 'Cosmetic damage', severity: 'low' },
    { id: 'other', label: 'Other issue', severity: 'low' }
  ]
};

// ============================================================================
// UTILITY FUNCTIONS (mirrors backend/app/services/)
// ============================================================================

const inferSeverity = (itemType: string, reasonId: string): 'low' | 'medium' | 'high' | 'critical' => {
  const reasons = MOCK_REASONS[itemType as keyof typeof MOCK_REASONS] || [];
  const reason = reasons.find(r => r.id === reasonId);
  
  if (!reason) return 'medium';
  
  // Check for emergency indicators
  if (reasonId.includes('emergency') || reasonId === 'not_working') {
    return 'critical';
  }
  
  return reason.severity as 'low' | 'medium' | 'high' | 'critical';
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical': return 'bg-red-100 text-red-800 border-red-300';
    case 'high': return 'bg-orange-100 text-orange-800 border-orange-300';
    case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 'low': return 'bg-green-100 text-green-800 border-green-300';
    default: return 'bg-gray-100 text-gray-800 border-gray-300';
  }
};

const generateContextualGreeting = (item: any, reason: any, cta: string) => {
  const itemName = item?.name || 'the selected item';
  const reasonLabel = reason?.label || 'the issue';
  
  return `I understand you're experiencing ${reasonLabel.toLowerCase()} with your ${itemName}. I'm here to help diagnose and resolve this issue. Can you tell me more about what's happening?`;
};

// ============================================================================
// ORCHESTRATOR SIMULATION (mirrors ai_support_orchestrator.py)
// ============================================================================

class AIFlowOrchestrator {
  private sessionState: SessionState;
  
  constructor(sessionId: string, persona: Persona) {
    this.sessionState = {
      sessionId,
      channelId: `channel_${sessionId}`,
      persona,
      stage: 'intro',
      uiMode: 'cta_panel',
      flowState: {
        isComplete: false,
        canProceed: false,
        requiresInput: true
      },
      context: {}
    };
  }
  
  handleIntent(intent: AIIntent): AIState {
    switch (intent.type) {
      case 'cta_selected':
        return this.handleCTASelection(intent.payload);
      case 'item_selected':
        return this.handleItemSelection(intent.payload);
      case 'reason_selected':
        return this.handleReasonSelection(intent.payload);
      case 'confirm_summary':
        return this.handleConfirmSummary(intent.payload);
      case 'edit_summary':
        return this.handleEditSummary(intent.payload);
      default:
        return this.getCurrentState();
    }
  }
  
  private handleCTASelection(payload: any): AIState {
    this.sessionState.selectedCTA = payload.cta_id;
    this.sessionState.stage = 'item_select';
    this.sessionState.uiMode = 'gallery';
    this.sessionState.context.cta = payload;
    
    return {
      type: 'ai_state',
      stage: 'item_select',
      uiMode: 'gallery',
      context: {
        instructions: 'Please select the item or area you need help with',
        items: MOCK_ITEMS
      }
    };
  }
  
  private handleItemSelection(payload: any): AIState {
    this.sessionState.selectedItem = payload.item;
    this.sessionState.stage = 'issue_select';
    this.sessionState.uiMode = 'selector';
    this.sessionState.context.item = payload.item;
    
    const itemType = payload.item.item_type;
    const reasons = MOCK_REASONS[itemType as keyof typeof MOCK_REASONS] || [];
    
    return {
      type: 'ai_state',
      stage: 'issue_select',
      uiMode: 'selector',
      context: {
        instructions: `What's the issue with your ${payload.item.name}?`,
        reasons
      }
    };
  }
  
  private handleReasonSelection(payload: any): AIState {
    this.sessionState.selectedReason = payload.reason_id;
    this.sessionState.stage = 'summary';
    this.sessionState.uiMode = 'summary';
    this.sessionState.context.reason = payload;
    
    const severity = inferSeverity(
      this.sessionState.selectedItem?.item_type,
      payload.reason_id
    );
    
    return {
      type: 'ai_state',
      stage: 'summary',
      uiMode: 'summary',
      context: {
        cta: this.sessionState.context.cta,
        item: this.sessionState.selectedItem,
        reason: payload,
        severity,
        canEdit: true
      }
    };
  }
  
  private handleConfirmSummary(payload: any): AIState {
    this.sessionState.stage = 'diagnosis';
    this.sessionState.uiMode = 'chat';
    
    const greeting = generateContextualGreeting(
      this.sessionState.selectedItem,
      this.sessionState.context.reason,
      this.sessionState.selectedCTA || ''
    );
    
    return {
      type: 'ai_state',
      stage: 'diagnosis',
      uiMode: 'chat',
      context: {
        initialMessage: greeting,
        incidentCreated: true
      }
    };
  }
  
  private handleEditSummary(payload: any): AIState {
    const field = payload.field;
    
    if (field === 'cta') {
      this.sessionState.stage = 'intro';
      this.sessionState.uiMode = 'cta_panel';
    } else if (field === 'item') {
      this.sessionState.stage = 'item_select';
      this.sessionState.uiMode = 'gallery';
    } else if (field === 'reason') {
      this.sessionState.stage = 'issue_select';
      this.sessionState.uiMode = 'selector';
    }
    
    return this.getCurrentState();
  }
  
  getCurrentState(): AIState {
    return {
      type: 'ai_state',
      stage: this.sessionState.stage,
      uiMode: this.sessionState.uiMode,
      context: this.sessionState.context
    };
  }
  
  getSessionState(): SessionState {
    return this.sessionState;
  }
}

// ============================================================================
// MAIN COMPONENT (mirrors AIChatContainer.tsx + AIDynamicPanel.tsx)
// ============================================================================

const LandTenAISupportDemo: React.FC = () => {
  // Session state
  const [sessionId] = useState(`session_${Date.now()}`);
  const [persona] = useState<Persona>('tenant');
  const [orchestrator] = useState(() => new AIFlowOrchestrator(sessionId, persona));
  
  // UI state
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [stage, setStage] = useState<Stage>('intro');
  const [uiMode, setUIMode] = useState<UIMode>('cta_panel');
  const [context, setContext] = useState<Record<string, any>>({});
  
  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [userInput, setUserInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isEscalated, setIsEscalated] = useState(false);
  const [agentName, setAgentName] = useState('');
  
  // Refs
  const chatContainerRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);
  
  // ============================================================================
  // INTENT HANDLERS (mirrors useAISupportFlow.ts sendIntent())
  // ============================================================================
  
  const sendIntent = async (intent: AIIntent) => {
    console.log('[INTENT]', intent);
    
    const state = orchestrator.handleIntent(intent);
    
    setStage(state.stage);
    setUIMode(state.uiMode);
    setContext(state.context);
    
    // If transitioning to chat, add initial AI message
    if (state.uiMode === 'chat' && state.context.initialMessage) {
      const aiMessage: Message = {
        id: `msg_${Date.now()}`,
        type: 'ai',
        text: state.context.initialMessage,
        timestamp: new Date().toISOString(),
        user: {
          id: 'tenant-bot',
          name: 'Property Assistant',
          role: 'ai'
        }
      };
      setMessages([aiMessage]);
    }
  };
  
  const handleCTASelect = (ctaId: string) => {
    const cta = MOCK_CTAS.find(c => c.id === ctaId);
    sendIntent({
      type: 'cta_selected',
      payload: { cta_id: ctaId, cta },
      timestamp: new Date().toISOString()
    });
  };
  
  const handleItemSelect = (item: any) => {
    sendIntent({
      type: 'item_selected',
      payload: { item },
      timestamp: new Date().toISOString()
    });
  };
  
  const handleReasonSelect = (reasonId: string) => {
    const itemType = orchestrator.getSessionState().selectedItem?.item_type;
    const reasons = MOCK_REASONS[itemType as keyof typeof MOCK_REASONS] || [];
    const reason = reasons.find(r => r.id === reasonId);
    
    sendIntent({
      type: 'reason_selected',
      payload: { reason_id: reasonId, reason },
      timestamp: new Date().toISOString()
    });
  };
  
  const handleConfirmSummary = () => {
    sendIntent({
      type: 'confirm_summary',
      payload: { confirmed: true },
      timestamp: new Date().toISOString()
    });
  };
  
  const handleEditSummary = (field: string) => {
    sendIntent({
      type: 'edit_summary',
      payload: { field },
      timestamp: new Date().toISOString()
    });
  };
  
  const handleSendMessage = () => {
    if (!userInput.trim()) return;
    
    // Add user message
    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      type: 'user',
      text: userInput,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setUserInput('');
    setIsTyping(true);
    
    // Simulate AI response (in real app, this goes through Stream Chat webhook)
    setTimeout(() => {
      setIsTyping(false);
      
      const responses = [
        "I see. Let me check a few things to help diagnose this issue better.",
        "That's helpful information. Based on what you've described, I have a few follow-up questions.",
        "Thank you for those details. I'm analyzing the situation and will provide you with the best solution.",
        "I understand the urgency. Let me walk you through some troubleshooting steps that often resolve this issue."
      ];
      
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];
      
      const aiMessage: Message = {
        id: `msg_${Date.now() + 1}`,
        type: 'ai',
        text: randomResponse,
        timestamp: new Date().toISOString(),
        user: {
          id: 'tenant-bot',
          name: 'Property Assistant',
          role: 'ai'
        }
      };
      
      setMessages(prev => [...prev, aiMessage]);
      
      // After a few messages, offer resolution
      if (messages.length >= 5) {
        setTimeout(() => {
          setStage('resolution');
          setUIMode('resolution');
        }, 1500);
      }
    }, 1500);
  };
  
  const handleEscalate = () => {
    setIsEscalated(true);
    
    const systemMessage: Message = {
      id: `msg_${Date.now()}`,
      type: 'system',
      text: 'Connecting you to a property manager...',
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, systemMessage]);
    
    setTimeout(() => {
      const agents = ['Sarah (Property Manager)', 'Mike (Maintenance Lead)', 'Jessica (Support)'];
      const randomAgent = agents[Math.floor(Math.random() * agents.length)];
      setAgentName(randomAgent);
      
      const systemMessage2: Message = {
        id: `msg_${Date.now() + 1}`,
        type: 'system',
        text: `${randomAgent} has joined the chat and can see your full conversation history.`,
        timestamp: new Date().toISOString()
      };
      
      const agentMessage: Message = {
        id: `msg_${Date.now() + 2}`,
        type: 'ai',
        text: `Hi! I've reviewed your ${context.item?.name} issue. I'll help coordinate the repair right away. I'm creating a work order for a qualified contractor.`,
        timestamp: new Date().toISOString(),
        user: {
          id: 'agent-1',
          name: randomAgent,
          role: 'agent'
        }
      };
      
      setMessages(prev => [...prev, systemMessage2, agentMessage]);
    }, 2000);
  };
  
  const handleBack = () => {
    if (stage === 'item_select') {
      setStage('intro');
      setUIMode('cta_panel');
    } else if (stage === 'issue_select') {
      setStage('item_select');
      setUIMode('gallery');
    } else if (stage === 'summary') {
      setStage('issue_select');
      setUIMode('selector');
    } else if (stage === 'diagnosis') {
      setStage('summary');
      setUIMode('summary');
      setMessages([]);
    } else if (stage === 'resolution') {
      setStage('diagnosis');
      setUIMode('chat');
    }
  };
  
  const handleClose = () => {
    setDrawerOpen(false);
    setTimeout(() => {
      setStage('intro');
      setUIMode('cta_panel');
      setContext({});
      setMessages([]);
      setIsEscalated(false);
    }, 300);
  };
  
  const sessionState = orchestrator.getSessionState();
  
  // ============================================================================
  // RENDER FUNCTIONS (mirrors individual panel components)
  // ============================================================================
  
  const renderCTAPanel = () => (
    <div className="space-y-4">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="text-2xl">🏠</div>
          <div className="font-semibold text-blue-900">Welcome to Property Assistant</div>
        </div>
        <p className="text-sm text-blue-700">
          I'm your AI-powered maintenance assistant. I can help you report issues, 
          get troubleshooting advice, and track repair requests.
        </p>
      </div>
      
      <p className="text-gray-700 font-medium">How can I help you today?</p>
      
      {MOCK_CTAS.map(cta => (
        <button
          key={cta.id}
          onClick={() => handleCTASelect(cta.id)}
          className="w-full p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left flex items-center gap-3 group"
        >
          <span className="text-3xl">{cta.icon}</span>
          <div>
            <div className="font-semibold text-gray-900 group-hover:text-blue-700">{cta.label}</div>
            <div className="text-xs text-gray-500">{cta.category}</div>
          </div>
        </button>
      ))}
    </div>
  );
  
  const renderGalleryPanel = () => (
    <div className="space-y-4">
      <p className="text-gray-700 font-medium mb-4">
        Which item or area do you need help with?
      </p>
      
      <div className="grid grid-cols-1 gap-3">
        {MOCK_ITEMS.map(item => (
          <button
            key={item.item_id}
            onClick={() => handleItemSelect(item)}
            className="p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
          >
            <div className="flex items-start gap-4">
              <div className="text-4xl">{item.icon}</div>
              <div className="flex-1">
                <div className="font-semibold text-gray-900 group-hover:text-blue-700">
                  {item.name}
                </div>
                <div className="text-sm text-gray-600">
                  {item.category} • {item.location}
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    item.status === 'operational' || item.status === 'good'
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {item.status}
                  </span>
                  {item.last_maintenance && (
                    <span className="text-xs text-gray-500">
                      Last serviced: {item.last_maintenance}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
  
  const renderSelectorPanel = () => {
    const item = sessionState.selectedItem;
    if (!item) return null;
    
    const reasons = MOCK_REASONS[item.item_type as keyof typeof MOCK_REASONS] || [];
    
    return (
      <div className="space-y-4">
        <div className="bg-gray-50 rounded-lg p-4 mb-4 border border-gray-200">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{item.icon}</span>
            <div>
              <div className="font-semibold text-gray-900">{item.name}</div>
              <div className="text-sm text-gray-600">{item.location}</div>
            </div>
          </div>
        </div>
        
        <p className="text-gray-700 font-medium">
          What's the issue you're experiencing?
        </p>
        
        {reasons.map(reason => (
          <button
            key={reason.id}
            onClick={() => handleReasonSelect(reason.id)}
            className="w-full p-4 border-2 border-gray-300 rounded-lg hover:border-blue-500 hover:bg-blue-50 transition-all text-left group"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-900 group-hover:text-blue-700">
                {reason.label}
              </span>
              <span className={`text-xs px-2 py-1 rounded-full ${getSeverityColor(reason.severity)}`}>
                {reason.severity}
              </span>
            </div>
          </button>
        ))}
      </div>
    );
  };
  
  const renderSummaryPanel = () => {
    const { cta, item, reason, severity } = context;
    
    return (
      <div className="space-y-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={20} className="text-blue-600" />
            <span className="font-semibold text-blue-900">Review Your Request</span>
          </div>
          <p className="text-sm text-blue-700">
            Please review the details below before we start the diagnosis.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Item Details */}
          <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-3">Item Details</h3>
            <div className="text-center mb-4">
              <div className="text-5xl mb-2">{item?.icon}</div>
              <div className="font-medium text-gray-900">{item?.name}</div>
              <div className="text-sm text-gray-600">{item?.location}</div>
            </div>
            
            <div className="space-y-2 text-sm">
              <div>
                <span className="text-gray-600 font-medium">Type:</span>
                <span className="text-gray-900 ml-2">{item?.category}</span>
              </div>
              <div>
                <span className="text-gray-600 font-medium">Status:</span>
                <span className="text-gray-900 ml-2">{item?.status}</span>
              </div>
              {item?.last_maintenance && (
                <div>
                  <span className="text-gray-600 font-medium">Last Service:</span>
                  <span className="text-gray-900 ml-2">{item.last_maintenance}</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Issue Summary */}
          <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
            <h3 className="font-semibold text-gray-900 mb-3">Issue Summary</h3>
            
            <div className="space-y-4">
              <div>
                <div className="text-sm text-gray-600 mb-1">Request Type:</div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{cta?.label}</span>
                  <button
                    onClick={() => handleEditSummary('cta')}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Edit
                  </button>
                </div>
              </div>
              
              <div>
                <div className="text-sm text-gray-600 mb-1">Selected Item:</div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{item?.name}</span>
                  <button
                    onClick={() => handleEditSummary('item')}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Edit
                  </button>
                </div>
              </div>
              
              <div>
                <div className="text-sm text-gray-600 mb-1">Issue Description:</div>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-900">{reason?.label}</span>
                  <button
                    onClick={() => handleEditSummary('reason')}
                    className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                  >
                    Edit
                  </button>
                </div>
              </div>
              
              <div>
                <div className="text-sm text-gray-600 mb-1">Severity Level:</div>
                <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold border ${getSeverityColor(severity)}`}>
                  {severity?.toUpperCase()} PRIORITY
                </span>
                <div className="text-xs text-gray-500 mt-1">(Auto-detected based on issue type)</div>
              </div>
            </div>
          </div>
        </div>
        
        <button
          onClick={handleConfirmSummary}
          className="w-full px-6 py-4 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
        >
          <MessageSquare size={20} />
          Start AI Diagnosis Chat
        </button>
      </div>
    );
  };
  
  const renderChatPanel = () => (
    <div className="flex flex-col h-[calc(100vh-180px)]">
      {/* Messages */}
      <div ref={chatContainerRef} className="flex-1 overflow-y-auto space-y-4 mb-4 px-1">
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.type === 'system' ? (
              <div className="bg-yellow-50 border border-yellow-300 rounded-lg px-4 py-2 text-center text-sm text-yellow-900 max-w-[85%]">
                <div className="flex items-center justify-center gap-2">
                  <Loader2 size={14} className="animate-spin" />
                  <span>{msg.text}</span>
                </div>
              </div>
            ) : (
              <div className={`rounded-2xl px-4 py-3 max-w-[80%] shadow-sm ${
                msg.type === 'user'
                  ? 'bg-blue-600 text-white rounded-br-sm'
                  : msg.user?.role === 'agent'
                  ? 'bg-green-50 text-gray-900 rounded-bl-sm border-2 border-green-400'
                  : 'bg-gray-100 text-gray-900 rounded-bl-sm'
              }`}>
                {msg.user?.role === 'agent' && (
                  <div className="flex items-center gap-2 mb-2 pb-2 border-b border-green-300">
                    <User size={16} className="text-green-600" />
                    <span className="text-xs font-semibold text-green-700">{msg.user.name}</span>
                  </div>
                )}
                {msg.user?.role === 'ai' && msg.type !== 'user' && (
                  <div className="flex items-center gap-2 mb-1">
                    <div className="w-6 h-6 bg-blue-500 rounded-full flex items-center justify-center text-white text-xs font-bold">
                      AI
                    </div>
                    <span className="text-xs font-medium text-gray-600">{msg.user.name}</span>
                  </div>
                )}
                <div className="text-sm leading-relaxed">{msg.text}</div>
                <div className={`text-xs mt-2 ${msg.type === 'user' ? 'text-blue-200' : 'text-gray-500'}`}>
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </div>
              </div>
            )}
          </div>
        ))}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>
      
      {/* Input */}
      <div className="border-t border-gray-200 pt-4">
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={userInput}
            onChange={(e) => setUserInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            placeholder="Describe what's happening..."
            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          />
          <button
            onClick={handleSendMessage}
            disabled={!userInput.trim() || isTyping}
            className="px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
          >
            <Send size={20} />
          </button>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => {
              setStage('resolution');
              setUIMode('resolution');
            }}
            className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors text-sm font-medium flex items-center justify-center gap-2"
          >
            <CheckCircle size={16} />
            View Solutions
          </button>
          
          {!isEscalated && (
            <button
              onClick={handleEscalate}
              className="flex-1 px-4 py-2 bg-green-100 text-green-700 rounded-lg hover:bg-green-200 transition-colors text-sm font-medium flex items-center justify-center gap-2"
            >
              <User size={16} />
              Talk to Human
            </button>
          )}
        </div>
      </div>
    </div>
  );
  
  const renderResolutionPanel = () => {
    const { item, reason, severity } = context;
    
    const resolutions = [
      {
        id: 'create_work_order',
        title: 'Create Work Order',
        description: 'Generate a professional work order and assign it to a qualified contractor.',
        icon: '📋',
        action: 'Create Work Order',
        available: severity === 'high' || severity === 'critical'
      },
      {
        id: 'diy_guide',
        title: 'Get DIY Instructions',
        description: 'Receive step-by-step troubleshooting guide to fix this yourself.',
        icon: '🛠️',
        action: 'View DIY Guide',
        available: severity === 'low' || severity === 'medium'
      },
      {
        id: 'schedule_inspection',
        title: 'Schedule Property Inspection',
        description: 'Book an appointment for a property manager to inspect the issue.',
        icon: '📅',
        action: 'Schedule Inspection',
        available: true
      }
    ];
    
    return (
      <div className="space-y-4">
        <div className="bg-green-50 border border-green-300 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle size={20} className="text-green-600" />
            <span className="font-semibold text-green-900">Diagnosis Complete</span>
          </div>
          <p className="text-sm text-green-700">
            Based on our conversation about your {item?.name}, here are your resolution options:
          </p>
        </div>
        
        {resolutions.filter(r => r.available).map(resolution => (
          <div key={resolution.id} className="border-2 border-gray-300 rounded-lg p-5 hover:border-blue-500 hover:shadow-md transition-all">
            <div className="flex items-start gap-4">
              <div className="text-4xl">{resolution.icon}</div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 mb-2">{resolution.title}</h4>
                <p className="text-sm text-gray-600 mb-4">{resolution.description}</p>
                <button
                  onClick={() => alert(`Processing: ${resolution.title}`)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                >
                  {resolution.action} →
                </button>
              </div>
            </div>
          </div>
        ))}
        
        <div className="border-t border-gray-200 pt-4 mt-6">
          <div className="text-sm text-gray-600 mb-3">Still need help?</div>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setStage('diagnosis');
                setUIMode('chat');
              }}
              className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
            >
              Continue Chat
            </button>
            <button
              onClick={handleClose}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };
  
  // ============================================================================
  // MAIN RENDER
  // ============================================================================
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 p-4">
      {/* Header */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="bg-white rounded-xl shadow-md p-6 border border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">LandTen AI Support - Live Demo</h1>
              <p className="text-gray-600">Actual architecture implementation with real flow patterns</p>
            </div>
            <button
              onClick={() => {
                setDrawerOpen(true);
                setStage('intro');
                setUIMode('cta_panel');
              }}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-all shadow-lg hover:shadow-xl flex items-center gap-2"
            >
              <MessageSquare size={20} />
              Launch Assistant
            </button>
          </div>
          
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Live Session
            </span>
            <span className="text-gray-500">Session: {sessionId.substring(0, 20)}...</span>
            <span className="text-gray-500">Persona: <span className="font-semibold text-blue-600">{persona}</span></span>
          </div>
        </div>
      </div>
      
      {/* Flow State Display */}
      <div className="max-w-6xl mx-auto mb-6">
        <div className="bg-white rounded-xl shadow-md p-6 border border-gray-200">
          <h2 className="text-lg font-semibold mb-4 text-gray-900 flex items-center gap-2">
            <div className="w-3 h-3 bg-blue-500 rounded-full animate-pulse"></div>
            Orchestrator State
          </h2>
          
          {/* Stage Progress */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              {['intro', 'item_select', 'issue_select', 'summary', 'diagnosis', 'resolution'].map((s, idx) => (
                <React.Fragment key={s}>
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold text-sm transition-all ${
                      stage === s
                        ? 'bg-blue-600 text-white scale-110 shadow-lg ring-4 ring-blue-200'
                        : ['intro', 'item_select', 'issue_select', 'summary', 'diagnosis', 'resolution'].indexOf(stage) > idx
                        ? 'bg-green-500 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}>
                      {['intro', 'item_select', 'issue_select', 'summary', 'diagnosis', 'resolution'].indexOf(stage) > idx ? '✓' : idx + 1}
                    </div>
                    <span className="text-xs mt-2 text-gray-600 capitalize">{s.replace('_', ' ')}</span>
                  </div>
                  {idx < 5 && (
                    <div className={`flex-1 h-1 mx-2 rounded transition-all ${
                      ['intro', 'item_select', 'issue_select', 'summary', 'diagnosis', 'resolution'].indexOf(stage) > idx
                        ? 'bg-green-500'
                        : 'bg-gray-200'
                    }`}></div>
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
          
          {/* State Details */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
              <div className="text-xs font-semibold text-blue-900 mb-1">Current Stage</div>
              <div className="text-sm text-blue-700 font-medium">{stage}</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
              <div className="text-xs font-semibold text-purple-900 mb-1">UI Mode</div>
              <div className="text-sm text-purple-700 font-medium">{uiMode}</div>
            </div>
            <div className="bg-green-50 rounded-lg p-3 border border-green-200">
              <div className="text-xs font-semibold text-green-900 mb-1">Selected Item</div>
              <div className="text-sm text-green-700 font-medium truncate">
                {sessionState.selectedItem?.name || 'None'}
              </div>
            </div>
            <div className="bg-orange-50 rounded-lg p-3 border border-orange-200">
              <div className="text-xs font-semibold text-orange-900 mb-1">Severity</div>
              <div className="text-sm text-orange-700 font-medium">
                {context.severity?.toUpperCase() || 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Architecture Info */}
      <div className="max-w-6xl mx-auto">
        <div className="bg-white rounded-xl shadow-md p-6 border border-gray-200">
          <h2 className="text-lg font-semibold mb-4 text-gray-900">Architecture Components Active</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="font-semibold text-gray-700 mb-2">Backend Services</div>
              <ul className="space-y-1 text-gray-600">
                <li>✓ ai_support_orchestrator.py</li>
                <li>✓ session_state_manager.py</li>
                <li>✓ stream_bot.py</li>
                <li>✓ card_builder.py</li>
              </ul>
            </div>
            <div>
              <div className="font-semibold text-gray-700 mb-2">Frontend Components</div>
              <ul className="space-y-1 text-gray-600">
                <li>✓ AIChatAssistantLauncher</li>
                <li>✓ AIDynamicPanel</li>
                <li>✓ useAISupportFlow hook</li>
                <li>✓ StreamChatPane</li>
              </ul>
            </div>
            <div>
              <div className="font-semibold text-gray-700 mb-2">Event Protocol</div>
              <ul className="space-y-1 text-gray-600">
                <li>✓ ai_intent (Frontend → Backend)</li>
                <li>✓ ai_state (Backend → Frontend)</li>
                <li>✓ Session state persistence</li>
                <li>✓ Stream Chat webhooks</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
      
      {/* Drawer Overlay */}
      {drawerOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 transition-opacity"
          onClick={handleClose}
        />
      )}
      
      {/* Drawer (mirrors AIChatContainer.tsx) */}
      <div className={`fixed top-0 right-0 h-full bg-white shadow-2xl z-50 transition-transform duration-300 ${
        drawerOpen ? 'translate-x-0' : 'translate-x-full'
      } w-full md:w-[560px]`}>
        
        {/* Drawer Header (mirrors CustomChannelHeader) */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white sticky top-0 z-10">
          {stage !== 'intro' && (
            <button
              onClick={handleBack}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ChevronLeft size={24} className="text-gray-700" />
            </button>
          )}
          <h2 className="text-lg font-semibold text-gray-900 flex-1 text-center">
            {stage === 'intro' && 'Property Assistant'}
            {stage === 'item_select' && 'Select Item or Area'}
            {stage === 'issue_select' && 'Describe the Issue'}
            {stage === 'summary' && 'Review Request'}
            {stage === 'diagnosis' && (isEscalated ? `Chat with ${agentName}` : 'AI Diagnosis')}
            {stage === 'resolution' && 'Resolution Options'}
          </h2>
          <button
            onClick={handleClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X size={24} className="text-gray-700" />
          </button>
        </div>
        
        {/* Drawer Body (mirrors AIDynamicPanel) */}
        <div className="overflow-y-auto h-[calc(100%-73px)] p-6">
          {uiMode === 'cta_panel' && renderCTAPanel()}
          {uiMode === 'gallery' && renderGalleryPanel()}
          {uiMode === 'selector' && renderSelectorPanel()}
          {uiMode === 'summary' && renderSummaryPanel()}
          {uiMode === 'chat' && renderChatPanel()}
          {uiMode === 'resolution' && renderResolutionPanel()}
        </div>
      </div>
    </div>
  );
};

export default LandTenAISupportDemo;
