import { useEffect, useState } from "react";
import AdminShell from "../components/AdminShell";
import {
  CardReconciliation,
  EventSettings,
  SellerOption,
  getAdminEvent,
  getAdminSellers,
  getAdminStats,
  getCardReconciliation,
} from "../services/api";

function IconOrders() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
      <rect x="9" y="3" width="6" height="4" rx="1"/>
      <line x1="9" y1="12" x2="15" y2="12"/><line x1="9" y1="16" x2="13" y2="16"/>
    </svg>
  );
}

function IconRevenue() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="12" y1="1" x2="12" y2="23"/>
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>
    </svg>
  );
}

function IconTickets() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2z"/>
    </svg>
  );
}

function IconCheckin() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
      <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  );
}

function IconWallet() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 12V7a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>
      <path d="M21 12h-4a2 2 0 0 0 0 4h4v-4Z"/>
    </svg>
  );
}

function IconSpend() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M6 9l6-6 6 6"/>
      <path d="M12 3v14"/>
      <path d="M5 21h14"/>
    </svg>
  );
}

function IconBalance() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9"/>
      <path d="M9 12h6"/>
    </svg>
  );
}

function formatCurrency(value: number | string) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function sumTotals(rows: Array<{ total: string }>) {
  return rows.reduce((acc, row) => acc + Number(row.total || 0), 0);
}

