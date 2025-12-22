/**
 * API Service Layer for PropertyAI
 * Handles all backend communication with proper error handling
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

const getBackendUrl = () => {
  return process.env.NEXT_PUBLIC_BACKEND_URL || '';
};

const getAuthHeaders = () => {
  // In dev mode, backend accepts any Authorization header
  // In production, this should be a proper Firebase token
  return {
    'Content-Type': 'application/json',
    'Authorization': 'dev', // Will be replaced with real token in production
  };
};

export interface Incident {
  id: string;
  tenant_id: string;
  description: string;
  status: string;
  created_at?: string;
  title?: string;
  severity?: string;
  property?: string;
  tenant?: string;
  created?: string;
  priority?: string;
}

export interface Task {
  task_id: string;
  title: string;
  description: string;
  status: string;
  persona?: string;
  assigned_to?: string;
  created_at?: string;
  created?: string;
  priority?: string;
}

export interface Job {
  id: string;
  incident_id: string;
  contractor_id: string;
  status: string;
  scheduled_time?: string;
  title?: string;
  property?: string;
  budget?: string;
  distance?: string;
  urgency?: string;
  matchScore?: number;
}

export interface Property {
  id: string;
  name: string;
  address: string;
  landlord_id: string;
  tenants: string[];
  status: string;
  created_at?: string;
}

export interface Profile {
  user_id: string;
  persona: string;
  email?: string;
}

// ==================== INCIDENTS ====================

export async function createIncident(incident: Omit<Incident, 'created_at'>): Promise<Incident> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/incident/create`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(incident),
  });

  if (!response.ok) {
    throw new Error(`Failed to create incident: ${response.statusText}`);
  }

  const data = await response.json();
  return data.incident;
}

export async function listIncidents(tenantId: string): Promise<Incident[]> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/incident/list/${encodeURIComponent(tenantId)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to list incidents: ${response.statusText}`);
  }

  const data = await response.json();
  return data.incidents || [];
}

// ==================== TASKS ====================

export async function createTask(task: Omit<Task, 'task_id'>): Promise<Task> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const taskWithId = {
    ...task,
    task_id: `task-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  };

  const response = await fetch(`${backendUrl}/task/create`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(taskWithId),
  });

  if (!response.ok) {
    throw new Error(`Failed to create task: ${response.statusText}`);
  }

  const data = await response.json();
  return data.task || taskWithId;
}

export async function listTasks(persona: string): Promise<Task[]> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/task/list/${encodeURIComponent(persona)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to list tasks: ${response.statusText}`);
  }

  const data = await response.json();
  return data.tasks || [];
}

export async function updateTaskStatus(taskId: string, status: string): Promise<void> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/task/update_status`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ task_id: taskId, status }),
  });

  if (!response.ok) {
    throw new Error(`Failed to update task status: ${response.statusText}`);
  }
}

// ==================== JOBS ====================

export async function createJob(job: Omit<Job, 'id'>): Promise<Job> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const jobWithId = {
    ...job,
    id: `job-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  };

  const response = await fetch(`${backendUrl}/job/create`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(jobWithId),
  });

  if (!response.ok) {
    throw new Error(`Failed to create job: ${response.statusText}`);
  }

  const data = await response.json();
  return data.job || jobWithId;
}

export async function listJobs(contractorId: string): Promise<Job[]> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/job/list/${encodeURIComponent(contractorId)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to list jobs: ${response.statusText}`);
  }

  const data = await response.json();
  return data.jobs || [];
}

// ==================== PROFILE ====================

export async function getProfile(email: string): Promise<Profile | null> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) return null;

  try {
    const response = await fetch(`${backendUrl}/profile/${encodeURIComponent(email)}`, {
      headers: getAuthHeaders(),
    });

    if (!response.ok) return null;

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Failed to get profile:', error);
    return null;
  }
}

export async function saveProfile(userId: string, persona: string): Promise<void> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/profile`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ user_id: userId, persona }),
  });

  if (!response.ok) {
    throw new Error(`Failed to save profile: ${response.statusText}`);
  }
}

// ==================== MEDIA ====================

export async function getMediaUploadUrl(filename: string, contentType: string): Promise<{ upload_url: string; asset_url: string }> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(
    `${backendUrl}/media/upload_url?filename=${encodeURIComponent(filename)}&content_type=${encodeURIComponent(contentType)}`,
    {
      headers: getAuthHeaders(),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get upload URL: ${response.statusText}`);
  }

  return response.json();
}

export async function uploadMedia(file: File): Promise<string> {
  // Step 1: Get presigned URL
  const { upload_url, asset_url } = await getMediaUploadUrl(file.name, file.type);

  // Step 2: Upload directly to S3
  const uploadResponse = await fetch(upload_url, {
    method: 'PUT',
    headers: {
      'Content-Type': file.type,
    },
    body: file,
  });

  if (!uploadResponse.ok) {
    throw new Error(`Failed to upload media: ${uploadResponse.statusText}`);
  }

  return asset_url;
}

// ==================== PROPERTIES ====================

export async function createProperty(property: Omit<Property, 'id' | 'created_at'>): Promise<Property> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/property/create`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(property),
  });

  if (!response.ok) {
    throw new Error(`Failed to create property: ${response.statusText}`);
  }

  const data = await response.json();
  return data.property;
}

export async function listProperties(landlordId: string): Promise<Property[]> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/property/list/${encodeURIComponent(landlordId)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to list properties: ${response.statusText}`);
  }

  const data = await response.json();
  return data.properties || [];
}

export async function getTenantProperty(tenantId: string): Promise<Property | null> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/property/tenant/${encodeURIComponent(tenantId)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get tenant property: ${response.statusText}`);
  }

  const data = await response.json();
  return data.property;
}

// ==================== AI BOT ====================

export interface AIAction {
  name: string;
  text: string;
  style?: string;
  value: string;
}

export interface AIBotStatus {
  status: string;
  bots: {
    [persona: string]: {
      id: string;
      name: string;
      description: string;
    };
  };
  webhook_configured: boolean;
}

/**
 * Initialize AI bot in a channel
 */
