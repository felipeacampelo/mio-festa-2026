import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import { VendorAuthProvider } from "./contexts/VendorAuthContext";
import AdminCardsPage from "./pages/AdminCardsPage";
import AdminProductsPage from "./pages/AdminProductsPage";
import AdminVendorsPage from "./pages/AdminVendorsPage";
import AdminDashboardPage from "./pages/AdminDashboardPage";
import AdminEventPage from "./pages/AdminEventPage";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminOrdersPage from "./pages/AdminOrdersPage";
import CheckoutPage from "./pages/CheckoutPage";
import HomePage from "./pages/HomePage";
import OrderLookupPage from "./pages/OrderLookupPage";
import OrderPage from "./pages/OrderPage";
import VendorCardPage from "./pages/VendorCardPage";
import VendorCheckinPage from "./pages/VendorCheckinPage";
import VendorHomePage from "./pages/VendorHomePage";
import VendorLoginPage from "./pages/VendorLoginPage";
import { PrivateRoute } from "./components/PrivateRoute";
import { VendorPrivateRoute } from "./components/VendorPrivateRoute";

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
          path="/admin/evento"
          element={
            <PrivateRoute>
              <AdminEventPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin/cartoes"
          element={
            <PrivateRoute>
              <AdminCardsPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin/produtos"
          element={
            <PrivateRoute>
              <AdminProductsPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/admin/acesso-vendedor"
          element={
            <PrivateRoute>
              <AdminVendorsPage />
            </PrivateRoute>
          }
        />
        <Route
          path="/caixa/login"
          element={
            <VendorAuthProvider>
              <VendorLoginPage />
            </VendorAuthProvider>
          }
        />
        <Route
          path="/caixa"
          element={
            <VendorAuthProvider>
              <VendorPrivateRoute>
                <VendorHomePage />
              </VendorPrivateRoute>
            </VendorAuthProvider>
          }
        />
        <Route
          path="/caixa/checkin"
          element={
            <VendorAuthProvider>
              <VendorPrivateRoute>
                <VendorCheckinPage />
              </VendorPrivateRoute>
            </VendorAuthProvider>
          }
        />
        <Route
          path="/caixa/:uid"
          element={
            <VendorAuthProvider>
              <VendorPrivateRoute>
                <VendorCardPage />
              </VendorPrivateRoute>
            </VendorAuthProvider>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