function RankList({
  rows,
  emptyMessage,
  renderName,
  renderValue,
  valueOf,
  keyOf,
}: {
  rows: any[];
  emptyMessage: string;
  renderName: (row: any) => React.ReactNode;
  renderValue: (row: any) => React.ReactNode;
  valueOf: (row: any) => number;
  keyOf: (row: any) => string;
}) {
  if (rows.length === 0) return <p className="rank-empty">{emptyMessage}</p>;
  const max = Math.max(...rows.map(valueOf), 0.01);
  return (
    <div className="rank-list">
      {rows.map((row, i) => (
        <div key={keyOf(row)} className="rank-row">
          <div className="rank-row-top">
            <span className="rank-badge">{i + 1}</span>
            <span className="rank-name">{renderName(row)}</span>
            <strong className="rank-value">{renderValue(row)}</strong>
          </div>
          <div className="rank-bar-track">
            <div className="rank-bar-fill" style={{ width: `${(valueOf(row) / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AdminDashboardPage() {
  const [event, setEvent] = useState<EventSettings | null>(null);
  const [reconciliation, setReconciliation] = useState<CardReconciliation | null>(null);
  const [sellers, setSellers] = useState<SellerOption[]>([]);
  const [sellerFilter, setSellerFilter] = useState("");
  const [stats, setStats] = useState({
    totalOrders: 0,
    paidOrders: 0,
    revenue: 0,
    totalTickets: 0,
    activeTickets: 0,
    usedTickets: 0,
  });
  const [error, setError] = useState(false);

  const load = () => {
    setError(false);
    Promise.all([getAdminEvent(), getAdminStats(), getCardReconciliation(), getAdminSellers()])
      .then(([eventData, statsData, reconciliationData, sellersData]) => {
        setEvent(eventData);
        setReconciliation(reconciliationData);
        setSellers(sellersData);
        setStats({
          totalOrders: statsData.total_orders,
          paidOrders: statsData.paid_orders,
          revenue: Number(statsData.revenue || 0),
          totalTickets: statsData.total_tickets,
          activeTickets: statsData.active_tickets,
          usedTickets: statsData.used_tickets,
        });
      })
      .catch(() => setError(true));
  };

  useEffect(() => { load(); }, []);

  const totalRecharged = reconciliation ? sumTotals(reconciliation.recharge_by_vendor) : 0;
  const totalSpent = reconciliation ? sumTotals(reconciliation.sold_by_vendor) : 0;

  const sellerOptions = sellers.map((s) => ({ id: String(s.id), name: s.display_name }));

  const selectedSellerTotal = (reconciliation?.sold_by_vendor || []).find(
    (row) => String(row.vendor_id ?? "sem-vendedor") === sellerFilter
  );

  const productsForSelectedSeller = (reconciliation?.sold_by_product || []).filter(
    (row) => String(row.vendor_id ?? "sem-vendedor") === sellerFilter
  );

  const statCards = [
    {
      label: "Pedidos",
      value: stats.totalOrders,
      sub: `${stats.paidOrders} pagos`,
      icon: <IconOrders />,
      accent: "var(--navy)",
    },
    {
      label: "Receita",
      value: formatCurrency(stats.revenue),
      sub: "pagamentos confirmados",
      icon: <IconRevenue />,
      accent: "var(--brand)",
    },
    {
      label: "Ingressos emitidos",
      value: stats.totalTickets,
      sub: `${stats.activeTickets} ativos`,
      icon: <IconTickets />,
      accent: "var(--navy)",
    },
    {
      label: "Check-ins",
      value: stats.usedTickets,
      sub: "entradas registradas",
      icon: <IconCheckin />,
      accent: "#059669",
    },
    {
      label: "Recarregado",
      value: formatCurrency(totalRecharged),
      sub: "em cartões, no total",
      icon: <IconWallet />,
      accent: "var(--navy)",
    },
    {
      label: "Gasto",
      value: formatCurrency(totalSpent),
      sub: "consumido nos cartões",
      icon: <IconSpend />,
      accent: "#B45309",
    },
    {
      label: "Saldo restante",
      value: reconciliation ? formatCurrency(reconciliation.outstanding_balance) : formatCurrency(0),
      sub: "ainda em cartões ativos/bloqueados",
      icon: <IconBalance />,
      accent: "#059669",
    },
  ];

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Visão geral</p>
          <h1>Dashboard</h1>
        </div>

        {error && (
          <div className="admin-load-error">
            Não foi possível carregar os dados.{" "}
            <button className="link-btn" onClick={load}>Tentar novamente</button>
          </div>
        )}

        <div className="dashboard-grid">
          {statCards.map((card) => (
            <article key={card.label} className="card dashboard-card">
              <div className="dashboard-card-icon" style={{ color: card.accent }}>
                {card.icon}
              </div>
              <div className="dashboard-card-text">
                <p className="dashboard-label">{card.label}</p>
                <strong className="dashboard-metric" style={{ color: card.accent }}>
                  {card.value}
                </strong>
                <span className="dashboard-sub">{card.sub}</span>
              </div>
            </article>
          ))}
        </div>

        {reconciliation && (
          <div className="dashboard-rank-grid">
            <article className="card">
              <div className="rank-card-header">
                <h2>Recarga por caixa</h2>
              </div>
              <RankList
                rows={reconciliation.recharge_by_vendor}
                emptyMessage="Nenhuma recarga registrada ainda."
                keyOf={(row) => String(row.vendor_id ?? "sem-caixa")}
                renderName={(row) => row.vendor__display_name || "Sem caixa"}
                renderValue={(row) => formatCurrency(row.total)}
                valueOf={(row) => Number(row.total || 0)}
              />
            </article>

            <article className="card">
              <div className="rank-card-header">
                <h2>Vendas por vendedor</h2>
                {sellerOptions.length > 0 && (
                  <select value={sellerFilter} onChange={(e) => setSellerFilter(e.target.value)}>
                    <option value="">Todos os vendedores</option>
                    {sellerOptions.map((v) => (
                      <option key={v.id} value={v.id}>{v.name}</option>
                    ))}
                  </select>
                )}
              </div>

              {!sellerFilter && (
                <RankList
                  rows={reconciliation.sold_by_vendor}
                  emptyMessage="Nenhuma venda registrada ainda."
                  keyOf={(row) => String(row.vendor_id ?? "sem-vendedor")}
                  renderName={(row) => row.vendor__display_name || "Sem vendedor"}
                  renderValue={(row) => formatCurrency(row.total)}
                  valueOf={(row) => Number(row.total || 0)}
                />
              )}

              {sellerFilter && (
                <>
                  <div className="rank-seller-total">
                    <span>Total vendido</span>
                    <strong>{formatCurrency(selectedSellerTotal?.total || 0)}</strong>
                  </div>
                  <RankList
                    rows={productsForSelectedSeller}
                    emptyMessage="Nenhum produto vendido por este vendedor ainda."
                    keyOf={(row) => row.product_name}
                    renderName={(row) => row.product_name}
                    renderValue={(row) => `${row.quantity}x · ${formatCurrency(row.total)}`}
                    valueOf={(row) => row.quantity}
                  />
                </>
              )}
            </article>
          </div>
        )}

        <div className="admin-grid" style={{ gridTemplateColumns: "1fr" }}>
          <article className="card">
            <h2>Evento atual</h2>
            <p><strong>Nome:</strong> {event?.name || "—"}</p>
            <p><strong>Data:</strong> {event?.event_date ? new Date(event.event_date).toLocaleString("pt-BR") : "—"}</p>
            <p><strong>Local:</strong> {event?.location || "—"}</p>
            <p><strong>Preço:</strong> {event?.price ? Number(event.price).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }) : "—"}</p>
            <p><strong>Status:</strong> {event?.sales_status || "—"}</p>
          </article>
        </div>
      </section>
    </AdminShell>
  );
}
