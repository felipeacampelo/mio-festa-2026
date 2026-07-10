import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import Layout from "../components/Layout";
import { Order, getOrder } from "../services/api";

function StatusBadge({ status }: { status: string }) {
  const normalized = status?.toLowerCase() || "";
  let cls = "status-badge";
  if (["paid", "approved", "active"].includes(normalized)) cls += " paid";
  else if (["pending"].includes(normalized)) cls += " pending";
  else if (["failed"].includes(normalized)) cls += " failed";
  else if (["used"].includes(normalized)) cls += " used";
  return <span className={cls}>{status}</span>;
}

const statusLabels: Record<string, string> = {
  pending: "Aguardando pagamento",
  paid: "Pago",
  approved: "Aprovado",
  active: "Ativo",
  used: "Utilizado",
  failed: "Falhou",
};

export default function OrderPage() {
  const { publicId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const [order, setOrder] = useState<Order | null>(null);

  useEffect(() => {
    const token = searchParams.get("access_token");
    if (!token || !publicId) return;
    getOrder(publicId, token).then(setOrder);
  }, [publicId, searchParams]);

  return (
    <Layout>
      <section className="page">
        <div className="page-header">
          <h1>Meu pedido</h1>
          {order && (
            <p>
              Código: <strong>{order.public_id}</strong>
            </p>
          )}
        </div>

        {order && (
          <>
            <div className="order-meta">
              <div className="order-meta-item">
                <p className="order-meta-label">Status do pedido</p>
                <StatusBadge status={statusLabels[order.status] || order.status} />
              </div>
              <div className="order-meta-item">
                <p className="order-meta-label">Pagamento</p>
                <StatusBadge
                  status={
                    statusLabels[order.payment?.status || ""] ||
                    order.payment?.status ||
                    "pendente"
                  }
                />
              </div>
            </div>

            {order.payment?.method === "pix" && order.payment.pix_copy_paste && (
              <div className="card" style={{ marginBottom: "var(--sp-5)" }}>
                <h2>Pagar via PIX</h2>
                <p style={{ marginBottom: "var(--sp-4)" }}>
                  Copie o código abaixo e cole no seu banco para realizar o pagamento.
                </p>
                <div className="field">
                  <label htmlFor="pixCode">Código PIX (Copia e Cola)</label>
                  <textarea
                    id="pixCode"
                    readOnly
                    value={order.payment.pix_copy_paste}
                    rows={4}
                    onClick={(e) => (e.target as HTMLTextAreaElement).select()}
                    style={{ cursor: "pointer", fontFamily: "monospace", fontSize: "0.82rem" }}
                    aria-label="Código PIX para copiar"
                  />
                </div>
              </div>
            )}

            {order.payment?.checkout_url && (
              <div className="card" style={{ marginBottom: "var(--sp-5)" }}>
                <h2>Pagamento por cartão</h2>
                <p style={{ marginBottom: "var(--sp-4)" }}>
                  Clique abaixo para acessar o checkout seguro e finalizar o pagamento.
                </p>
                <a
                  className="button button-primary"
                  href={order.payment.checkout_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  Ir para o checkout
                </a>
              </div>
            )}

            <h2 style={{ fontFamily: "var(--font-display)", fontSize: "1.5rem", letterSpacing: "0.04em", color: "var(--brand-dark)", marginBottom: "var(--sp-2)" }}>
              Ingressos
            </h2>
            <p style={{ color: "var(--text-muted)", fontSize: "0.88rem", marginBottom: "0" }}>
              Os QR Codes abaixo serão validados na entrada do evento.
            </p>

            <div className="ticket-grid">
              {order.tickets.map((ticket) => (
                <article key={ticket.id} className="ticket-card">
                  <div className="ticket-card-header">
                    <h3>{ticket.participant_name}</h3>
                    {ticket.participant_email && (
                      <p>{ticket.participant_email}</p>
                    )}
                  </div>
                  <div className="ticket-card-body">
                    <StatusBadge status={statusLabels[ticket.status] || ticket.status} />
                    {ticket.qr_code_data_url && (
                      <img
                        src={ticket.qr_code_data_url}
                        alt={`QR Code do ingresso de ${ticket.participant_name}`}
                        className="qr-preview"
                      />
                    )}
                  </div>
                </article>
              ))}
            </div>
          </>
        )}

        {!order && (
          <div className="card">
            <p style={{ textAlign: "center", color: "var(--text-muted)" }}>
              Carregando dados do pedido…
            </p>
          </div>
        )}
      </section>
    </Layout>
  );
}
