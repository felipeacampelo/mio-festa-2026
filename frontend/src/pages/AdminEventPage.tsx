import { FormEvent, useEffect, useRef, useState } from "react";
import AdminShell from "../components/AdminShell";
import { EventSettings, getAdminEvent, updateAdminEvent } from "../services/api";

function SpinnerIcon() {
  return (
    <svg className="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" width="16" height="16" aria-hidden="true">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

export default function AdminEventPage() {
  const [event, setEvent] = useState<EventSettings | null>(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const messageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getAdminEvent().then(setEvent).catch(() => {});
  }, []);

  useEffect(() => {
    if (message) {
      messageRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [message]);

  const onSubmit = async (formEvent: FormEvent) => {
    formEvent.preventDefault();
    if (!event) return;
    setLoading(true);
    setMessage("");
    try {
      const updated = await updateAdminEvent(event);
      setEvent(updated);
      setMessage("Evento atualizado com sucesso.");
    } catch {
      setMessage("Erro ao salvar. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  const patch = (fields: Partial<EventSettings>) =>
    setEvent((cur) => (cur ? { ...cur, ...fields } : cur));

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Configurações</p>
          <h1>Evento</h1>
        </div>

        <form className="stack-form admin-form" onSubmit={onSubmit}>

          <div className="card">
            <h2>Dados principais</h2>
            <div className="stack-form">
              <div className="field">
                <label htmlFor="ev-name">Nome do evento</label>
                <input
                  id="ev-name"
                  type="text"
                  placeholder="Ex: MIÓ Festa do Mundo 2026"
                  value={event?.name || ""}
                  onChange={(e) => patch({ name: e.target.value })}
                />
              </div>

              <div className="field">
                <label htmlFor="ev-description">Descrição</label>
                <textarea
                  id="ev-description"
                  rows={4}
                  placeholder="Descrição pública do evento"
                  value={event?.description || ""}
                  onChange={(e) => patch({ description: e.target.value })}
                />
              </div>

              <div className="field">
                <label htmlFor="ev-date">Data e hora do evento</label>
                <input
                  id="ev-date"
                  type="datetime-local"
                  value={event?.event_date ? event.event_date.slice(0, 16) : ""}
                  onChange={(e) => patch({ event_date: e.target.value })}
                />
              </div>

              <div className="field">
                <label htmlFor="ev-location">Local</label>
                <input
                  id="ev-location"
                  type="text"
                  placeholder="Ex: Centro de Convenções Ulysses Guimarães"
                  value={event?.location || ""}
                  onChange={(e) => patch({ location: e.target.value })}
                />
              </div>
            </div>
          </div>

          <div className="card">
            <h2>Comercial</h2>
            <div className="stack-form">
              <div className="field">
                <label htmlFor="ev-price">Preço por ingresso (R$)</label>
                <input
                  id="ev-price"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0,00"
                  value={event?.price || ""}
                  onChange={(e) => patch({ price: e.target.value })}
                />
              </div>

              <div className="field">
                <label htmlFor="ev-sales-end">Encerramento das vendas</label>
                <input
                  id="ev-sales-end"
                  type="datetime-local"
                  value={event?.sales_end_at ? event.sales_end_at.slice(0, 16) : ""}
                  onChange={(e) => patch({ sales_end_at: e.target.value || null })}
                />
              </div>

              <div className="field">
                <label htmlFor="ev-capacity">Capacidade total</label>
                <input
                  id="ev-capacity"
                  type="number"
                  min="0"
                  placeholder="0"
                  value={event?.capacity_total || 0}
                  onChange={(e) => patch({ capacity_total: Number(e.target.value) })}
                />
              </div>

              <div className="field">
                <label htmlFor="ev-refund">Política de não reembolso</label>
                <textarea
                  id="ev-refund"
                  rows={4}
                  placeholder="Texto exibido no checkout e enviado ao comprador"
                  value={event?.no_refund_policy || ""}
                  onChange={(e) => patch({ no_refund_policy: e.target.value })}
                />
              </div>
            </div>
          </div>

          {message && (
            <div
              ref={messageRef}
              className={message.startsWith("Erro") ? "error-box" : "result-box"}
              role="status"
            >
              {message}
            </div>
          )}

          <button
            type="submit"
            className="button button-primary admin-save-button"
            disabled={loading}
          >
            {loading ? <><SpinnerIcon /> Salvando…</> : "Salvar evento"}
          </button>
        </form>
      </section>
    </AdminShell>
  );
}
