import api from './axios';

export const chatWithCoach = async (message, sessionId = "default_session") => {
  try {
    const response = await api.post('/chat', {
      message,
      session_id: sessionId
    });
    return response.data;
  } catch (error) {
    console.error('Chat API Error:', error);
    throw error;
  }
};

/**
 * Fetch past chat history for a session.
 */
export const getChatHistory = async (sessionId = "default_session") => {
    try {
        const response = await api.get('/chat/history', {
            params: { session_id: sessionId }
        });
        return response.data;
    } catch (error) {
        console.error('Fetch History Error:', error);
        throw error;
    }
};

/**
 * Fetch all chat sessions.
 */
export const getChatSessions = async () => {
    try {
        const response = await api.get('/chat/sessions');
        return response.data;
    } catch (error) {
        console.error('Fetch Sessions Error:', error);
        throw error;
    }
};

/**
 * Delete a chat session and all its history.
 */
export const deleteSession = async (sessionId) => {
    try {
        const response = await api.delete(`/chat/sessions/${sessionId}`);
        return response.data;
    } catch (error) {
        console.error('Delete Session Error:', error);
        throw error;
    }
};

/**
 * Rename a chat session title.
 */
export const renameSession = async (sessionId, newTitle) => {
    try {
        const response = await api.patch(`/chat/sessions/${sessionId}`, {
            title: newTitle
        });
        return response.data;
    } catch (error) {
        console.error('Rename Session Error:', error);
        throw error;
    }
};
