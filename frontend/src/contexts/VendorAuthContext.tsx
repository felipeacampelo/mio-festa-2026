import { createContext, useContext, useEffect, useState } from "react";
import { Vendor, setVendorAuthToken, setVendorUnauthorizedHandler, vendorLogin, vendorMe } from "../services/api";

type VendorAuthContextValue = {
  token: string | null;
  vendor: Vendor | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<Vendor>;
  logout: () => void;
};

const VendorAuthContext = createContext<VendorAuthContextValue | null>(null);

export function VendorAuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    const stored = localStorage.getItem("vendor_token");
    if (stored) setVendorAuthToken(stored);
    return stored;
  });
  const [vendor, setVendor] = useState<Vendor | null>(null);

  const clearSession = () => {
    localStorage.removeItem("vendor_token");
    setVendorAuthToken(null);
    setToken(null);
    setVendor(null);
  };

  useEffect(() => {
    // Qualquer chamada a vendorApi (não só a validação no carregamento)
    // que responda 401/403 - token expirado, vendedor desativado no meio
    // do turno - dispara isso e derruba a sessão, em vez de deixar a
    // pessoa presa numa tela mostrando "erro de comunicação" genérico.
    setVendorUnauthorizedHandler(clearSession);
    return () => setVendorUnauthorizedHandler(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!token) return;
    setVendorAuthToken(token);
    vendorMe()
      .then(setVendor)
      .catch(() => {
        // 401/403 já são tratados globalmente pelo handler acima.
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const login = async (username: string, password: string) => {
    const response = await vendorLogin(username, password);
    localStorage.setItem("vendor_token", response.token);
    setVendorAuthToken(response.token);
    setToken(response.token);
    setVendor(response.vendor);
    return response.vendor;
  };

  return (
    <VendorAuthContext.Provider value={{ token, vendor, isAuthenticated: Boolean(token), login, logout: clearSession }}>
      {children}
    </VendorAuthContext.Provider>
  );
}

export function useVendorAuth() {
  const context = useContext(VendorAuthContext);
  if (!context) throw new Error("VendorAuthContext ausente");
  return context;
}
