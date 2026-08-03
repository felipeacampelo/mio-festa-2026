export default function VendorShell({
  vendor,
  onLogout,
  children,
}: {
  vendor: { display_name: string; role: string } | null;
  onLogout: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="app-shell">
      <header className="topbar">
        <span className="brand-text">{vendor?.display_name || "Caixa"}</span>
        <button className="button button-secondary" onClick={onLogout}>
          Sair
        </button>
      </header>
      <main>
        <section className="page narrow">{children}</section>
      </main>
    </div>
  );
}
