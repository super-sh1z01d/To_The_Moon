import React, { createContext, useState, useEffect, ReactNode } from 'react';
import { User } from '@/types/user';

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isLoading: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check for token in URL fragment (from OAuth callback)
    const hash = window.location.hash.substring(1); // Remove the '#'
    const params = new URLSearchParams(hash);
    const tokenFromHash = params.get('token');

    if (tokenFromHash) {
      // Save token and remove from URL
      localStorage.setItem('authToken', tokenFromHash);
      setToken(tokenFromHash);
      // Clean URL hash
      window.history.replaceState({}, document.title, window.location.pathname);
    } else {
      // Check localStorage
      const storedToken = localStorage.getItem('authToken');
      if (storedToken) {
        setToken(storedToken);
      }
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    if (token) {
      // Fetch user profile when token is available
      fetch('/auth/users/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      })
        .then(res => res.ok ? res.json() : Promise.reject(res))
        .then(data => setUser(data))
        .catch(() => {
          // Token is invalid, log out
          logout();
        });
    } else {
      setUser(null);
    }
  }, [token]);

  const login = (newToken: string) => {
    localStorage.setItem('authToken', newToken);
    setToken(newToken);
  };

  const logout = () => {
    localStorage.removeItem('authToken');
    setToken(null);
    setUser(null);
  };

  const value = {
    isAuthenticated: !!token,
    user,
    token,
    login,
    logout,
    isLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
