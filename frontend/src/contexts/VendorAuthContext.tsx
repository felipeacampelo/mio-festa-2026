import { createContext, useContext, useEffect, useState } from "react";
import { Vendor, setAuthToken, vendorLogin, vendorMe } from "../services/api";

type VendorAuthContextValue = {
  token: string | null;
  vendor: Vendor | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const VendorAuthContext = createContext<VendorAuthContextValue | null>(null);

export function VendorAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const stored = localStorage.getItem("vendor_token");
    if (stored) setAuthToken(stored);
    return stored;
  });
  const [vendor, setVendor] = useState<Vendor | null>(null);

  useEffect(() => {
    if (!token) return;
    setAuthToken(token);
    vendorMe()
      .then(setVendor)
      .catch((err) => {
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          localStorage.removeItem("vendor_token");
          setToken(null);
          setVendor(null);
          setAuthToken(null);
        }
      });
  }, [token]);

  const login = async (username: string, password: string) => {
    const response = await vendorLogin(username, password);
    localStorage.setItem("vendor_token", response.token);
    setAuthToken(response.token);
    setToken(response.token);
    setVendor(response.vendor);
  };

  const logout = () => {
    localStorage.removeItem("vendor_token");
    setAuthToken(null);
    setToken(null);
    setVendor(null);
  };

  return (
    <VendorAuthContext.Provider value={{ token, vendor, isAuthenticated: Boolean(token), login, logout }}>
      {children}
    </VendorAuthContext.Provider>
  );
}

export function useVendorAuth() {
  const context = useContext(VendorAuthContext);
  if (!context) throw new Error("VendorAuthContext ausente");
  return context;
}