export async function initializeAIChannel(channelId: string, persona: string): Promise<any> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/init-channel`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      channel_id: channelId,
      persona: persona,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to initialize AI channel: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Send AI message with action buttons
 */
export async function sendAIAction(
  channelId: string,
  persona: string,
  text: string,
  actions: AIAction[]
): Promise<any> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/send-action`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      channel_id: channelId,
      persona: persona,
      text: text,
      actions: actions,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send AI action: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Get AI bot status
 */
export async function getAIBotStatus(): Promise<AIBotStatus> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/bot-status`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get AI bot status: ${response.statusText}`);
  }

  return await response.json();
}

// ==================== PAYMENTS ====================

export interface BankAccountDetails {
  contractor_id: string;
  account_number: string;
  routing_number: string;
  account_holder_name: string;
  account_holder_type?: string;
}

export interface PaymentInfo {
  contractor_id: string;
  payment_enabled: boolean;
  bank_account_last4?: string;
  bank_account_status?: string;
  has_stripe_account: boolean;
}

export interface PaymentRequest {
  contractor_id: string;
  amount: number;
  description: string;
  job_id?: string;
  incident_id?: string;
}

export interface PaymentResponse {
  status: string;
  transfer_id: string;
  amount: number;
  contractor_id: string;
  contractor_name?: string;
  description: string;
  transfer_status: string;
}

/**
 * Add bank account details for a contractor
 */
export async function addBankAccount(details: BankAccountDetails): Promise<any> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/contractor/bank-account`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(details),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to add bank account: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Get payment information for a contractor
 */
export async function getPaymentInfo(contractorId: string): Promise<PaymentInfo> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/contractor/payment-info/${encodeURIComponent(contractorId)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get payment info: ${response.statusText}`);
  }

  return await response.json();
}

