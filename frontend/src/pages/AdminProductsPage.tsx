import { FormEvent, useEffect, useState } from "react";
import AdminShell from "../components/AdminShell";
import { Product, createProduct, deleteProduct, getAdminProducts, updateProduct } from "../services/api";

function formatCurrency(value: string | number) {
  return Number(value || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function AdminProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    getAdminProducts(search)
      .then((response) => setProducts(response.results))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    const handle = setTimeout(load, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const resetForm = () => {
    setName("");
    setPrice("");
    setEditingId(null);
  };

  const startEdit = (product: Product) => {
    setEditingId(product.id);
    setName(product.name);
    setPrice(product.price);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !price) return;
    setSaving(true);
    setError("");
    try {
      if (editingId) {
        await updateProduct(editingId, { name: name.trim(), price });
      } else {
        await createProduct({ name: name.trim(), price });
      }
      resetForm();
      load();
    } catch {
      setError("Não foi possível salvar o produto.");
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async (product: Product) => {
    setBusyId(product.id);
    try {
      await updateProduct(product.id, { is_active: !product.is_active });
      load();
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (product: Product) => {
    setBusyId(product.id);
    setError("");
    try {
      await deleteProduct(product.id);
      load();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Não foi possível excluir este produto.");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <AdminShell>
      <section className="page admin-page">
        <div className="admin-page-header">
          <p className="admin-kicker">Cartões NFC</p>
          <h1>Produtos</h1>
        </div>

        <div className="card" style={{ maxWidth: "420px", marginBottom: "1.5rem" }}>
          <h2>{editingId ? "Editar produto" : "Novo produto"}</h2>
          <form className="stack-form" onSubmit={submit}>
            <div className="field">
              <label htmlFor="productName">Nome</label>
              <input
                id="productName"
                type="text"
                placeholder="Ex: Água"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="productPrice">Preço</label>
              <input
                id="productPrice"
                type="text"
                inputMode="decimal"
                placeholder="0,00"
                value={price}
                onChange={(e) => setPrice(e.target.value.replace(",", "."))}
              />
            </div>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button className="button button-primary" type="submit" disabled={saving || !name.trim() || !price}>
                {saving ? "Salvando…" : editingId ? "Salvar alterações" : "Adicionar produto"}
              </button>
              {editingId && (
                <button className="button button-secondary" type="button" onClick={resetForm}>
                  Cancelar
                </button>
              )}
            </div>
          </form>
        </div>

        {error && <div className="error-box" role="alert" style={{ marginBottom: "1rem" }}>{error}</div>}

        <div className="field" style={{ maxWidth: "320px", marginBottom: "1rem" }}>
          <input
            type="text"
            placeholder="Buscar por nome…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Preço</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr><td colSpan={4}>Carregando…</td></tr>
              )}
              {!loading && products.length === 0 && (
                <tr><td colSpan={4}>Nenhum produto cadastrado.</td></tr>
              )}
              {!loading && products.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{formatCurrency(p.price)}</td>
                  <td>
                    <span className={`status-badge ${p.is_active ? "paid" : "used"}`}>
                      {p.is_active ? "Ativo" : "Inativo"}
                    </span>
                  </td>
                  <td style={{ display: "flex", gap: "0.5rem" }}>
                    <button className="button button-secondary" onClick={() => startEdit(p)}>
                      Editar
                    </button>
                    <button
                      className="button button-secondary"
                      disabled={busyId === p.id}
                      onClick={() => toggleActive(p)}
                    >
                      {p.is_active ? "Desativar" : "Ativar"}
                    </button>
                    <button
                      className="button button-secondary"
                      disabled={busyId === p.id}
                      onClick={() => handleDelete(p)}
                    >
                      Excluir
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AdminShell>
  );
}
