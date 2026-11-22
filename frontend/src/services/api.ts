import { CreateJobPayload, Job, TimelineData } from '../types';

const API_BASE = '/api/v1';

export const api = {
  async getHealth() {
    const res = await fetch('/health');
    return res.json();
  },

  async getReady() {
    const res = await fetch('/ready');
    return res.json();
  },

  async getConfig() {
    const res = await fetch(`${API_BASE}/config`);
    return res.json();
  },

  async getProviders() {
    const res = await fetch(`${API_BASE}/providers`);
    return res.json();
  },

  async getJobs(limit = 20, offset = 0): Promise<{ total: number; jobs: Job[] }> {
    const res = await fetch(`${API_BASE}/jobs?limit=${limit}&offset=${offset}`);
    if (!res.ok) throw new Error('Failed to fetch jobs list');
    return res.json();
  },

  async getJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message || `Failed to fetch job ${jobId}`);
    }
    return res.json();
  },

  async createJob(payload: CreateJobPayload, idempotencyKey?: string): Promise<Job> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }

    const res = await fetch(`${API_BASE}/broll/jobs`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message || 'Job submission failed');
    }
    return res.json();
  },

  async uploadAudioJob(formData: FormData, idempotencyKey?: string): Promise<Job> {
    const headers: Record<string, string> = {};
    if (idempotencyKey) {
      headers['Idempotency-Key'] = idempotencyKey;
    }

    const res = await fetch(`${API_BASE}/broll/jobs/upload`, {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message || 'Audio upload job failed');
    }
    return res.json();
  },

  async getTimeline(jobId: string): Promise<TimelineData> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/timeline`);
    if (!res.ok) throw new Error('Failed to fetch timeline');
    return res.json();
  },

  async getManifest(jobId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/manifest`);
    if (!res.ok) throw new Error('Failed to fetch manifest');
    return res.json();
  },

  async swapSceneClip(jobId: string, sceneId: string, newVisualHint?: string): Promise<any> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/scenes/${sceneId}/swap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ visual_hint: newVisualHint }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err?.error?.message || 'Scene swap failed');
    }
    return res.json();
  },
};
