import type { Message } from "@/types/chat";
import { API_CONFIG } from "@/config/chat";

export const sendChatMessage = async (message: Message): Promise<Message> => {
  try {
    console.log(message);
    const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.CHAT}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(message),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return {
      ...data,
      timestamp: new Date(data.timestamp)
    };
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
}; 