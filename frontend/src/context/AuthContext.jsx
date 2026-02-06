import React, { createContext, useState, useContext, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'react-toastify';
import { jwtDecode } from 'jwt-decode';
import api from '../api/axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const isTokenExpired = (token) => {
    if (!token) return true;
    try {
      const decoded = jwtDecode(token);
      const currentTime = Date.now() / 1000;
      return decoded.exp < currentTime;
    } catch (error) {
      return true;
    }
  };

  const logout = async (expired = false) => {
    // Prevent duplicate logout actions if already cleared
    if (!localStorage.getItem('diet_planner_token')) {
        // If expired=true was passed but token is already gone, 
        // we might have already logged out. 
        // We can optionally show the toast if we want to be sure the user sees it,
        // but to prevent duplicates, we'll rely on toastId.
    }

    // Clear local state immediately
    setUser(null);
    localStorage.removeItem('diet_planner_user'); 
    localStorage.removeItem('diet_planner_token');
    localStorage.removeItem('dp_token'); // Clear legacy if exists
    
    if (expired) {
        // use toastId to prevent duplicates
        toast.error("Your session is expired", {
            toastId: 'session-expired'
        });
        navigate('/');
    }

    try {
      await api.post('/login/logout');
    } catch (error) {
      console.error("Backend logout failed", error);
    }
  };

  const verifySession = async () => {
    try {
        // console.log("Verifying session with backend...");
        await api.get('/users/me');
        // console.log("Session valid.");
    } catch (error) {
        console.warn("Session verification failed:", error.response?.status);
        if (error.response?.status === 401 || error.response?.status === 403) {
             console.log("Auth error detected in verifySession, forcing logout.");
             // Use alert for immediate visibility during debugging
             // alert("Session expired or invalid (Cookie missing). Logging out.");
             logout(true);
        }
    }
  };

  const checkSession = async () => {
    const token = localStorage.getItem('diet_planner_token');
    if (token) {
        if (isTokenExpired(token)) {
            console.log("Token expired locally (JWT check)");
            logout(true);
        } else {
            await verifySession();
        }
    }
  };

  useEffect(() => {
    const storedUser = localStorage.getItem('diet_planner_user');
    const token = localStorage.getItem('diet_planner_token');

    if (storedUser && token) {
        if (isTokenExpired(token)) {
            console.log("Initial load: Token expired locally");
            logout(true);
        } else {
            setUser(JSON.parse(storedUser));
            verifySession();
        }
    }
    setLoading(false);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const handleAuthLogout = () => logout(true);
    window.addEventListener('auth:logout', handleAuthLogout);

    const events = ['mousedown', 'keydown', 'touchstart', 'scroll'];
    const handleInteraction = () => {
        const now = Date.now();
        // Throttle check to 30s
        if (!handleInteraction.lastRun || now - handleInteraction.lastRun > 30000) {
            checkSession();
            handleInteraction.lastRun = now;
        }
    };

    events.forEach(event => window.addEventListener(event, handleInteraction));

    return () => {
        window.removeEventListener('auth:logout', handleAuthLogout);
        events.forEach(event => window.removeEventListener(event, handleInteraction));
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const login = (userData, token) => {
    setUser(userData);
    localStorage.setItem('diet_planner_user', JSON.stringify(userData));
    if (token) {
        localStorage.setItem('diet_planner_token', token);
    }
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

// Change to named function for better HMR support
export function useAuth() {
  return useContext(AuthContext);
}
