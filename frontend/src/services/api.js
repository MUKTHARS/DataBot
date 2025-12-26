import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 second timeout for complex queries
});

// Request interceptor for adding auth tokens if needed
api.interceptors.request.use(
  (config) => {
    // You can add authentication tokens here if needed
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      // Server responded with error status
      console.error('API Error:', error.response.status, error.response.data);
      
      // Handle specific error codes
      switch (error.response.status) {
        case 401:
          // Unauthorized - redirect to login
          window.location.href = '/login';
          break;
        case 403:
          // Forbidden
          console.error('Access forbidden');
          break;
        case 404:
          // Not found
          console.error('Endpoint not found');
          break;
        case 500:
          // Server error
          console.error('Server error occurred');
          break;
        case 503:
          // Service unavailable
          console.error('Service unavailable - check backend');
          break;
        default:
          console.error('Unknown error occurred');
      }
    } else if (error.request) {
      // Request made but no response
      console.error('No response received. Check if backend is running.');
    } else {
      // Request setup error
      console.error('Request error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export const processChatQuery = async (query, sessionId = 'default') => {
  try {
    const response = await api.post('/chat', {
      query,
      session_id: sessionId,
      stream: false
    });
    
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
};

export const streamChatQuery = async (query, sessionId, onChunk, onComplete) => {
  try {
    const response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        session_id: sessionId,
        stream: true
      })
    });

    if (!response.ok) {
      throw new Error(`Stream request failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        if (onComplete) onComplete();
        break;
      }
      
      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.substring(6);
          if (data) {
            try {
              const parsed = JSON.parse(data);
              if (parsed.chunk && onChunk) {
                onChunk(parsed.chunk);
              }
              if (parsed.error) {
                throw new Error(parsed.error);
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream error:', error);
    throw error;
  }
};

export const getChatHistory = async (sessionId) => {
  try {
    const response = await api.get(`/history/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Failed to get chat history:', error);
    return { messages: [] };
  }
};

export const analyzeQuery = async (query) => {
  try {
    const response = await api.post('/analyze-query', { query });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
};

export const getDatabaseSchema = async () => {
  try {
    const response = await api.get('/schema');
    return response.data;
  } catch (error) {
    console.error('Failed to get schema:', error);
    return { tables: [], collections: [], relationships: [] };
  }
};

export const getAgentStatus = async () => {
  try {
    const response = await api.get('/status');
    return response.data;
  } catch (error) {
    console.error('Failed to get agent status:', error);
    return {
      agent_ready: false,
      database_connected: false,
      database_type: 'unknown',
      chatgpt_available: false
    };
  }
};

export const testDatabaseConnection = async (dbType, connectionUrl) => {
  try {
    const response = await api.post('/test-connection', {
      database_type: dbType,
      connection_url: connectionUrl
    });
    
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
};

export const switchDatabase = async (config) => {
  try {
    const response = await api.post('/switch-database', config);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || error.message);
  }
};

export const suggestQueries = async (context) => {
  try {
    const response = await api.post('/suggest-queries', { context });
    return response.data;
  } catch (error) {
    console.error('Failed to get suggestions:', error);
    return { suggestions: [] };
  }
};

export const getStats = async () => {
  try {
    // Note: This endpoint might need to be implemented in the backend
    const response = await api.get('/stats');
    return response.data;
  } catch (error) {
    console.error('Failed to get stats:', error);
    return null;
  }
};

// WebSocket connection for real-time chat
export const createWebSocket = (sessionId) => {
  const wsUrl = `ws://localhost:8000/ws/chat`;
  const ws = new WebSocket(wsUrl);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    // Send initial message with session ID
    ws.send(JSON.stringify({
      type: 'init',
      session_id: sessionId
    }));
  };
  
  return ws;
};

export default api;