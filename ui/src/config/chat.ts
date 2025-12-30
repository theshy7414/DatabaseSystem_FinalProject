export const CHAT_MODE: 'mock' | 'api' = 'api';

// Demo mode configuration
export const DEMO_MODE = true;

export const API_CONFIG = {
  BASE_URL: 'http://localhost:8000', // Updated to match server.py port
  ENDPOINTS: {
    SEARCH: '/api/search',
  }
};

// Timeouts for mock mode (in ms)
export const MOCK_DELAYS = {
  BOT_RESPONSE: 1000,
}; 