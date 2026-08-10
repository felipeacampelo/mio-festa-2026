import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
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
  const [statusCounts, setStatusCounts] = useState<CardReconciliation["status_counts"] | null>(null);
  const [search, setSearch] = useState("");
  const [hideReturned, setHideReturned] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busyUid, setBusyUid] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    Promise.all([getAdminCards(search, 1, 50, hideReturned), getCardReconciliation()])
      .then(([cardsResponse, reconciliationResponse]) => {
        setCards(cardsResponse.results);
        setStatusCounts(reconciliationResponse.status_counts);
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

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Cartões NFC</p>
          <h1>Cartões</h1>
          {statusCounts && (
            <p className="muted">
              {statusCounts.active || 0} ativos, {statusCounts.blocked || 0} bloqueados, {statusCounts.returned || 0} devolvidos.{" "}
              Resumo financeiro e vendas ficam no <Link to="/admin">Dashboard</Link>.
            </p>
          )}
        </div>

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
