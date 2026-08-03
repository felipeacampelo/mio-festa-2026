import { Navigate, useLocation } from "react-router-dom";
import { useVendorAuth } from "../contexts/VendorAuthContext";

export function VendorPrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useVendorAuth();
  const location = useLocation();
  return isAuthenticated ? (
    <>{children}</>
  ) : (
    <Navigate to={`/caixa/login?next=${encodeURIComponent(location.pathname)}`} replace />
  );
}
