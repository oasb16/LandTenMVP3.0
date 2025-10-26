/**
 * React hooks for PropertyAI data management
 */

import { useState, useEffect, useCallback } from 'react';
import * as api from '@/lib/api';

// ==================== INCIDENTS ====================

export function useIncidents(tenantId: string | null) {
  const [incidents, setIncidents] = useState<api.Incident[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchIncidents = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listIncidents(tenantId);
      setIncidents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load incidents');
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const createIncident = async (incident: Omit<api.Incident, 'created_at'>) => {
    try {
      const newIncident = await api.createIncident(incident);
      setIncidents(prev => [newIncident, ...prev]);
      return newIncident;
    } catch (err) {
      throw err;
    }
  };

  return { incidents, loading, error, refetch: fetchIncidents, createIncident };
}

// ==================== TASKS ====================

export function useTasks(persona: string | null) {
  const [tasks, setTasks] = useState<api.Task[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTasks = useCallback(async () => {
    if (!persona) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listTasks(persona);
      setTasks(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tasks');
    } finally {
      setLoading(false);
    }
  }, [persona]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  const createTask = async (task: Omit<api.Task, 'task_id'>) => {
    try {
      const newTask = await api.createTask(task);
      setTasks(prev => [newTask, ...prev]);
      return newTask;
    } catch (err) {
      throw err;
    }
  };

  const updateStatus = async (taskId: string, status: string) => {
    try {
      await api.updateTaskStatus(taskId, status);
      setTasks(prev =>
        prev.map(t => (t.task_id === taskId ? { ...t, status } : t))
      );
    } catch (err) {
      throw err;
    }
  };

  return { tasks, loading, error, refetch: fetchTasks, createTask, updateStatus };
}

// ==================== JOBS ====================

export function useJobs(contractorId: string | null) {
  const [jobs, setJobs] = useState<api.Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    if (!contractorId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.listJobs(contractorId);
      setJobs(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  }, [contractorId]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const createJob = async (job: Omit<api.Job, 'id'>) => {
    try {
      const newJob = await api.createJob(job);
      setJobs(prev => [newJob, ...prev]);
      return newJob;
    } catch (err) {
      throw err;
    }
  };

  return { jobs, loading, error, refetch: fetchJobs, createJob };
}

// ==================== PROPERTIES ====================

export function useProperties(landlordId: string | null) {
  // TODO: Backend doesn't have property API yet
  // For now, return mock data
  const [properties] = useState<api.Property[]>([
    { id: 1, name: '123 Oakwood Ave', tenants: 1, incidents: 0, status: 'Active' },
    { id: 2, name: '456 Maple St', tenants: 1, incidents: 0, status: 'Active' }
  ]);

  return { properties, loading: false, error: null };
}

// ==================== MEDIA UPLOAD ====================

export function useMediaUpload() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const upload = async (file: File): Promise<string | null> => {
    setUploading(true);
    setError(null);
    try {
      const url = await api.uploadMedia(file);
      return url;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to upload media';
      setError(message);
      return null;
    } finally {
      setUploading(false);
    }
  };

  return { upload, uploading, error };
}
