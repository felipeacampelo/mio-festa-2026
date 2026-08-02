import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { EventSettings, createOrder, getEvent } from "../services/api";

type Participant = {
  participant_name: string;
  participant_email: string;
  is_child: boolean;
  participant_document: string;
  participant_birth_date: string;
};

function PixIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M9.5 4.5a3.5 3.5 0 0 1 5 0l5 5a3.5 3.5 0 0 1 0 5l-5 5a3.5 3.5 0 0 1-5 0l-5-5a3.5 3.5 0 0 1 0-5z"/>
    </svg>
  );
}

function CardIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
      <line x1="1" y1="10" x2="23" y2="10" />
    </svg>
  );
}

function SpinnerIcon() {
  return (
    <svg className="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" width="16" height="16" aria-hidden="true">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

function formatDateShort(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString("pt-BR", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatPrice(price: string | number) {
  return Number(price).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export default function CheckoutPage() {
  const navigate = useNavigate();
  const [event, setEvent] = useState<EventSettings | null>(null);
  const [buyerName, setBuyerName] = useState("");
  const [buyerEmail, setBuyerEmail] = useState("");
  const [buyerPhone, setBuyerPhone] = useState("");
  const [buyerDocument, setBuyerDocument] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<"pix" | "credit_card">("pix");
  const [participants, setParticipants] = useState<Participant[]>([
    { participant_name: "", participant_email: "", is_child: false, participant_document: "", participant_birth_date: "" },
  ]);
  const [accepted, setAccepted] = useState(false);
  const [acceptError, setAcceptError] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const errorRef = useRef<HTMLDivElement>(null);
  const checkboxRef = useRef<HTMLLabelElement>(null);

  useEffect(() => {
    getEvent().then(setEvent);
  }, []);

  useEffect(() => {
    if (error) {
      errorRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [error]);

  const paidCount = useMemo(() => participants.filter((p) => !p.is_child).length, [participants]);

  const total = useMemo(() => {
    const price = Number(event?.price || 0);
    return (price * paidCount).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  }, [event, paidCount]);

  const updateParticipant = (index: number, field: keyof Participant, value: string) => {
    setParticipants((current) =>
      current.map((item, i) => (i === index ? { ...item, [field]: value } : item))
    );
  };

  const setParticipantCount = (count: number) => {
    const safeCount = Math.max(1, Math.min(10, count));
    setParticipants((current) => {
      if (safeCount === current.length) return current;
      if (safeCount < current.length) return current.slice(0, safeCount);
      return [
        ...current,
        ...Array.from({ length: safeCount - current.length }, () => ({
          participant_name: "",
          participant_email: "",
          is_child: false,
          participant_document: "",
          participant_birth_date: "",
        })),
      ];
    });
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!accepted) {
      setAcceptError(true);
      checkboxRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    setAcceptError(false);
    setShowConfirm(true);
  };

  const doSubmit = async () => {
    setLoading(true);
    setError("");
    try {
      const order = await createOrder({
        buyer_name: buyerName,
        buyer_email: buyerEmail,
        buyer_phone: buyerPhone,
        buyer_document: buyerDocument,
        payment_method: paymentMethod,
        accepted_no_refund: accepted,
        participants: participants.map((p) =>
          p.is_child
            ? { participant_name: p.participant_name, participant_email: "", is_child: true, participant_document: p.participant_document, participant_birth_date: p.participant_birth_date }
            : { participant_name: p.participant_name, participant_email: p.participant_email, is_child: false }
        ),
      });
      navigate(`/pedido/${order.public_id}?access_token=${order.access_token}`);
    } catch (err: any) {
      setShowConfirm(false);
      setError(
        err.response?.data?.non_field_errors?.[0] ||
          err.response?.data?.buyer_document?.[0] ||
          err.response?.data?.detail ||
          "Não foi possível criar o pedido. Tente novamente."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <section className="page">

        {/* Resumo do evento */}
        {event && (
          <div className="checkout-summary">
            <div className="checkout-summary-info">
              <span className="checkout-summary-name">{event.name}</span>
              <div className="checkout-summary-details">
                {event.event_date && (
                  <span className="checkout-summary-detail">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                    </svg>
                    {formatDateShort(event.event_date)}
                  </span>
                )}
                {event.location && (
                  <span className="checkout-summary-detail">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                    </svg>
                    {event.location}
                  </span>
                )}
              </div>
            </div>
            {event.price && (
              <div className="checkout-summary-price">
                <span className="checkout-summary-price-value">{formatPrice(event.price)}</span>
                <span className="checkout-summary-price-label">por ingresso</span>
                <span className="checkout-summary-price-note">R$&nbsp;35 revertidos em consumação</span>
              </div>
            )}
          </div>
        )}

        <div className="page-header">
          <h1>Garantir meu ingresso</h1>
          <p>Cada ingresso é nominal — preencha o nome de quem vai usar.</p>
        </div>

        <form className="stack-form" onSubmit={onSubmit} noValidate>

          {/* Comprador */}
          <div className="card">
            <h2>Dados do comprador</h2>
            <div className="stack-form">
              <div className="field">
                <label htmlFor="buyerName">
                  Nome completo <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="buyerName"
                  type="text"
                  placeholder="Ex: Maria da Silva"
                  value={buyerName}
                  onChange={(e) => setBuyerName(e.target.value)}
                  autoComplete="name"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="buyerEmail">
                  E-mail <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="buyerEmail"
                  type="email"
                  placeholder="Ex: maria@email.com"
                  value={buyerEmail}
                  onChange={(e) => setBuyerEmail(e.target.value)}
                  autoComplete="email"
                  inputMode="email"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="buyerPhone">
                  Telefone / WhatsApp <span className="optional">(opcional)</span>
                </label>
                <input
                  id="buyerPhone"
                  type="tel"
                  placeholder="Ex: (61) 9 9999-9999"
                  value={buyerPhone}
                  onChange={(e) => setBuyerPhone(e.target.value)}
                  autoComplete="tel"
                  inputMode="tel"
                />
              </div>

              <div className="field">
                <label htmlFor="buyerDocument">
                  CPF ou CNPJ <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="buyerDocument"
                  type="text"
                  placeholder="Ex: 000.000.000-00"
                  value={buyerDocument}
                  onChange={(e) => setBuyerDocument(e.target.value)}
                  inputMode="numeric"
                  required
                />
              </div>
            </div>
          </div>

          {/* Participantes */}
          <div className="card">
            <div className="inline-between" style={{ marginBottom: "var(--sp-5)", paddingBottom: "var(--sp-4)", borderBottom: "1px solid var(--border)" }}>
              <div>
                <h2 style={{ margin: 0, padding: 0, border: 0 }}>Ingressos</h2>
                <p className="muted" style={{ marginTop: "var(--sp-2)" }}>
                  Escolha quantos ingressos deseja comprar e preencha os dados de cada participante.
                </p>
              </div>
            </div>

            <div className="ticket-quantity-card">
              <div>
                <p className="form-label">Quantidade de ingressos</p>
                <span className="ticket-quantity-caption">Cada ingresso gera um QR code nominal.</span>
              </div>

              <div className="ticket-stepper" aria-label="Quantidade de ingressos">
                <button
                  type="button"
                  className="ticket-stepper-button"
                  onClick={() => setParticipantCount(participants.length - 1)}
                  disabled={participants.length <= 1}
                  aria-label="Diminuir quantidade de ingressos"
                >
                  -
                </button>
                <span className="ticket-stepper-value">{participants.length}</span>
                <button
                  type="button"
                  className="ticket-stepper-button"
                  onClick={() => setParticipantCount(participants.length + 1)}
                  disabled={participants.length >= 10}
                  aria-label="Aumentar quantidade de ingressos"
                >
                  +
                </button>
              </div>
            </div>

            <div className="stack-form">
              {participants.map((participant, index) => (
                <div key={index} className="participant-block">
                  <div className="inline-between" style={{ marginBottom: "var(--sp-4)" }}>
                    <p className="participant-number">Ingresso {index + 1}</p>
                    <span className="participant-helper">Participante {index + 1} de {participants.length}</span>
                  </div>

                  <label className="child-toggle">
                    <input
                      type="checkbox"
                      checked={participant.is_child}
                      onChange={(e) => updateParticipant(index, "is_child", e.target.checked as any)}
                    />
                    <span>Criança até 6 anos <span className="child-toggle-badge">Gratuito</span></span>
                  </label>

                  <div className="participant-grid">
                    <div className="field">
                      <label htmlFor={`participant-name-${index}`}>
                        Nome {participant.is_child ? "da criança" : "do participante"} <span className="req" aria-hidden="true">*</span>
                      </label>
                      <input
                        id={`participant-name-${index}`}
                        type="text"
                        placeholder="Nome completo"
                        value={participant.participant_name}
                        onChange={(e) =>
                          updateParticipant(index, "participant_name", e.target.value)
                        }
                        required
                      />
                    </div>

                    {!participant.is_child && (
                      <div className="field">
                        <label htmlFor={`participant-email-${index}`}>
                          E-mail do participante <span className="optional">(opcional)</span>
                        </label>
                        <input
                          id={`participant-email-${index}`}
                          type="email"
                          placeholder="email@exemplo.com"
                          value={participant.participant_email}
                          onChange={(e) =>
                            updateParticipant(index, "participant_email", e.target.value)
                          }
                          inputMode="email"
                        />
                      </div>
                    )}

                    {participant.is_child && (
                      <>
                        <div className="field">
                          <label htmlFor={`participant-doc-${index}`}>
                            CPF da criança <span className="req" aria-hidden="true">*</span>
                          </label>
                          <input
                            id={`participant-doc-${index}`}
                            type="text"
                            placeholder="000.000.000-00"
                            value={participant.participant_document}
                            onChange={(e) =>
                              updateParticipant(index, "participant_document", e.target.value)
                            }
                            inputMode="numeric"
                            required
                          />
                        </div>

                        <div className="field">
                          <label htmlFor={`participant-birth-${index}`}>
                            Data de nascimento <span className="req" aria-hidden="true">*</span>
                          </label>
                          <input
                            id={`participant-birth-${index}`}
                            type="date"
                            value={participant.participant_birth_date}
                            onChange={(e) =>
                              updateParticipant(index, "participant_birth_date", e.target.value)
                            }
                            required
                          />
                        </div>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Pagamento */}
          <div className="card">
            <h2>Pagamento</h2>
            <div className="stack-form">
              <div>
                <p className="form-label" style={{ marginBottom: "var(--sp-3)" }}>
                  Forma de pagamento
                </p>
                <div className="payment-toggle" role="radiogroup" aria-label="Forma de pagamento">
                  <div className="payment-option">
                    <input
                      type="radio"
                      id="method-pix"
                      name="paymentMethod"
                      checked={paymentMethod === "pix"}
                      onChange={() => setPaymentMethod("pix")}
                    />
                    <label className="payment-option-label" htmlFor="method-pix">
                      <span className="payment-option-icon"><PixIcon /></span>
                      <span className="payment-option-content">
                        <span className="payment-option-name">PIX</span>
                        <span className="payment-option-desc">Aprovação imediata</span>
                      </span>
                    </label>
                  </div>

                  <div className="payment-option">
                    <input
                      type="radio"
                      id="method-card"
                      name="paymentMethod"
                      checked={paymentMethod === "credit_card"}
                      onChange={() => setPaymentMethod("credit_card")}
                    />
                    <label className="payment-option-label" htmlFor="method-card">
                      <span className="payment-option-icon"><CardIcon /></span>
                      <span className="payment-option-content">
                        <span className="payment-option-name">Cartão</span>
                        <span className="payment-option-desc">Crédito ou débito</span>
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="total-summary">
                <span className="total-label">
                  {paidCount} ingresso{paidCount !== 1 ? "s" : ""}
                  {participants.length > paidCount && (
                    <span className="total-children"> + {participants.length - paidCount} criança{participants.length - paidCount !== 1 ? "s" : ""} (grátis)</span>
                  )}
                </span>
                <span className="total-value">{total}</span>
              </div>

              <label
                ref={checkboxRef}
                className={`checkbox${acceptError ? " checkbox-error" : ""}`}
              >
                <input
                  type="checkbox"
                  checked={accepted}
                  onChange={(e) => {
                    setAccepted(e.target.checked);
                    if (e.target.checked) setAcceptError(false);
                  }}
                />
                <span>
                  Li e aceito a{" "}
                  <strong>política de não reembolso</strong>
                  {event?.no_refund_policy ? `: ${event.no_refund_policy}` : "."}
                </span>
              </label>
              {acceptError && (
                <p className="accept-error-hint" role="alert">
                  Você precisa aceitar a política de não reembolso para continuar.
                </p>
              )}
            </div>
          </div>

          {error && (
            <div className="error-box" role="alert" ref={errorRef}>
              {error}
            </div>
          )}

          <button
            type="submit"
            className="button button-primary"
            disabled={loading}
            style={{ width: "100%", padding: "1rem" }}
          >
            {loading
              ? <><SpinnerIcon /> Criando pedido…</>
              : "Finalizar compra"}
          </button>

          {/* Barra sticky em mobile */}
          <div className="checkout-sticky-cta" aria-hidden="true">
            <div className="checkout-sticky-info">
              <span className="checkout-sticky-qty">
                {paidCount} ingresso{paidCount !== 1 ? "s" : ""}
                {participants.length > paidCount && ` + ${participants.length - paidCount} criança${participants.length - paidCount !== 1 ? "s" : ""}`}
              </span>
              <span className="checkout-sticky-total">{total}</span>
            </div>
            <button type="submit" className="button button-primary" disabled={loading}>
              {loading ? <><SpinnerIcon /> Processando…</> : "Finalizar"}
            </button>
          </div>

        </form>

        {/* Modal de confirmação */}
        {showConfirm && (
          <div
            className="modal-overlay"
            role="dialog"
            aria-modal="true"
            aria-labelledby="confirm-title"
            onClick={(e) => { if (e.target === e.currentTarget && !loading) setShowConfirm(false); }}
          >
            <div className="modal-box">
              <h2 id="confirm-title">Confirmar compra</h2>
              <p className="modal-body">
                Você está comprando{" "}
                <strong>{paidCount} ingresso{paidCount !== 1 ? "s" : ""}</strong>
                {participants.length > paidCount && (
                  <> + <strong>{participants.length - paidCount} ingresso{participants.length - paidCount !== 1 ? "s" : ""} infantil{participants.length - paidCount !== 1 ? "s" : ""} (grátis)</strong></>
                )}{" "}
                por <strong>{total}</strong>.
              </p>
              <p className="modal-warning">
                Esta compra não é reembolsável.
              </p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="button"
                  onClick={() => setShowConfirm(false)}
                  disabled={loading}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="button button-primary"
                  onClick={doSubmit}
                  disabled={loading}
                >
                  {loading ? <><SpinnerIcon /> Processando…</> : "Confirmar e pagar"}
                </button>
              </div>
            </div>
          </div>
        )}

      </section>
    </Layout>
  );
}
