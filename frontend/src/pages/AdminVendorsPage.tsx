import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import AdminShell from "../components/AdminShell";
import { Vendor, getAdminVendors, impersonateVendor } from "../services/api";

const ROLE_LABELS: Record<Vendor["role"], string> = {
  seller: "Vendedor",
  recharge: "Caixa de recarga",
  checkin: "Check-in",
};

const ROLE_HOME: Record<Vendor["role"], string> = {
  seller: "/caixa",
  recharge: "/caixa",
  checkin: "/caixa/checkin",
};

export default function AdminVendorsPage() {
  const navigate = useNavigate();
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  useEffect(() => {
    getAdminVendors()
      .then(setVendors)
      .catch(() => setError("Não foi possível carregar os vendedores."))
      .finally(() => setLoading(false));
  }, []);

  const enterAs = async (vendor: Vendor) => {
    setBusyId(vendor.id);
    setError("");
    try {
      const { token } = await impersonateVendor(vendor.id);
      localStorage.setItem("vendor_token", token);
      navigate(ROLE_HOME[vendor.role]);
      // Recarrega pra o VendorAuthProvider reler o token novo do localStorage.
      window.location.reload();
    } catch {
      setError("Não foi possível entrar como este vendedor.");
      setBusyId(null);
    }
  };

  const grouped = (["seller", "recharge", "checkin"] as const).map((role) => ({
    role,
    items: vendors.filter((v) => v.role === role),
  }));

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Cartões NFC</p>
          <h1>Acessar como vendedor</h1>
          <p>Entre direto num vendedor, caixa de recarga ou check-in já cadastrado, sem precisar da senha dele.</p>
        </div>

        {error && <div className="error-box" role="alert" style={{ marginBottom: "1rem" }}>{error}</div>}
        {loading && <p>Carregando…</p>}

        {!loading && grouped.map(({ role, items }) => (
          <div key={role} className="card" style={{ marginBottom: "1.5rem" }}>
            <h2>{ROLE_LABELS[role]}</h2>
            {items.length === 0 && <p>Nenhum vendedor cadastrado com este papel.</p>}
            {items.length > 0 && (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Nome</th>
                      <th>Status</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map((v) => (
                      <tr key={v.id}>
                        <td>{v.display_name}</td>
                        <td>
                          <span className={`status-badge ${v.is_active ? "paid" : "used"}`}>
                            {v.is_active ? "Ativo" : "Inativo"}
                          </span>
                        </td>
                        <td>
                          <button
                            className="button button-primary"
                            disabled={!v.is_active || busyId === v.id}
                            onClick={() => enterAs(v)}
                          >
                            {busyId === v.id ? "Entrando…" : "Entrar"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        ))}
      </section>
    </AdminShell>
  );
}
