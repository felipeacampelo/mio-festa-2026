import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { EventSettings, getEvent } from "../services/api";
import heroImg from "../assets/hero-bg.png";
import logoImg from "../assets/logo_mio_festa.png";

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

function formatDateParts(dateStr: string) {
  try {
    const d = new Date(dateStr);
    return {
      day: d.toLocaleDateString("pt-BR", { day: "2-digit" }),
      month: d.toLocaleDateString("pt-BR", { month: "long" }),
      year: d.getFullYear(),
      weekday: d.toLocaleDateString("pt-BR", { weekday: "long" }),
      time: d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }),
    };
  } catch {
    return null;
  }
}

function formatPrice(price: string | number) {
  return Number(price).toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
  });
}

export default function HomePage() {
  const [event, setEvent] = useState<EventSettings | null>(null);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    getEvent().then(setEvent);
    const onScroll = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const salesOpen = !event || event.sales_status === "open";

  return (
    <div className="landing-shell">
      {/* Header — transparente → navy ao rolar */}
      <header className={`topbar topbar-float${scrolled ? " topbar-scrolled" : ""}`}>
        <Link to="/" className="brand" aria-label="MIÓ Festa do Mundo — Página inicial">
          <span className="brand-mark">MIÓ</span>
          <span className="brand-text">Festa do<br />Mundo 2026</span>
        </Link>
        <nav className="topnav" aria-label="Navegação principal">
          {salesOpen && <Link to="/checkout">Comprar ingressos</Link>}
          <Link to="/pedido">Consultar pedido</Link>
        </nav>
      </header>

      {/* Hero full-screen */}
      <section className="hero-full" aria-label="MIÓ Festa do Mundo 2026">
        {/* Imagem decorativa como fundo (texto acessível está no overlay abaixo) */}
        <img
          src={heroImg}
          alt=""
          role="presentation"
          className="hero-full-bg"
        />

        {/* Overlay escuro para garantir contraste WCAG 4.5:1 no texto */}
        <div className="hero-overlay" aria-hidden="true" />

        {/* Conteúdo do hero */}
        <div className="hero-content">
          <img
            src={logoImg}
            alt="MIÓ Festa do Mundo 2026"
            className="hero-logo"
          />

          {/* Chips de data e local */}
          {(event?.event_date || event?.location) && (
            <div className="hero-chips" role="list">
              {event.event_date && (
                <span className="hero-chip" role="listitem">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                  {formatDateShort(event.event_date)}
                </span>
              )}
              {event.location && (
                <span className="hero-chip" role="listitem">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                  </svg>
                  {event.location}
                </span>
              )}
            </div>
          )}

          {/* CTAs */}
          <div className="hero-ctas">
            {salesOpen && (
              <Link to="/checkout" className="button hero-btn-primary">
                Comprar ingresso
              </Link>
            )}
            <Link to="/pedido" className="button hero-btn-ghost">
              Consultar pedido
            </Link>
          </div>
        </div>

        {/* Scroll hint */}
        <div className="scroll-hint" aria-hidden="true">
          <span className="scroll-hint-label">Ver detalhes</span>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </section>

      {/* Seção de detalhes — abaixo do fold */}
      <section className="info-section" aria-label="Detalhes do evento">
        <div className="info-section-inner">

          {event?.event_date && (() => {
            const dp = formatDateParts(event.event_date);
            return (
              <div className="info-card">
                <div className="info-card-icon-wrap" aria-hidden="true">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
                  </svg>
                </div>
                <div className="info-card-text">
                  <span className="info-label">Quando</span>
                  {dp ? (
                    <div className="info-date">
                      <span className="info-date-day">{dp.day}</span>
                      <div className="info-date-right">
                        <span className="info-date-month">{dp.month} {dp.year}</span>
                        <span className="info-date-meta">{dp.weekday} · {dp.time}</span>
                      </div>
                    </div>
                  ) : (
                    <span className="info-value">{event.event_date}</span>
                  )}
                </div>
              </div>
            );
          })()}

          {event?.location && (
            <div className="info-card">
              <div className="info-card-icon-wrap" aria-hidden="true">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>
                </svg>
              </div>
              <div className="info-card-text">
                <span className="info-label">Onde</span>
                <span className="info-value">{event.location}</span>
              </div>
            </div>
          )}

          <div className="info-card info-card-cta">
            <div className="info-card-icon-wrap" aria-hidden="true">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2z"/>
              </svg>
            </div>
            <div className="info-card-text">
              <span className="info-label">Ingressos</span>
              {event?.price && (
                <span className="info-value info-price">{formatPrice(event.price)}</span>
              )}
              <span className="info-status">
                {event
                  ? event.sales_status === "open" ? "Vendas abertas" : "Vendas encerradas"
                  : "Carregando…"}
              </span>
              {salesOpen && (
                <Link to="/checkout" className="info-cta-btn">
                  Garantir meu lugar
                </Link>
              )}
            </div>
          </div>

        </div>

      </section>

      <footer className="site-footer">
        <div className="footer-inner">
          <div className="footer-brand">
            <span className="footer-mark">MIÓ</span>
            <span className="footer-tagline">Festa do Mundo 2026</span>
          </div>

          <nav className="footer-nav" aria-label="Links rápidos">
            {salesOpen && <Link to="/checkout">Comprar ingresso</Link>}
            <Link to="/pedido">Consultar pedido</Link>
          </nav>

          <p className="footer-copy">
            © 2026 Igreja Batista Capital
          </p>
        </div>
      </footer>
    </div>
  );
}
