import axios from 'axios';
import { getAuthHeader } from './authService';

const API_URL = 'http://localhost:8000/feast-mode';

const getFeastStatus = async (date) => {
    try {
        const response = await axios.get(`${API_URL}/status`, {
            params: { current_date: date },
            headers: getAuthHeader()
        });
        return response.data;
    } catch (error) {
        console.error("Error fetching feast status:", error);
        return null;
    }
};

const proposeFeast = async (eventDetails) => {
    const response = await axios.post(`${API_URL}/propose`, eventDetails, {
        headers: getAuthHeader()
    });
    return response.data;
};

const preActivateCheck = async (checkData) => {
    const response = await axios.post(`${API_URL}/pre-activate-check`, checkData, {
        headers: getAuthHeader()
    });
    return response.data;
};

const activateFeast = async (activationData) => {
    const response = await axios.post(`${API_URL}/activate`, activationData, {
        headers: getAuthHeader()
    });
    return response.data;
};

const updateFeast = async (updateData) => {
    const response = await axios.patch(`${API_URL}/update`, updateData, {
        headers: getAuthHeader()
    });
    return response.data;
};

const cancelFeast = async () => {
    const response = await axios.post(`${API_URL}/cancel`, {}, {
        headers: getAuthHeader()
    });
    return response.data;
};

const deactivatePreview = async () => {
    const response = await axios.post(`${API_URL}/deactivate-preview`, {}, {
        headers: getAuthHeader()
    });
    return response.data;
};

const getOverrides = async (date) => {
    try {
        const response = await axios.get(`${API_URL}/overrides`, {
            params: { target_date: date },
            headers: getAuthHeader()
        });
        return response.data;
    } catch (error) {
        console.error("Error fetching overrides:", error);
        return [];
    }
};

export default {
    getFeastStatus,
    proposeFeast,
    preActivateCheck,
    activateFeast,
    updateFeast,
    cancelFeast,
    deactivatePreview,
    getOverrides
};
