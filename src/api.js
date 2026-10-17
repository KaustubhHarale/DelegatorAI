// All frontend API calls live here.
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `Cannot reach the backend at ${API_BASE}. Start the FastAPI server and check that FRONTEND_ORIGINS allows this frontend's origin.`,
      );
    }
    throw error;
  }
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
  chatWithCoordinator: (message, history = []) => request("/assistant/chat", {
    method: "POST",
    body: JSON.stringify({ message, history }),
  }),
};

export { API_BASE };