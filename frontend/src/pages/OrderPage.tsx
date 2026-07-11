import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import Layout from "../components/Layout";
import { Order, getOrder } from "../services/api";

type BadgeTone = "pending" | "paid" | "failed" | "used" | "closed";

function StatusBadge({ status, label }: { status: string; label?: string }) {
  const normalized = status?.toLowerCase() || "";
  let tone: BadgeTone = "pending";
  if (["paid", "approved", "active", "confirmed"].includes(normalized)) tone = "paid";
  else if (["failed", "cancelled", "canceled", "blocked"].includes(normalized)) tone = "failed";
  else if (["used"].includes(normalized)) tone = "used";
  else if (["expired", "closed"].includes(normalized)) tone = "closed";

  return <span className={`status-badge ${tone}`}>{label || status}</span>;
}

const statusLabels: Record<string, string> = {
  active: "Ativo",
  approved: "Aprovado",
  blocked: "Bloqueado",
  cancelled: "Cancelado",
  confirmed: "Confirmado",
  expired: "Expirado",
  failed: "Falhou",
  paid: "Pago",
  pending: "Aguardando pagamento",
  used: "Utilizado",
};

function labelStatus(status?: string | null) {
  if (!status) return "Pendente";
  return statusLabels[status.toLowerCase()] || status;
}

function buildPixQrCodeSrc(value?: string | null) {
  if (!value) return "";
  if (value.startsWith("data:image/")) return value;
  return `data:image/png;base64,${value}`;
}

function formatCurrency(value: string | number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(value));
}

function getPaymentTitle(order: Order) {
  const paymentStatus = order.payment?.status;
  if (order.status === "paid" || paymentStatus === "confirmed") return "Pagamento confirmado";
  if (order.status === "expired" || paymentStatus === "expired") return "Pagamento expirado";
  return "Finalize seu pagamento";
}

function getPaymentDescription(order: Order) {
  const paymentStatus = order.payment?.status;
  if (order.status === "paid" || paymentStatus === "confirmed") {
    return "Seus ingressos já foram liberados. Apresente o QR Code individual de cada participante na entrada.";
  }
  if (order.status === "expired" || paymentStatus === "expired") {
    return "Esta cobrança não está mais ativa. Procure a organização com o código do pedido para verificação.";
  }
  return "Para garantir seus ingressos, conclua o pagamento nesta tela. Os QR Codes serão liberados assim que o pagamento for confirmado.";
}

