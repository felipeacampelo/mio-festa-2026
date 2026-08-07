import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import VendorShell from "../components/VendorShell";
import { useVendorAuth } from "../contexts/VendorAuthContext";
import {
  Card,
  CardResult,
  Product,
  TicketSearchResult,
  creditCard,
  debitCard,
  debitCardCart,
  getCard,
  getProducts,
  linkCard,
  searchTickets,
} from "../services/api";
import { PendingCardLink, clearPendingCardLink, getPendingCardLink } from "../services/pendingCardLink";

function SpinnerIcon() {
  return (
    <svg className="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" width="16" height="16" aria-hidden="true">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
      <polyline points="22 4 12 14.01 9 11.01" />
    </svg>
  );
}

function IconX() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function formatMoney(value: string) {
  return Number(value).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

const RESULT_LABELS: Record<string, string> = {
  insufficient_balance: "Saldo insuficiente",
  card_blocked: "Cartão bloqueado",
  card_returned: "Cartão já devolvido",
  not_linked: "Cartão ainda não vinculado",
  card_not_found: "Cartão não encontrado",
  invalid_amount: "Valor inválido",
  already_linked: "Este cartão já está vinculado a outra pessoa.",
  ticket_already_has_card: "Este participante já tem um cartão vinculado.",
  ticket_not_found: "Participante não encontrado.",
  ticket_not_eligible: "Este ingresso ainda não pode ser vinculado a um cartão.",
};

export default function VendorCardPage() {
  const { uid = "" } = useParams();
  const navigate = useNavigate();
  const { vendor, logout } = useVendorAuth();

  const [card, setCard] = useState<Card | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<TicketSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [linking, setLinking] = useState<number | null>(null);

  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CardResult | null>(null);
  const [justLinkedName, setJustLinkedName] = useState<string | null>(null);
  const idempotencyKeyRef = useRef<string | null>(null);

  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<Record<number, number>>({});
  const [manualMode, setManualMode] = useState(false);
  const [pendingLink, setPendingLink] = useState<PendingCardLink | null>(() => getPendingCardLink());

  const setAmountForNewAttempt = (value: string) => {
    idempotencyKeyRef.current = null;
    setAmount(value);
  };

  const resetCartAttempt = () => {
    idempotencyKeyRef.current = null;
  };

  const changeCartQuantity = (productId: number, delta: number) => {
    resetCartAttempt();
    setCart((current) => {
      const next = { ...current };
      const qty = (next[productId] || 0) + delta;
      if (qty <= 0) {
        delete next[productId];
      } else {
        next[productId] = qty;
      }
      return next;
    });
  };

  const cartTotal = products.reduce((sum, p) => sum + (cart[p.id] || 0) * Number(p.price), 0);
  const cartEntries = products
    .filter((p) => cart[p.id] > 0)
    .map((p) => ({ product: p, quantity: cart[p.id] }));

  const loadCard = () => {
    setLoading(true);
    setError("");
    getCard(uid)
      .then(setCard)
      .catch(() => setError("Não foi possível carregar o cartão."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uid]);

  useEffect(() => {
    if (vendor?.role !== "seller") return;
    getProducts()
      .then(setProducts)
      .catch(() => {});
  }, [vendor?.role]);

  useEffect(() => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }
    setSearching(true);
    const handle = setTimeout(() => {
      searchTickets(query.trim())
        .then(setSearchResults)
        .catch(() => setSearchResults([]))
        .finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(handle);
  }, [query]);

  const handleLink = async (ticketId: number) => {
    setLinking(ticketId);
    setError("");
    try {
      const response = await linkCard(uid, ticketId);
      if (response.result === "ok" && response.card) {
        setCard(response.card);
        setQuery("");
        setSearchResults([]);
        setJustLinkedName(response.card.participant_name);
        clearPendingCardLink();
        setPendingLink(null);
      } else {
        setError(RESULT_LABELS[response.result] || "Não foi possível vincular este cartão.");
      }
    } catch {
      setError("Erro de comunicação ao vincular o cartão.");
    } finally {
      setLinking(null);
    }
  };

  const submitManualAction = async () => {
    if (!amount || Number(amount) <= 0) return;
    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = crypto.randomUUID();
    }
    setError("");
    setSubmitting(true);
    try {
      const action = vendor?.role === "recharge" ? creditCard : debitCard;
      const response = await action(uid, amount, idempotencyKeyRef.current);
      setResult(response);
    } catch {
      // Chave preservada de propósito: se a cobrança já tiver sido processada no
      // servidor e só a resposta se perdeu, um retry com chave nova cobraria de novo.
      setError("Erro de comunicação. Toque em cobrar/recarregar de novo para tentar novamente.");
    } finally {
      setSubmitting(false);
    }
  };

  const submitCartAction = async () => {
    if (cartEntries.length === 0) return;
    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = crypto.randomUUID();
    }
    setError("");
    setSubmitting(true);
    try {
      const items = cartEntries.map((e) => ({ product_id: e.product.id, quantity: e.quantity }));
      const response = await debitCardCart(uid, items, idempotencyKeyRef.current);
      setResult(response);
    } catch {
      // Mesma logica do valor manual: chave preservada pra nao cobrar duas vezes
      // se a primeira tentativa ja tiver processado e so a resposta se perdeu.
      setError("Erro de comunicação. Toque em cobrar de novo para tentar novamente.");
    } finally {
      setSubmitting(false);
    }
  };

  const goToNextCard = () => {
    navigate("/caixa", { replace: true });
  };

  if (loading) {
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        <p>Carregando cartão…</p>
      </VendorShell>
    );
  }

  if (result) {
    const success = result.result === "ok";
    const actionLabel = vendor?.role === "recharge" ? "Recarga" : "Cobrança";
    const hasItems = success && result.items && result.items.length > 0;
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        <div className={`checkin-result ${success ? "checkin-success" : "checkin-fail"}`}>
          <div className="checkin-result-icon">{success ? <IconCheck /> : <IconX />}</div>
          <p className="checkin-result-status">
            {success ? `${actionLabel} confirmada` : RESULT_LABELS[result.result] || "Não foi possível concluir"}
          </p>
          {card?.participant_name && <p className="checkin-result-name">{card.participant_name}</p>}
          {hasItems ? (
            <div style={{ margin: "0.5rem 0" }}>
              {result.items!.map((item, i) => (
                <p key={i} className="checkin-result-code" style={{ margin: "0.15rem 0" }}>
                  {item.quantity}x {item.product_name} — {formatMoney((Number(item.unit_price) * item.quantity).toFixed(2))}
                </p>
              ))}
            </div>
          ) : (
            success && <p className="checkin-result-code">{formatMoney(amount)}</p>
          )}
          {result.card && <p className="checkin-result-reason">Saldo atual: {formatMoney(result.card.balance)}</p>}
          <button className="button checkin-next-btn" onClick={goToNextCard}>
            Próximo
          </button>
        </div>
      </VendorShell>
    );
  }

  if (!card) {
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        {error && <div className="error-box" role="alert">{error}</div>}
      </VendorShell>
    );
  }

  if (card.status !== "active") {
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        <div className="card">
          <h2>Cartão {card.status === "blocked" ? "bloqueado" : "devolvido"}</h2>
          <p>Este cartão não pode ser usado. Fale com a organização.</p>
        </div>
      </VendorShell>
    );
  }

  if (justLinkedName) {
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        <div className="checkin-result checkin-success">
          <div className="checkin-result-icon"><IconCheck /></div>
          <p className="checkin-result-status">Cartão vinculado</p>
          <p className="checkin-result-name">{justLinkedName}</p>
          <button className="button checkin-next-btn" onClick={goToNextCard}>
            Próximo
          </button>
        </div>
      </VendorShell>
    );
  }

  if (!card.participant_name) {
    if (vendor?.role !== "checkin") {
      return (
        <VendorShell vendor={vendor} onLogout={logout}>
          <div className="card">
            <h2>Cartão ainda não vinculado</h2>
            <p>Este cartão precisa ser vinculado no check-in antes de ser usado. Peça para a pessoa procurar o check-in.</p>
            <button className="button button-secondary" onClick={goToNextCard} style={{ marginTop: "1rem" }}>
              Próximo
            </button>
          </div>
        </VendorShell>
      );
    }
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        {pendingLink && (
          <div className="card" style={{ marginBottom: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <div style={{ fontSize: "0.8rem", opacity: 0.75 }}>Validado agora no check-in</div>
                <strong>{pendingLink.participantName}</strong>
              </div>
              <button
                className="button button-primary"
                disabled={linking === pendingLink.ticketId}
                onClick={() => handleLink(pendingLink.ticketId)}
              >
                {linking === pendingLink.ticketId ? "Vinculando…" : "Vincular"}
              </button>
            </div>
            <button
              className="button button-secondary"
              type="button"
              style={{ marginTop: "0.75rem", width: "100%" }}
              onClick={() => {
                clearPendingCardLink();
                setPendingLink(null);
              }}
            >
              Não é essa pessoa
            </button>
          </div>
        )}
        <div className="card">
          <h2>Vincular cartão</h2>
          <div className="stack-form">
            <div className="field">
              <label htmlFor="search">Nome ou CPF do participante</label>
              <input
                id="search"
                type="text"
                placeholder="Digite para buscar…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                autoFocus
              />
            </div>
            {searching && <p>Buscando…</p>}
            {!searching && query.trim() && searchResults.length === 0 && <p>Nenhum participante encontrado.</p>}
            {searchResults.map((t) => (
              <div key={t.id} className="card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <strong>{t.participant_name}</strong>
                  {t.is_child && <span className="child-toggle-badge" style={{ marginLeft: "0.5rem" }}>Criança</span>}
                  {t.purchased_on_event_day && (
                    <span className="child-toggle-badge" style={{ marginLeft: "0.5rem" }}>Compra no dia — sem consumação</span>
                  )}
                  <div style={{ fontSize: "0.85rem", opacity: 0.75 }}>Pedido de {t.order_buyer_name}</div>
                </div>
                <button
                  className="button button-primary"
                  disabled={t.has_card || linking === t.id}
                  onClick={() => handleLink(t.id)}
                >
                  {t.has_card ? "Já tem cartão" : linking === t.id ? "Vinculando…" : "Vincular"}
                </button>
              </div>
            ))}
          </div>
          {error && <div className="error-box" role="alert">{error}</div>}
        </div>
      </VendorShell>
    );
  }

  if (vendor?.role === "checkin") {
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        <div className="card">
          <h2>{card.participant_name}</h2>
          <p>Cartão já vinculado. Nada mais a fazer aqui.</p>
          <button className="button button-secondary" onClick={goToNextCard} style={{ marginTop: "1rem" }}>
            Próximo
          </button>
        </div>
      </VendorShell>
    );
  }

  const isRecharge = vendor?.role === "recharge";
  const showManualForm = isRecharge || manualMode;

  if (showManualForm) {
    return (
      <VendorShell vendor={vendor} onLogout={logout}>
        <div className="card">
          <h2>{card.participant_name}</h2>
          <p style={{ fontSize: "1.5rem", fontWeight: 700 }}>{formatMoney(card.balance)}</p>
          <div className="stack-form">
            <div className="field">
              <label htmlFor="amount">Valor {isRecharge ? "a recarregar" : "da compra"}</label>
              <input
                id="amount"
                type="text"
                inputMode="decimal"
                placeholder="0,00"
                value={amount}
                onChange={(e) => setAmountForNewAttempt(e.target.value.replace(",", "."))}
                autoFocus
              />
            </div>
            <button
              className="button button-primary"
              disabled={!amount || Number(amount) <= 0 || submitting}
              onClick={submitManualAction}
            >
              {submitting ? <><SpinnerIcon /> Processando…</> : isRecharge ? "Adicionar saldo" : "Cobrar"}
            </button>
            {!isRecharge && (
              <button
                className="button button-secondary"
                type="button"
                onClick={() => {
                  setManualMode(false);
                  setAmountForNewAttempt("");
                }}
              >
                Voltar pro carrinho
              </button>
            )}
          </div>
          {error && <div className="error-box" role="alert">{error}</div>}
        </div>
      </VendorShell>
    );
  }

  return (
    <VendorShell vendor={vendor} onLogout={logout}>
      <div className="card">
        <h2>{card.participant_name}</h2>
        <p style={{ fontSize: "1.5rem", fontWeight: 700 }}>{formatMoney(card.balance)}</p>

        {products.length === 0 && <p>Nenhum produto cadastrado ainda.</p>}
        <div className="stack-form">
          {products.map((p) => {
            const qty = cart[p.id] || 0;
            return (
              <div
                key={p.id}
                className="card"
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
              >
                <div>
                  <strong>{p.name}</strong>
                  <div style={{ fontSize: "0.85rem", opacity: 0.75 }}>{formatMoney(p.price)}</div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <button
                    className="button button-secondary"
                    disabled={qty === 0}
                    onClick={() => changeCartQuantity(p.id, -1)}
                  >
                    −
                  </button>
                  <span style={{ minWidth: "1.5rem", textAlign: "center" }}>{qty}</span>
                  <button className="button button-secondary" onClick={() => changeCartQuantity(p.id, 1)}>
                    +
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            margin: "1rem 0",
            fontSize: "1.25rem",
            fontWeight: 700,
          }}
        >
          <span>Total</span>
          <span>{formatMoney(cartTotal.toFixed(2))}</span>
        </div>

        <div className="stack-form">
          <button
            className="button button-primary"
            disabled={cartEntries.length === 0 || submitting}
            onClick={submitCartAction}
          >
            {submitting ? <><SpinnerIcon /> Processando…</> : "Cobrar"}
          </button>
          <button className="button button-secondary" type="button" onClick={() => setManualMode(true)}>
            Cobrar valor avulso
          </button>
        </div>
        {error && <div className="error-box" role="alert">{error}</div>}
      </div>
    </VendorShell>
  );
}
