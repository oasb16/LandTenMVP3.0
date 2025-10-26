/**
 * API Service Layer for PropertyAI
 * Handles all backend communication with proper error handling
 */

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
  id: number;
  name: string;
  tenants: number;
  incidents: number;
  status: string;
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