export default function OrderPage() {
  const { publicId = "" } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("access_token") || "";
  const [order, setOrder] = useState<Order | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  async function loadOrder(showRefreshing = false) {
    if (!token || !publicId) {
      setLoading(false);
      setError("Link do pedido inválido ou incompleto.");
      return;
    }

    if (showRefreshing) setRefreshing(true);
    try {
      const data = await getOrder(publicId, token);
      setOrder(data);
      setError("");
    } catch {
      setError("Não foi possível carregar este pedido. Confira o link ou consulte pelo e-mail do comprador.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function copyPixCode() {
    if (!order?.payment?.pix_copy_paste) return;
    try {
      await navigator.clipboard.writeText(order.payment.pix_copy_paste);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2500);
    } catch {
      setCopyState("failed");
      window.setTimeout(() => setCopyState("idle"), 2500);
    }
  }

  useEffect(() => {
    loadOrder();
  }, [publicId, token]);

  useEffect(() => {
    if (!order || order.status === "paid" || order.payment?.status === "confirmed") return;
    if (order.status === "expired" || order.payment?.status === "expired") return;

    const intervalId = window.setInterval(() => {
      loadOrder();
    }, 8000);

    return () => window.clearInterval(intervalId);
  }, [order?.status, order?.payment?.status, publicId, token]);

  const isPaid = order?.status === "paid" || order?.payment?.status === "confirmed";
  const isExpired = order?.status === "expired" || order?.payment?.status === "expired";
  const isPixPending = order?.payment?.method === "pix" && !isPaid && !isExpired;
  const isCardPending = order?.payment?.method === "credit_card" && !isPaid && !isExpired;

  return (
    <Layout>
      <section className="page order-page">
        {loading && (
          <div className="order-state-card">
            <p>Carregando dados do pedido...</p>
          </div>
        )}

        {!loading && error && (
          <div className="order-state-card order-state-card-error">
            <h1>Pedido não encontrado</h1>
            <p>{error}</p>
            <Link className="button button-primary" to="/pedido">
              Consultar pedido
            </Link>
          </div>
        )}

        {!loading && order && (
          <>
            <header className={`order-hero ${isPaid ? "is-paid" : ""} ${isExpired ? "is-expired" : ""}`}>
              <div className="order-hero-copy">
                {(isPaid || isExpired) && (
                  <StatusBadge status={order.status} label={labelStatus(order.status)} />
                )}
                <h1>{getPaymentTitle(order)}</h1>
                <p>{getPaymentDescription(order)}</p>
              </div>
              <div className="order-hero-summary">
                <div className="order-summary-item">
                  <span>Total</span>
                  <strong>{formatCurrency(order.total_amount)}</strong>
                </div>
                <div className="order-summary-item">
                  <span>Ingressos</span>
                  <strong>{order.quantity}</strong>
                </div>
                <div className="order-summary-item order-summary-code">
                  <span>Pedido</span>
                  <strong>{order.order_code}</strong>
                </div>
              </div>
            </header>

            {isPixPending && order.payment?.pix_copy_paste && (
              <section className="payment-panel">
                <div className="payment-panel-header">
                  <span className="payment-kicker">PIX</span>
                  <h2>Pague agora para liberar seus ingressos</h2>
                  <p>Use o QR Code ou copie o código PIX. Mantenha esta página aberta até a confirmação aparecer.</p>
                </div>

                <div className="pix-payment-layout">
                  <div className="pix-qr-surface">
                    {order.payment.pix_qr_code ? (
                      <img
                        src={buildPixQrCodeSrc(order.payment.pix_qr_code)}
                        alt="QR Code PIX para pagamento"
                        className="pix-qr-code"
                      />
                    ) : (
                      <p className="pix-qr-empty">QR Code indisponível. Use o código copia e cola.</p>
                    )}
                  </div>

                  <div className="pix-code-card">
                    <div className="pix-code-card-header">
                      <div>
                        <span className="payment-kicker">Copia e cola</span>
                        <h3>Código PIX</h3>
                      </div>
                      <button className="button button-primary" type="button" onClick={copyPixCode}>
                        {copyState === "copied" ? "Copiado" : "Copiar"}
                      </button>
                    </div>
                    <textarea
                      id="pixCode"
                      readOnly
                      value={order.payment.pix_copy_paste}
                      rows={4}
                      onClick={(e) => (e.target as HTMLTextAreaElement).select()}
                      aria-label="Código PIX para copiar"
                    />
                    <div className="payment-actions">
                      <button
                        className="button button-secondary"
                        type="button"
                        onClick={() => loadOrder(true)}
                        disabled={refreshing}
                      >
                        {refreshing ? "Atualizando..." : "Atualizar status"}
                      </button>
                    </div>
                    {copyState === "failed" && (
                      <p className="copy-feedback">Não foi possível copiar automaticamente. Selecione o código acima.</p>
                    )}
                  </div>
                </div>
              </section>
            )}

            {isCardPending && order.payment?.checkout_url && (
              <section className="payment-panel payment-panel-card">
                <div>
                  <span className="payment-kicker">Cartão</span>
                  <h2>Finalize o pagamento agora</h2>
                  <p>Acesse o checkout seguro do Asaas e conclua o pagamento para liberar seus ingressos.</p>
                </div>
                <div className="payment-actions">
                  <a
                    className="button button-primary"
                    href={order.payment.checkout_url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Pagar agora
                  </a>
                  <button
                    className="button button-secondary"
                    type="button"
                    onClick={() => loadOrder(true)}
                    disabled={refreshing}
                  >
                    {refreshing ? "Atualizando..." : "Atualizar status"}
                  </button>
                </div>
              </section>
            )}

            <section className="ticket-section">
              <div className="ticket-section-header">
                <div>
                  <span className="payment-kicker">Ingressos</span>
                  <h2>{isPaid ? "Ingressos liberados" : "Ingressos liberados após pagar"}</h2>
                </div>
                <span className="ticket-count">{order.quantity} ingresso{order.quantity === 1 ? "" : "s"}</span>
              </div>

              {!isPaid && (
                <div className="tickets-locked">
                  <h3>Conclua o pagamento acima para receber os QR Codes.</h3>
                  <p>
                    Cada participante terá um ingresso individual e nominado assim que o pagamento for confirmado.
                  </p>
                </div>
              )}

              {isPaid && (
                <div className="ticket-grid">
                  {order.tickets.map((ticket) => (
                    <article key={ticket.id} className="ticket-card">
                      <div className="ticket-card-header">
                        <span>Ingresso {ticket.ticket_code}</span>
                        <h3>{ticket.participant_name}</h3>
                        {ticket.participant_email && <p>{ticket.participant_email}</p>}
                      </div>
                      <div className="ticket-card-body">
                        <StatusBadge status={ticket.status} label={labelStatus(ticket.status)} />
                        {ticket.qr_code_data_url ? (
                          <img
                            src={ticket.qr_code_data_url}
                            alt={`QR Code do ingresso de ${ticket.participant_name}`}
                            className="qr-preview"
                          />
                        ) : (
                          <p className="ticket-missing-qr">QR Code indisponível para este ingresso.</p>
                        )}
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>

            <aside className="order-help-card">
              <div>
                <span className="payment-kicker">Suporte</span>
                <h2>Precisa de ajuda?</h2>
              </div>
              <p>Se o pagamento já foi feito e os ingressos ainda não aparecerem, aguarde alguns segundos e atualize o status. Para suporte, informe o código do pedido.</p>
            </aside>
          </>
        )}
      </section>
    </Layout>
  );
}
