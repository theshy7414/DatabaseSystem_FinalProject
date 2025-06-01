export const CHAT_MODE: 'mock' | 'api' = 'mock';

export const API_CONFIG = {
  BASE_URL: 'http://localhost:3001', // Change this to your API URL
  ENDPOINTS: {
    CHAT: '/api/chat',
  }
};

// Timeouts for mock mode (in ms)
export const MOCK_DELAYS = {
  BOT_RESPONSE: 1000,
}; 