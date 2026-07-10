import { Link } from "react-router-dom";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand" aria-label="MIÓ Festa do Mundo — Página inicial">
          <span className="brand-mark">MIÓ</span>
          <span className="brand-text">Festa do<br />Mundo 2026</span>
        </Link>
        <nav className="topnav" aria-label="Navegação principal">
          <Link to="/checkout">Comprar ingressos</Link>
          <Link to="/pedido">Consultar pedido</Link>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
