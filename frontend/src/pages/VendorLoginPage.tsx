import { FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useVendorAuth } from "../contexts/VendorAuthContext";

export default function VendorLoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { login } = useVendorAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const vendor = await login(username, password);
      const next = searchParams.get("next");
      const fallback = vendor.role === "checkin" ? "/caixa/checkin" : "/caixa";
      navigate(next || fallback, { replace: true });
    } catch {
      setError("Usuário ou senha inválidos. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <main>
        <section className="page narrow">
          <div className="page-header">
            <h1>Caixa do evento</h1>
            <p>Login de vendedor ou caixa de recarga.</p>
          </div>

          <form className="stack-form" onSubmit={submit} noValidate>
            <div className="card">
              <div className="stack-form">
                <div className="field">
                  <label htmlFor="vendorUser">
                    Usuário <span className="req" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="vendorUser"
                    type="text"
                    placeholder="nome de usuário"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                    autoFocus
                    required
                  />
                </div>

                <div className="field">
                  <label htmlFor="vendorPass">
                    Senha <span className="req" aria-hidden="true">*</span>
                  </label>
                  <input
                    id="vendorPass"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                  />
                </div>
              </div>
            </div>

            {error && <div className="error-box" role="alert">{error}</div>}

            <button
              type="submit"
              className="button button-primary"
              disabled={loading}
              style={{ width: "100%", padding: "1rem" }}
            >
              {loading ? "Entrando…" : "Entrar"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
