import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import { lookupOrder } from "../services/api";

export default function OrderLookupPage() {
  const navigate = useNavigate();
  const [publicId, setPublicId] = useState("");
  const [buyerEmail, setBuyerEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const order = await lookupOrder(publicId, buyerEmail);
      navigate(`/pedido/${order.public_id}?access_token=${order.access_token}`);
    } catch {
      setError("Pedido não encontrado. Verifique o código e o e-mail informados.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <section className="page narrow">
        <div className="page-header">
          <h1>Consultar pedido</h1>
          <p>Informe o código do pedido e o e-mail usado na compra para localizar seus ingressos.</p>
        </div>

        <form className="stack-form" onSubmit={submit} noValidate>
          <div className="card">
            <div className="stack-form">
              <div className="field">
                <label htmlFor="publicId">
                  Código do pedido <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="publicId"
                  type="text"
                  placeholder="Ex: MIO-ABCD1234"
                  value={publicId}
                  onChange={(e) => setPublicId(e.target.value)}
                  autoCapitalize="characters"
                  required
                />
              </div>

              <div className="field">
                <label htmlFor="lookupEmail">
                  E-mail do comprador <span className="req" aria-hidden="true">*</span>
                </label>
                <input
                  id="lookupEmail"
                  type="email"
                  placeholder="Ex: maria@email.com"
                  value={buyerEmail}
                  onChange={(e) => setBuyerEmail(e.target.value)}
                  autoComplete="email"
                  inputMode="email"
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
            {loading ? "Consultando…" : "Consultar pedido"}
          </button>
        </form>
      </section>
    </Layout>
  );
}
