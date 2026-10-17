// All frontend API calls live here.
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try {
      const parsed = JSON.parse(body);
      message = parsed.detail || body;
    } catch {
      // Keep the response body when the server did not return JSON.
    }
    throw new Error(message || `API request failed (${response.status})`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export const api = {
  getParticipants: () => request("/participants"),
  getTasks: () => request("/tasks"),
  createTask: (task) => request("/tasks", { method: "POST", body: JSON.stringify(task) }),
  updateTask: (id, patch) => request(`/tasks/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  getTaskHistory: (id) => request(`/tasks/${id}/history`),
  followUpTask: (id) => request(`/tasks/${id}/follow-up`, { method: "POST" }),
};

export { API_BASE };