import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { useAuth } from "../contexts/AuthContext";

export default function AdminLoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
      navigate("/admin/pedidos");
    } catch {
      setError("Usuário ou senha inválidos. Tente novamente.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <section className="page narrow">
        <div className="page-header">
          <h1>Área administrativa</h1>
          <p>Acesso restrito aos organizadores do evento.</p>
        </div>

        <form className="stack-form" onSubmit={submit} noValidate>
          <div className="card">
            <div className="stack-form">
              <div className="field">
                <label htmlFor="adminUser">
                  Usuário <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="adminUser"
                  type="text"
                  placeholder="nome de usuário"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="adminPass">
                  Senha <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="adminPass"
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
    </Layout>
  );
}
