import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const navGroups = [
  {
    label: "Operacional",
    items: [
      { to: "/admin", label: "Dashboard", end: true },
      { to: "/admin/pedidos", label: "Pedidos", end: false },
      { to: "/admin/cartoes", label: "Cartões", end: false },
      { to: "/admin/produtos", label: "Produtos", end: false },
    ],
  },
  {
    label: "Configurações",
    items: [{ to: "/admin/evento", label: "Evento", end: false }],
  },
];

function IconMenu() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="3" y1="6" x2="21" y2="6"/>
      <line x1="3" y1="12" x2="21" y2="12"/>
      <line x1="3" y1="18" x2="21" y2="18"/>
    </svg>
  );
}

function IconClose() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  );
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  // Fecha o drawer ao navegar
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  // Bloqueia scroll do body quando drawer está aberto
  useEffect(() => {
    document.body.style.overflow = mobileOpen ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [mobileOpen]);

  return (
    <div className="admin-shell">

      {/* Topbar mobile */}
      <div className="admin-mobile-topbar">
        <button
          className="admin-hamburger"
          onClick={() => setMobileOpen(true)}
          aria-label="Abrir menu"
          aria-expanded={mobileOpen}
        >
          <IconMenu />
        </button>
        <span className="admin-mobile-title">MIÓ Admin</span>
      </div>

      {/* Backdrop */}
      {mobileOpen && (
        <div
          className="admin-sidebar-backdrop"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside className={`admin-sidebar${mobileOpen ? " is-open" : ""}`}>
        <div className="admin-brand">
          <span className="admin-brand-mark">MIÓ</span>
          <div>
            <p className="admin-brand-title">Administrativo</p>
            <p className="admin-brand-subtitle">Festa do Mundo</p>
          </div>
          <button
            className="admin-sidebar-close"
            onClick={() => setMobileOpen(false)}
            aria-label="Fechar menu"
          >
            <IconClose />
          </button>
        </div>

        <nav className="admin-nav" aria-label="Menu administrativo">
          {navGroups.map((group) => (
            <div key={group.label} className="admin-nav-group">
              <p className="admin-nav-label">{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `admin-nav-link${isActive ? " is-active" : ""}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="admin-sidebar-footer">
          <button
            className="button button-secondary admin-sidebar-button"
            onClick={() => navigate("/")}
          >
            Voltar ao site
          </button>
          <button
            className="button button-primary admin-sidebar-button"
            onClick={() => { logout(); navigate("/admin/login"); }}
          >
            Sair
          </button>
        </div>
      </aside>

      <div className="admin-content">
        <div className="admin-content-inner">{children}</div>
      </div>
    </div>
  );
}
