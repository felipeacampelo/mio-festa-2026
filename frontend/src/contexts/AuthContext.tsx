import { createContext, useContext, useEffect, useState } from "react";
import { adminMe, loginAdmin, setAuthToken } from "../services/api";

type AuthContextValue = {
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("admin_token"));

  useEffect(() => {
    if (!token) return;
    setAuthToken(token);
    adminMe().catch(() => {
      localStorage.removeItem("admin_token");
      setToken(null);
      setAuthToken(null);
    });
  }, [token]);

  const login = async (username: string, password: string) => {
    const response = await loginAdmin(username, password);
    localStorage.setItem("admin_token", response.token);
    setAuthToken(response.token);
    setToken(response.token);
  };

  const logout = () => {
    localStorage.removeItem("admin_token");
    setAuthToken(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: Boolean(token), login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("AuthContext ausente");
  return context;
}
