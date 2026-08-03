import VendorShell from "../components/VendorShell";
import { useVendorAuth } from "../contexts/VendorAuthContext";

export default function VendorHomePage() {
  const { vendor, logout } = useVendorAuth();
  const isRecharge = vendor?.role === "recharge";

  return (
    <VendorShell vendor={vendor} onLogout={logout}>
      <div className="card">
        <h2>Aguardando cartão</h2>
        <p>
          {isRecharge
            ? "Toque um cartão para lançar uma recarga de saldo."
            : "Toque um cartão para cobrar uma compra."}
        </p>
      </div>
    </VendorShell>
  );
}
