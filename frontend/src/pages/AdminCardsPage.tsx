import { useEffect, useState } from "react";
import AdminShell from "../components/AdminShell";
import {
  AdminCard,
  CardReconciliation,
  blockCard,
  getAdminCards,
  getCardReconciliation,
  returnCard,
  unblockCard,
} from "../services/api";

function formatCurrency(value: string | number) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}

const statusLabel: Record<string, string> = { active: "Ativo", blocked: "Bloqueado", returned: "Devolvido" };

function StatusBadge({ status }: { status: string }) {
  let cls = "status-badge";
  if (status === "active") cls += " paid";
  else if (status === "blocked") cls += " failed";
  else cls += " used";
  return <span className={cls}>{statusLabel[status] || status}</span>;
}

export default function AdminCardsPage() {
  const [cards, setCards] = useState<AdminCard[]>([]);
  const [reconciliation, setReconciliation] = useState<CardReconciliation | null>(null);
  const [search, setSearch] = useState("");
  const [hideReturned, setHideReturned] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyUid, setBusyUid] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([getAdminCards(search, 1, 50, hideReturned), getCardReconciliation()])
      .then(([cardsResponse, reconciliationResponse]) => {
        setCards(cardsResponse.results);
        setReconciliation(reconciliationResponse);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, hideReturned]);

  const handleAction = async (action: (uid: string) => Promise<AdminCard>, uid: string) => {
    setBusyUid(uid);
    try {
      await action(uid);
      load();
    } finally {
      setBusyUid(null);
    }
  };

  const sumTotals = (rows: Array<{ total: string }>) =>
    rows.reduce((acc, row) => acc + Number(row.total || 0), 0);

  const totalRecharged = reconciliation ? sumTotals(reconciliation.recharge_by_vendor) : 0;
  const totalSpent = reconciliation ? sumTotals(reconciliation.sold_by_vendor) : 0;

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Cartões NFC</p>
          <h1>Cartões</h1>
        </div>

        {reconciliation && (
          <div className="admin-grid" style={{ marginBottom: "1.5rem" }}>
            <div className="card">
              <h2>Resumo financeiro</h2>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span>Total recarregado</span>
                  <strong>{formatCurrency(totalRecharged)}</strong>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                  <span>Total gasto</span>
                  <strong>{formatCurrency(totalSpent)}</strong>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "baseline",
                    borderTop: "1px solid var(--border)",
                    paddingTop: "0.5rem",
                    marginTop: "0.25rem",
                  }}
                >
                  <span>Saldo restante em cartões</span>
                  <strong style={{ fontSize: "1.3rem" }}>{formatCurrency(reconciliation.outstanding_balance)}</strong>
                </div>
              </div>
              <p style={{ fontSize: "0.85rem", opacity: 0.75, marginTop: "0.75rem" }}>
                {reconciliation.status_counts.active || 0} ativos, {reconciliation.status_counts.blocked || 0} bloqueados,{" "}
                {reconciliation.status_counts.returned || 0} devolvidos
              </p>
              <p style={{ fontSize: "0.78rem", opacity: 0.65, marginTop: "0.4rem" }}>
                O saldo restante também inclui o valor pré-carregado de ingressos antecipados, não só recargas feitas no caixa.
              </p>
            </div>
            <div className="card">
              <h2>Recarga por caixa</h2>
              {reconciliation.recharge_by_vendor.length === 0 && <p>Nenhuma recarga registrada ainda.</p>}
              {reconciliation.recharge_by_vendor.map((row) => (
                <div key={row.vendor_id ?? "sem-caixa"} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{row.vendor__display_name || "Sem caixa"}</span>
                  <strong>{formatCurrency(row.total)}</strong>
                </div>
              ))}
            </div>
            <div className="card">
              <h2>Vendas por vendedor</h2>
              {reconciliation.sold_by_vendor.length === 0 && <p>Nenhuma venda registrada ainda.</p>}
              {reconciliation.sold_by_vendor.map((row) => (
                <div key={row.vendor_id ?? "sem-vendedor"} style={{ display: "flex", justifyContent: "space-between" }}>
                  <span>{row.vendor__display_name || "Sem vendedor"}</span>
                  <strong>{formatCurrency(row.total)}</strong>
                </div>
              ))}
            </div>
            <div className="card">
              <h2>Vendas por produto</h2>
              {reconciliation.sold_by_product.length === 0 && <p>Nenhuma venda registrada ainda.</p>}
              {reconciliation.sold_by_product.map((row) => (
                <div
                  key={row.product_name}
                  style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem" }}
                >
                  <span>{row.product_name}</span>
                  <span style={{ display: "flex", gap: "0.75rem" }}>
                    <span style={{ opacity: 0.7 }}>{row.quantity}x</span>
                    <strong>{formatCurrency(row.total)}</strong>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <div className="field" style={{ maxWidth: "320px", marginBottom: 0 }}>
            <input
              type="text"
              placeholder="Buscar por UID, nome ou CPF…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={hideReturned}
              onChange={(e) => setHideReturned(e.target.checked)}
            />
            Ocultar devolvidos
          </label>
        </div>

        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>UID</th>
                <th>Participante</th>
                <th>Status</th>
                <th>Saldo</th>
                <th>Vinculado em</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={6}>Carregando…</td></tr>
              )}
              {!loading && cards.length === 0 && (
                <tr><td colSpan={6}>Nenhum cartão encontrado.</td></tr>
              )}
              {!loading && cards.map((c) => (
                <tr key={c.id}>
                  <td>{c.uid}</td>
                  <td>{c.participant_name || "-"}</td>
                  <td><StatusBadge status={c.status} /></td>
                  <td>{formatCurrency(c.balance)}</td>
                  <td>{formatDate(c.linked_at)}</td>
                  <td style={{ display: "flex", gap: "0.5rem" }}>
                    {c.status === "active" && (
                      <button
                        className="button button-secondary"
                        disabled={busyUid === c.uid}
                        onClick={() => handleAction(blockCard, c.uid)}
                      >
                        Bloquear
                      </button>
                    )}
                    {c.status === "blocked" && (
                      <button
                        className="button button-secondary"
                        disabled={busyUid === c.uid}
                        onClick={() => handleAction(unblockCard, c.uid)}
                      >
                        Desbloquear
                      </button>
                    )}
                    {c.status !== "returned" && (
                      <button
                        className="button button-secondary"
                        disabled={busyUid === c.uid}
                        onClick={() => handleAction(returnCard, c.uid)}
                      >
                        Devolver
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AdminShell>
  );
}
