import { useEffect, useRef, useState } from "react";
import AdminShell from "../components/AdminShell";
import { editTicket, getAdminOrders, getAdminTickets, resendTickets, syncOrderPayment, transferTicket } from "../services/api";

function SpinnerIcon() {
  return (
    <svg className="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" width="14" height="14" aria-hidden="true">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

const statusLabel: Record<string, string> = {
  pending: "Aguardando pagamento",
  paid: "Pago",
  confirmed: "Pago",
  expired: "Expirado",
  approved: "Aprovado",
  active: "Ativo",
  used: "Utilizado",
  failed: "Falhou",
};

function StatusBadge({ status }: { status: string }) {
  const norm = status?.toLowerCase() || "";
  let cls = "status-badge";
  if (["paid", "approved", "active"].includes(norm)) cls += " paid";
  else if (norm === "pending") cls += " pending";
  else if (["failed", "expired"].includes(norm)) cls += " failed";
  else if (norm === "used") cls += " used";
  return <span className={cls}>{statusLabel[norm] || status}</span>;
}

type ModalMode = "edit" | "transfer";
interface TicketModal { mode: ModalMode; ticket: any }

export default function AdminOrdersPage() {
  const [search, setSearch] = useState("");
  const [orders, setOrders] = useState<any[]>([]);
  const [tickets, setTickets] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState<Record<number, boolean>>({});
  const [resent, setResent] = useState<Record<number, boolean>>({});
  const [syncing, setSyncing] = useState<Record<number, boolean>>({});

  const [ticketModal, setTicketModal] = useState<TicketModal | null>(null);
  const [modalName, setModalName] = useState("");
  const [modalEmail, setModalEmail] = useState("");
  const [modalLoading, setModalLoading] = useState(false);
  const modalNameRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    setLoading(true);
    try {
      const [ordersData, ticketsData] = await Promise.all([
        getAdminOrders(search),
        getAdminTickets(search),
      ]);
      setOrders(ordersData);
      setTickets(ticketsData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  useEffect(() => {
    if (ticketModal) {
      setTimeout(() => modalNameRef.current?.focus(), 50);
    }
  }, [ticketModal]);

  const openModal = (mode: ModalMode, ticket: any) => {
    setTicketModal({ mode, ticket });
    setModalName(ticket.participant_name || "");
    setModalEmail(ticket.participant_email || "");
  };

  const confirmModal = async () => {
    if (!ticketModal) return;
    setModalLoading(true);
    try {
      if (ticketModal.mode === "edit") {
        await editTicket(ticketModal.ticket.id, {
          participant_name: modalName,
          participant_email: modalEmail,
        });
      } else {
        await transferTicket(ticketModal.ticket.id, {
          participant_name: modalName,
          participant_email: modalEmail,
        });
      }
      setTicketModal(null);
      load();
    } finally {
      setModalLoading(false);
    }
  };

  const handleResend = async (orderId: number) => {
    setResending((r) => ({ ...r, [orderId]: true }));
    try {
      await resendTickets(orderId);
      setResent((r) => ({ ...r, [orderId]: true }));
      setTimeout(() => setResent((r) => ({ ...r, [orderId]: false })), 3000);
    } finally {
      setResending((r) => ({ ...r, [orderId]: false }));
    }
  };

  const handleSyncPayment = async (orderId: number) => {
    setSyncing((current) => ({ ...current, [orderId]: true }));
    try {
      await syncOrderPayment(orderId);
      await load();
    } finally {
      setSyncing((current) => ({ ...current, [orderId]: false }));
    }
  };

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header inline-between">
          <div>
            <p className="admin-kicker">Operacional</p>
            <h1>Pedidos e ingressos</h1>
          </div>
          <div className="inline-actions">
            <div className="field" style={{ margin: 0 }}>
              <label htmlFor="orders-search" className="sr-only">Buscar pedidos e ingressos</label>
              <input
                id="orders-search"
                placeholder="Buscar por nome ou e-mail"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") load(); }}
                style={{ minWidth: 220 }}
              />
            </div>
            <button className="button button-secondary" onClick={load} disabled={loading}>
              {loading ? <SpinnerIcon /> : "Buscar"}
            </button>
          </div>
        </div>

        <div className="admin-grid">

          {/* Pedidos */}
          <div>
            <h2>Pedidos</h2>
            {loading && orders.length === 0 && (
              <div className="empty-state">Carregando…</div>
            )}
            {!loading && orders.length === 0 && (
              <div className="empty-state">Nenhum pedido encontrado.</div>
            )}
            {orders.map((order) => (
              <article key={order.id} className="card order-card">
                <div className="order-card-header">
                  <div>
                    <p className="order-card-name">{order.buyer_name}</p>
                    <p className="order-card-email">{order.buyer_email}</p>
                  </div>
                  <StatusBadge status={order.status} />
                </div>
                <p className="order-card-id">Pedido #{order.public_id}</p>
                <div className="order-meta-list">
                  <div className="order-meta-item">
                    <div className="order-meta-label">Cobrança</div>
                    <div className="order-meta-value">
                      <StatusBadge status={order.payment?.status || "pending"} />
                    </div>
                  </div>
                  <div className="order-meta-item">
                    <div className="order-meta-label">Método</div>
                    <div className="order-meta-value">{order.payment_method === "pix" ? "PIX" : "Cartão"}</div>
                  </div>
                </div>
                <div className="inline-actions" style={{ marginTop: "var(--sp-3)" }}>
                  <button
                    className="button button-secondary"
                    onClick={() => handleSyncPayment(order.id)}
                    disabled={syncing[order.id]}
                  >
                    {syncing[order.id] ? <><SpinnerIcon /> Sincronizando…</> : "Sincronizar pagamento"}
                  </button>
                </div>
                <button
                  className="button button-secondary"
                  onClick={() => handleResend(order.id)}
                  disabled={resending[order.id]}
                  style={{ marginTop: "var(--sp-3)" }}
                >
                  {resending[order.id] ? <><SpinnerIcon /> Enviando…</> : resent[order.id] ? "✓ Enviado!" : "Reenviar ingressos"}
                </button>
              </article>
            ))}
          </div>

          {/* Ingressos */}
          <div>
            <h2>Ingressos</h2>
            {loading && tickets.length === 0 && (
              <div className="empty-state">Carregando…</div>
            )}
            {!loading && tickets.length === 0 && (
              <div className="empty-state">Nenhum ingresso encontrado.</div>
            )}
            {tickets.map((ticket) => (
              <article key={ticket.id} className="card order-card">
                <div className="order-card-header">
                  <div>
                    <p className="order-card-name">{ticket.participant_name}</p>
                    {ticket.participant_email && (
                      <p className="order-card-email">{ticket.participant_email}</p>
                    )}
                  </div>
                  <StatusBadge status={ticket.status} />
                </div>
                <div className="inline-actions" style={{ marginTop: "var(--sp-3)" }}>
                  <button
                    className="button button-secondary"
                    onClick={() => openModal("edit", ticket)}
                  >
                    Editar
                  </button>
                  <button
                    className="button button-secondary"
                    onClick={() => openModal("transfer", ticket)}
                  >
                    Transferir
                  </button>
                </div>
              </article>
            ))}
          </div>

        </div>
      </section>

      {/* Modal de edição / transferência */}
      {ticketModal && (
        <div
          className="modal-overlay"
          role="dialog"
          aria-modal="true"
          aria-labelledby="ticket-modal-title"
          onClick={(e) => { if (e.target === e.currentTarget && !modalLoading) setTicketModal(null); }}
        >
          <div className="modal-box">
            <h2 id="ticket-modal-title">
              {ticketModal.mode === "edit" ? "Editar ingresso" : "Transferir ingresso"}
            </h2>
            {ticketModal.mode === "transfer" && (
              <p className="modal-body">
                Informe os dados do novo titular. O ingresso original de{" "}
                <strong>{ticketModal.ticket.participant_name}</strong> será transferido.
              </p>
            )}
            <div className="stack-form" style={{ marginTop: "var(--sp-2)" }}>
              <div className="field">
                <label htmlFor="modal-name">
                  {ticketModal.mode === "edit" ? "Nome" : "Nome do novo titular"}{" "}
                  <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="modal-name"
                  ref={modalNameRef}
                  type="text"
                  value={modalName}
                  onChange={(e) => setModalName(e.target.value)}
                  autoComplete="name"
                />
              </div>
              <div className="field">
                <label htmlFor="modal-email">
                  E-mail <span className="optional">(opcional)</span>
                </label>
                <input
                  id="modal-email"
                  type="email"
                  value={modalEmail}
                  onChange={(e) => setModalEmail(e.target.value)}
                  inputMode="email"
                />
              </div>
            </div>
            <div className="modal-actions">
              <button
                type="button"
                className="button"
                onClick={() => setTicketModal(null)}
                disabled={modalLoading}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="button button-primary"
                onClick={confirmModal}
                disabled={modalLoading || !modalName.trim()}
              >
                {modalLoading ? <><SpinnerIcon /> Salvando…</> : ticketModal.mode === "edit" ? "Salvar" : "Transferir"}
              </button>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  );
}