/**
 * Initiate a payment from landlord to contractor
 */
export async function initiatePayment(payment: PaymentRequest): Promise<PaymentResponse> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/contractor/payment/initiate`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payment),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to initiate payment: ${response.statusText}`);
  }

  return await response.json();
}

// ==================== ANALYTICS ====================

export interface AnalyticsSummary {
  total_sessions: number;
  completion_rate: number;
  personas: { [key: string]: number };
  top_ctas: Array<{ name: string; count: number }>;
  top_items: Array<{ name: string; count: number }>;
  top_reasons: Array<{ name: string; count: number }>;
  top_actions: Array<{ name: string; count: number }>;
  dropoff_stages: { [key: string]: number };
}

export interface PersonaAnalytics {
  persona: string;
  total_sessions: number;
  completion_rate: number;
  top_reasons: Array<{ name: string; count: number }>;
  top_actions: Array<{ name: string; count: number }>;
}

export interface IssueTrends {
  total_issues: number;
  reasons: Array<{ name: string; count: number; percentage: number }>;
  cta_reason_patterns: { [key: string]: { [key: string]: number } };
}

export interface SatisfactionMetrics {
  satisfied: number;
  neutral: number;
  unsatisfied: number;
  abandoned: number;
  overall_score: number;
}

export interface AnalyticsDashboard {
  summary: AnalyticsSummary;
  trends: IssueTrends;
  satisfaction: SatisfactionMetrics;
  personas: {
    tenant: PersonaAnalytics;
    landlord: PersonaAnalytics;
    contractor: PersonaAnalytics;
    property_manager: PersonaAnalytics;
  };
}

/**
 * Get analytics summary
 */
export async function getAnalyticsSummary(): Promise<AnalyticsSummary> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/analytics/summary`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get analytics summary: ${response.statusText}`);
  }

  const data = await response.json();
  return data.data;
}

/**
 * Get persona-specific analytics
 */
export async function getPersonaAnalytics(persona: string): Promise<PersonaAnalytics> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/analytics/persona/${encodeURIComponent(persona)}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get persona analytics: ${response.statusText}`);
  }

  const data = await response.json();
  return data.data;
}

/**
 * Get issue trends
 */
export async function getIssueTrends(): Promise<IssueTrends> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/analytics/trends`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get issue trends: ${response.statusText}`);
  }

  const data = await response.json();
  return data.data;
}

/**
 * Get satisfaction metrics
 */
export async function getSatisfactionMetrics(): Promise<SatisfactionMetrics> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/analytics/satisfaction`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get satisfaction metrics: ${response.statusText}`);
  }

  const data = await response.json();
  return data.data;
}

/**
 * Get full analytics dashboard
 */
export async function getAnalyticsDashboard(): Promise<AnalyticsDashboard> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const response = await fetch(`${backendUrl}/ai/analytics/dashboard`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get analytics dashboard: ${response.statusText}`);
  }

  const data = await response.json();
  return data.data;
}

// ==================== GAMIFICATION ====================

export interface LeaderboardEntry {
  contractor_id: string;
  rank: number;
  display_name: string;
  score: number;
  level: string;
  jobs_completed: number;
  rating: number;
  badges_count: number;
  show_name: boolean;
}

/**
 * Get leaderboard rankings
 */
export async function getLeaderboard(
  category?: string,
  zipCode?: string,
  limit = 50
): Promise<LeaderboardEntry[]> {
  const backendUrl = getBackendUrl();
  if (!backendUrl) throw new Error('Backend URL not configured');

  const params = new URLSearchParams();
  if (category) params.append('category', category);
  if (zipCode) params.append('zip_code', zipCode);
  params.append('limit', limit.toString());

  const response = await fetch(`${backendUrl}/gamification/leaderboard?${params}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    throw new Error(`Failed to get leaderboard: ${response.statusText}`);
  }

  const data = await response.json();
  return data.leaderboard;
}
