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
  if (["paid", "approved", "active", "confirmed"].includes(norm)) cls += " paid";
  else if (norm === "pending") cls += " pending";
  else if (["failed", "expired"].includes(norm)) cls += " failed";
  else if (norm === "used") cls += " used";
  return <span className={cls}>{statusLabel[norm] || status}</span>;
}

type ModalMode = "edit" | "transfer";
interface TicketModal { mode: ModalMode; ticket: any }

function formatCurrency(value: string | number) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortCode(value?: string) {
  if (!value) return "-";
  return value.slice(0, 8);
}

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

  const hasIssuedTickets = (order: any) => order.status === "paid" || order.payment?.status === "confirmed";

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

        <div className="admin-operations-grid">
          <section className="admin-list-panel">
            <div className="admin-list-header">
              <div>
                <h2>Pedidos</h2>
                <p>{orders.length} registro{orders.length === 1 ? "" : "s"}</p>
              </div>
            </div>
            {loading && orders.length === 0 && (
              <div className="empty-state">Carregando…</div>
            )}
            {!loading && orders.length === 0 && (
              <div className="empty-state">Nenhum pedido encontrado.</div>
            )}
            {orders.length > 0 && (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Pedido</th>
                      <th>Comprador</th>
                      <th>Qtd.</th>
                      <th>Total</th>
                      <th>Pedido</th>
                      <th>Cobranca</th>
                      <th>Metodo</th>
                      <th>Criado</th>
                      <th>Acoes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => (
                      <tr key={order.id}>
                        <td>
                          <span className="admin-code" title={order.public_id}>
                            {order.order_code || shortCode(order.public_id)}
                          </span>
                        </td>
                        <td>
                          <div className="admin-primary-text">{order.buyer_name}</div>
                          <div className="admin-secondary-text">{order.buyer_email}</div>
                        </td>
                        <td>{order.quantity}</td>
                        <td>{formatCurrency(order.total_amount)}</td>
                        <td><StatusBadge status={order.status} /></td>
                        <td><StatusBadge status={order.payment?.status || "pending"} /></td>
                        <td>{order.payment_method === "pix" ? "PIX" : "Cartao"}</td>
                        <td>{formatDate(order.created_at)}</td>
                        <td>
                          <div className="admin-row-actions">
                            <button
                              className="admin-text-button"
                              onClick={() => handleSyncPayment(order.id)}
                              disabled={syncing[order.id]}
                            >
                              {syncing[order.id] ? "Sincronizando..." : "Sincronizar"}
                            </button>
                            <button
                              className="admin-text-button"
                              onClick={() => handleResend(order.id)}
                              disabled={resending[order.id] || !hasIssuedTickets(order)}
                            >
                              {resending[order.id]
                                ? "Enviando..."
                                : resent[order.id]
                                  ? "Enviado"
                                  : hasIssuedTickets(order)
                                    ? "Reenviar"
                                    : "Aguardando"}
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="admin-list-panel">
            <div className="admin-list-header">
              <div>
                <h2>Ingressos emitidos</h2>
                <p>{tickets.length} registro{tickets.length === 1 ? "" : "s"}</p>
              </div>
            </div>
            {loading && tickets.length === 0 && (
              <div className="empty-state">Carregando…</div>
            )}
            {!loading && tickets.length === 0 && (
              <div className="empty-state">Nenhum ingresso emitido encontrado. Pedidos pendentes aparecem apenas na coluna de pedidos.</div>
            )}
            {tickets.length > 0 && (
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Ingresso</th>
                      <th>Participante</th>
                      <th>Comprador</th>
                      <th>Status</th>
                      <th>Check-in</th>
                      <th>Acoes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tickets.map((ticket) => (
                      <tr key={ticket.id}>
                        <td>
                          <span className="admin-code" title={ticket.ticket_code}>
                            #{shortCode(ticket.ticket_code)}
                          </span>
                        </td>
                        <td>
                          <div className="admin-primary-text">{ticket.participant_name}</div>
                          {ticket.participant_email && (
                            <div className="admin-secondary-text">{ticket.participant_email}</div>
                          )}
                        </td>
                        <td>
                          <div className="admin-primary-text">{ticket.order?.buyer_name || "-"}</div>
                          <div className="admin-secondary-text">{ticket.order?.buyer_email || ""}</div>
                        </td>
                        <td><StatusBadge status={ticket.status} /></td>
                        <td>{ticket.checked_in_at ? formatDate(ticket.checked_in_at) : "-"}</td>
                        <td>
                          <div className="admin-row-actions">
                            <button className="admin-text-button" onClick={() => openModal("edit", ticket)}>
                              Editar
                            </button>
                            <button className="admin-text-button" onClick={() => openModal("transfer", ticket)}>
                              Transferir
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
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
