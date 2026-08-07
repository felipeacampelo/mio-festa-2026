import { Link } from "react-router-dom";
import VendorShell from "../components/VendorShell";
import { useVendorAuth } from "../contexts/VendorAuthContext";

const MESSAGES: Record<string, string> = {
  recharge: "Toque um cartão para lançar uma recarga de saldo.",
  checkin: "Toque um cartão para vincular ao participante.",
  seller: "Toque um cartão para cobrar uma compra.",
};

export default function VendorHomePage() {
  const { vendor, logout } = useVendorAuth();

  return (
    <VendorShell vendor={vendor} onLogout={logout}>
      <div className="card">
        <h2>Aguardando cartão</h2>
        <p>{(vendor && MESSAGES[vendor.role]) || "Toque um cartão para começar."}</p>
        {vendor?.role === "checkin" && (
          <Link to="/caixa/checkin" className="button button-primary" style={{ marginTop: "1rem", display: "inline-block" }}>
            Ler QR code (check-in)
          </Link>
        )}
      </div>
    </VendorShell>
  );
}
