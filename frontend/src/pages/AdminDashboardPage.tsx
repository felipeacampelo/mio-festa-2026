import { useEffect, useMemo, useState } from "react";
import AdminShell from "../components/AdminShell";
import { EventSettings, getAdminEvent, getAdminOrders, getAdminTickets } from "../services/api";

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

export default function AdminDashboardPage() {
  const [event, setEvent] = useState<EventSettings | null>(null);
  const [orders, setOrders] = useState<any[]>([]);
  const [tickets, setTickets] = useState<any[]>([]);

  useEffect(() => {
    Promise.all([getAdminEvent(), getAdminOrders(), getAdminTickets()]).then(
      ([eventData, ordersData, ticketsData]) => {
        setEvent(eventData);
        setOrders(ordersData.results);
        setTickets(ticketsData.results);
      }
    );
  }, []);

  const stats = useMemo(() => {
    const paidOrders = orders.filter((o) => o.status === "paid");
    return {
      totalOrders: orders.length,
      paidOrders: paidOrders.length,
      revenue: paidOrders.reduce((sum, o) => sum + Number(o.total_amount || 0), 0),
      totalTickets: tickets.length,
      activeTickets: tickets.filter((t) => t.status === "active").length,
      usedTickets: tickets.filter((t) => t.status === "used").length,
    };
  }, [orders, tickets]);

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
      value: stats.revenue.toLocaleString("pt-BR", { style: "currency", currency: "BRL" }),
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
  ];

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Visão geral</p>
          <h1>Dashboard</h1>
        </div>

        <div className="dashboard-grid">
          {statCards.map((card) => (
            <article key={card.label} className="card dashboard-card">
              <div className="dashboard-card-icon" style={{ color: card.accent }}>
                {card.icon}
              </div>
              <p className="dashboard-label">{card.label}</p>
              <strong className="dashboard-metric" style={{ color: card.accent }}>
                {card.value}
              </strong>
              <span className="dashboard-sub">{card.sub}</span>
            </article>
          ))}
        </div>

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
