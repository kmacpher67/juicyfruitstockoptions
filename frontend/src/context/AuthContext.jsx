import React, { createContext, useState, useEffect, useContext } from 'react';
import api from '../api/axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Check for existing token on load
        const token = localStorage.getItem('token');
        if (token) {
            console.debug('[AuthContext] Found existing token, fetching user profile...');
            fetchUser();
        } else {
            console.debug('[AuthContext] No token found, skipping user fetch');
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        // Auto-logout when axios interceptor detects a 401 (expired token)
        const handleAuthLogout = () => {
            console.debug('[AuthContext] auth:logout event received — logging out');
            logout();
        };
        window.addEventListener('auth:logout', handleAuthLogout);
        return () => window.removeEventListener('auth:logout', handleAuthLogout);
    }, [user]);

    const fetchUser = async () => {
        try {
            console.debug('[AuthContext] Fetching /users/me...');
            const response = await api.get('/users/me');
            console.debug('[AuthContext] User fetched:', response.data?.username);
            setUser(response.data);
            return response.data;
        } catch (error) {
            console.error('[AuthContext] Failed to fetch user:', error?.response?.status, error?.message);
            logout();
            return null;
        } finally {
            setLoading(false);
        }
    };

    const login = async (username, password) => {
        console.debug('[AuthContext] Login attempt for:', username);
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/token', formData);
        const { access_token } = response.data;
        console.debug('[AuthContext] Token received, storing...');

        localStorage.setItem('token', access_token);

        // Fetch user profile — do NOT call logout() on failure here, 
        // because logout() would remove the token we just stored.
        try {
            console.debug('[AuthContext] Fetching user profile after login...');
            const profileRes = await api.get('/users/me');
            console.debug('[AuthContext] Login profile fetched:', profileRes.data?.username);
            setUser(profileRes.data);
            setLoading(false);
            return profileRes.data;
        } catch (profileError) {
            console.error('[AuthContext] Failed to fetch profile after login:', profileError?.response?.status, profileError?.message);
            // Clean up: remove the token since we can't verify the session
            localStorage.removeItem('token');
            setUser(null);
            setLoading(false);
            throw new Error('Login succeeded but profile fetch failed');
        }
    };

    const logout = () => {
        // Save current location for deep link hijack protection, if a user was logged in
        if (user?.username) {
            console.debug('[AuthContext] Saving redirect context for user:', user.username);
            localStorage.setItem('redirect_context', JSON.stringify({
                url: window.location.pathname + window.location.search,
                username: user.username
            }));
        }
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
