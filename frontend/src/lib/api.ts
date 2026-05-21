const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type TokenPair = {
  access_token: string;
  refresh_token: string;
};

export const api = {
  // Auth
  register: async (email: string, password: string, name?: string) => {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, name }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Registration failed');
    }
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
    }
    return data;
  },

  login: async (email: string, password: string) => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || 'Login failed');
    }
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
    }
    return data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  getMe: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) throw new Error('Not authenticated');

    const res = await fetch(`${API_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to get user');
    return res.json();
  },

  refreshToken: async () => {
    const refresh_token = localStorage.getItem('refresh_token');
    if (!refresh_token) throw new Error('No refresh token');

    const res = await fetch(`${API_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token }),
    });
    if (!res.ok) throw new Error('Token refresh failed');
    const data = await res.json();
    if (data.access_token) {
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('refresh_token', data.refresh_token);
    }
    return data;
  },

  // RFPs
  uploadRFP: async (file?: File, content?: string) => {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();

    if (file) {
      formData.append('file', file);
    }
    if (content) {
      formData.append('content', content);
    }

    const res = await fetch(`${API_URL}/api/rfps/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload RFP');
    return res.json();
  },

  listRFPs: async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to list RFPs');
    return res.json();
  },

  getRFP: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to get RFP');
    return res.json();
  },

  getRFPContent: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/${id}/content`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to get RFP content');
    return res.json();
  },

  deleteRFP: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to delete RFP');
    return res.json();
  },

  // Extraction
  extractRFP: async (rfpId: number, engines: string[] = ['claude']) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/${rfpId}/extract?engines=${engines.join(',')}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to extract RFP');
    return res.json();
  },

  getExtractionResults: async (rfpId: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/${rfpId}/extraction-results`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to get extraction results');
    return res.json();
  },

  updateExtractionResult: async (rfpId: number, resultId: number, data: any) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/rfps/${rfpId}/extraction-results/${resultId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update extraction result');
    return res.json();
  },

  // Proposals
  createProposal: async (data: { client_name: string; title?: string; rfp_id?: number; extracted_data?: string }) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/proposals/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create proposal');
    return res.json();
  },

  listProposals: async (status?: string) => {
    const token = localStorage.getItem('access_token');
    const url = status ? `${API_URL}/api/proposals/?status_filter=${status}` : `${API_URL}/api/proposals/`;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to list proposals');
    return res.json();
  },

  getProposal: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/proposals/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to get proposal');
    return res.json();
  },

  updateProposal: async (id: number, data: any) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/proposals/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update proposal');
    return res.json();
  },

  deleteProposal: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/proposals/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to delete proposal');
    return res.json();
  },

  duplicateProposal: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/proposals/${id}/duplicate`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to duplicate proposal');
    return res.json();
  },

  // Generation
  generateProposal: async (proposalId: number, templateId?: number) => {
    const token = localStorage.getItem('access_token');
    const url = templateId
      ? `${API_URL}/api/proposals/${proposalId}/generate?template_id=${templateId}`
      : `${API_URL}/api/proposals/${proposalId}/generate`;

    const res = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to generate proposal');

    const blob = await res.blob();
    return blob;
  },

  generateProposalText: async (proposalId: number, templateId?: number) => {
    const token = localStorage.getItem('access_token');
    const url = templateId
      ? `${API_URL}/api/proposals/${proposalId}/generate-text?template_id=${templateId}`
      : `${API_URL}/api/proposals/${proposalId}/generate-text`;

    const res = await fetch(url, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to generate proposal text');
    return res.json();
  },

  // Templates
  createTemplate: async (data: { name: string; content?: string; is_default?: boolean }, file?: File) => {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('name', data.name);
    if (data.content) formData.append('content', data.content);
    if (data.is_default) formData.append('is_default', 'true');
    if (file) formData.append('file', file);

    const res = await fetch(`${API_URL}/api/templates/`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to create template');
    return res.json();
  },

  listTemplates: async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/templates/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to list templates');
    return res.json();
  },

  getTemplate: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/templates/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to get template');
    return res.json();
  },

  updateTemplate: async (id: number, data: any) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/templates/${id}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update template');
    return res.json();
  },

  deleteTemplate: async (id: number) => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/templates/${id}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('Failed to delete template');
    return res.json();
  },

  getDefaultTemplate: async () => {
    const token = localStorage.getItem('access_token');
    const res = await fetch(`${API_URL}/api/templates/default/`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) throw new Error('No default template');
    return res.json();
  },

  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },
};