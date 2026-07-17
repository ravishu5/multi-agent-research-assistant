const API_BASE = import.meta.env.VITE_API_URL || '/api/v1';

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.json();
}

export const api = {
  submitJob: (data) =>
    request('/jobs/submit', { method: 'POST', body: JSON.stringify(data) }),

  getStatus: (jobId) =>
    request(`/jobs/${jobId}/status`),

  getResult: (jobId) =>
    request(`/jobs/${jobId}/result`),

  approveJob: (jobId, approved, feedback = '') =>
    request(`/jobs/${jobId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ approved, feedback }),
    }),

  listJobs: () =>
    request('/jobs/'),
};
