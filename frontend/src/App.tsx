import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import AdminCheckinPage from "./pages/AdminCheckinPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminEventPage from "./pages/AdminEventPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminOrdersPage from "./pages/AdminOrdersPage";
import CheckoutPage from "./pages/CheckoutPage";
import HomePage from "./pages/HomePage";
import OrderLookupPage from "./pages/OrderLookupPage";
import OrderPage from "./pages/OrderPage";
import { PrivateRoute } from "./components/PrivateRoute";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/pedido" element={<OrderLookupPage />} />
        <Route path="/pedido/:publicId" element={<OrderPage />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />
        <Route
          path="/admin"
          element={
            <PrivateRoute>
              <AdminDashboardPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin/pedidos"
          element={
            <PrivateRoute>
              <AdminOrdersPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin/checkin"
          element={
            <PrivateRoute>
              <AdminCheckinPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin/evento"
          element={
            <PrivateRoute>
              <AdminEventPage />
            </PrivateRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
