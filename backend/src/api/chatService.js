import apiClient from './client';

export const chatService = {
  // Get authorized chat contacts with unread counts
  getContacts: async () => {
    const response = await apiClient.get('/api/v1/chat/contacts');
    return response.data;
  },

  // Get full conversation history with another user
  getConversation: async (otherUserId) => {
    const response = await apiClient.get(`/api/v1/chat/conversation/${otherUserId}`);
    return response.data;
  },

  // Send a new chat message
  sendMessage: async (recipientId, message) => {
    const response = await apiClient.post('/api/v1/chat/send', {
      recipient_id: recipientId,
      message,
    });
    return response.data;
  },

  // Mark conversation messages as read
  markAsRead: async (otherUserId) => {
    const response = await apiClient.post(`/api/v1/chat/read/${otherUserId}`);
    return response.data;
  },

  // Soft-delete a specific chat message
  deleteMessage: async (messageId) => {
    const response = await apiClient.delete(`/api/v1/chat/messages/${messageId}`);
    return response.data;
  },

  // Delete/clear entire conversation for current user
  deleteConversation: async (otherUserId) => {
    const response = await apiClient.delete(`/api/v1/chat/conversation/${otherUserId}`);
    return response.data;
  },
};

export default chatService;

