/**
 * Central API Client for Team MCP Gateway.
 * Interacts with backend FastAPI gateway REST endpoints.
 */

// If deployed under Ingress or Vite proxy, relative /api paths work seamlessly
const API_BASE = import.meta.env.VITE_API_URL || '/api';

export const authStorage = {
  getToken: () => localStorage.getItem('mcp_token'),
  setToken: (token) => localStorage.setItem('mcp_token', token),
  getUser: () => {
    const raw = localStorage.getItem('mcp_user');
    try {
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  },
  setUser: (user) => localStorage.setItem('mcp_user', JSON.stringify(user)),
  clear: () => {
    localStorage.removeItem('mcp_token');
    localStorage.removeItem('mcp_user');
  },
};

async function apiRequest(endpoint, options = {}) {
  const token = authStorage.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    // If unauthorized, clear invalid session
    if (!endpoint.includes('/auth/login')) {
      authStorage.clear();
      window.dispatchEvent(new Event('auth-change'));
    }
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMsg = data.detail || data.error || `HTTP ${response.status}: Request failed`;
    throw new Error(errorMsg);
  }

  return data;
}

export const api = {
  // Auth
  async login(email, password) {
    const data = await apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    authStorage.setToken(data.access_token);
    const userObj = data.user || { email: data.email, role: data.role };
    authStorage.setUser({ email: userObj.email, role: userObj.role });
    window.dispatchEvent(new Event('auth-change'));
    return data;
  },

  logout() {
    authStorage.clear();
    window.dispatchEvent(new Event('auth-change'));
  },

  getCurrentUser() {
    return authStorage.getUser();
  },

  // Servers
  async getServers() {
    return apiRequest('/servers');
  },

  async toggleServer(serverId) {
    return apiRequest(`/servers/${serverId}/toggle`, {
      method: 'POST',
    });
  },

  // Tools
  async getTools() {
    const data = await apiRequest('/tools');
    return Array.isArray(data) ? data : (data.tools || []);
  },

  // API Keys
  async getKeys() {
    return apiRequest('/keys');
  },

  async createKey(name) {
    return apiRequest('/keys', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  async revokeKey(keyId) {
    return apiRequest(`/keys/${keyId}`, {
      method: 'DELETE',
    });
  },

  // Audit Logs
  async getAuditLogs({ limit = 50, status, tool } = {}) {
    const params = new URLSearchParams();
    if (limit) params.set('limit', limit);
    if (status && status !== 'all') params.set('status', status);
    if (tool) params.set('tool', tool);
    const qs = params.toString();
    return apiRequest(`/audit${qs ? `?${qs}` : ''}`);
  },

  // Chat Agent
  async sendChat(message, history = []) {
    return apiRequest('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history }),
    });
  },
};
