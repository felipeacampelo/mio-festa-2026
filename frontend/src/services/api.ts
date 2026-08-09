import axios from "axios";

export type EventSettings = {
  id: number;
  name: string;
  description: string;
  event_date: string;
  location: string;
  price: string;
  sales_end_at: string | null;
  capacity_total: number;
  no_refund_policy: string;
  sales_status: string;
};

export type Ticket = {
  id: number;
  ticket_code: string;
  participant_name: string;
  participant_email: string;
  status: string;
  checked_in_at: string | null;
  qr_code_data_url: string | null;
};

export type Payment = {
  id: number;
  external_id: string;
  method: string;
  status: string;
  checkout_url: string;
  pix_copy_paste: string;
  pix_qr_code: string;
};

export type Order = {
  id: number;
  public_id: string;
  order_code: string;
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  buyer_document: string;
  quantity: number;
  unit_price: string;
  total_amount: string;
  accepted_no_refund: boolean;
  payment_method: string;
  status: string;
  paid_at: string | null;
  created_at: string;
  access_token?: string;
  tickets: Ticket[];
  payment?: Payment;
};

export type PaginatedResponse<T> = {
  count: number;
  page: number;
  page_size: number;
  results: T[];
};

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common.Authorization = `Token ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
}

// Instancia separada para o login de vendedor/caixa/check-in: evita que a
// sessao de admin e a de vendedor disputem o mesmo header Authorization
// quando as duas ficam montadas na mesma aba, e permite reagir a 401/403
// (token expirado, vendedor desativado no meio do turno) sem misturar com
// a logica de auth do admin.
const vendorApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000/api",
});

export function setVendorAuthToken(token: string | null) {
  if (token) {
    vendorApi.defaults.headers.common.Authorization = `Token ${token}`;
  } else {
    delete vendorApi.defaults.headers.common.Authorization;
  }
}

let onVendorUnauthorized: (() => void) | null = null;

export function setVendorUnauthorizedHandler(handler: (() => void) | null) {
  onVendorUnauthorized = handler;
}

vendorApi.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 || status === 403) {
      onVendorUnauthorized?.();
    }
    return Promise.reject(error);
  }
);

export async function getEvent() {
  const response = await api.get<EventSettings>("/events/current/");
  return response.data;
}

export async function getAdminEvent() {
  const response = await api.get<EventSettings>("/events/admin/current/");
  return response.data;
}

export async function updateAdminEvent(payload: EventSettings) {
  const response = await api.put<EventSettings>("/events/admin/current/", payload);
  return response.data;
}

export async function createOrder(payload: {
  buyer_name: string;
  buyer_email: string;
  buyer_phone: string;
  buyer_document: string;
  payment_method: "pix" | "credit_card";
  accepted_no_refund: boolean;
  participants: Array<{
    participant_name: string;
    participant_email: string;
    is_child?: boolean;
    participant_document?: string;
    participant_birth_date?: string;
  }>;
}) {
  const response = await api.post<Order>("/orders/checkout/", payload);
  return response.data;
}

export async function createCourtesyOrder(payload: { participant_name: string; participant_email?: string }) {
  const response = await api.post<Order>("/orders/admin/courtesy/", payload);
  return response.data;
}

export async function lookupOrder(publicId: string, buyerEmail: string) {
  const response = await api.post<Order>("/orders/lookup/", { public_id: publicId, buyer_email: buyerEmail });
  return response.data;
}

export async function getOrder(publicId: string, accessToken: string) {
  const response = await api.get<Order>(`/orders/${publicId}/`, { params: { access_token: accessToken } });
  return response.data;
}

export async function loginAdmin(username: string, password: string) {
  const response = await api.post<{ token: string }>("/auth/login/", { username, password });
  return response.data;
}

export async function adminMe() {
  const response = await api.get("/auth/me/");
  return response.data;
}

export async function getAdminStats() {
  const response = await api.get<{
    total_orders: number;
    paid_orders: number;
    revenue: number;
    total_tickets: number;
    active_tickets: number;
    used_tickets: number;
  }>("/admin/stats/");
  return response.data;
}

export async function getAdminOrders(search = "", page = 1, pageSize = 50) {
  const response = await api.get<PaginatedResponse<Order>>("/admin/orders/", {
    params: { search, page, page_size: pageSize },
  });
  return response.data;
}

export async function getAdminTickets(search = "", page = 1, pageSize = 50) {
  const response = await api.get<PaginatedResponse<any>>("/admin/tickets/", {
    params: { search, page, page_size: pageSize },
  });
  return response.data;
}

export async function resendTickets(orderId: number) {
  await api.post(`/admin/orders/${orderId}/resend-tickets/`);
}

export async function syncOrderPayment(orderId: number) {
  const response = await api.post(`/payments/admin/orders/${orderId}/sync/`);
  return response.data;
}

export async function editTicket(ticketId: number, payload: { participant_name: string; participant_email: string }) {
  const response = await api.patch(`/admin/tickets/${ticketId}/`, payload);
  return response.data;
}

export async function transferTicket(ticketId: number, payload: { participant_name: string; participant_email: string }) {
  const response = await api.post(`/admin/tickets/${ticketId}/transfer/`, payload);
  return response.data;
}

export async function undoCheckin(ticketId: number) {
  const response = await api.post(`/admin/tickets/${ticketId}/undo-checkin/`);
  return response.data;
}

export async function scanCheckin(qrToken: string) {
  const response = await vendorApi.post("/checkin/scan/", { qr_token: qrToken });
  return response.data;
}

export async function manualCheckin(ticketCode: string) {
  const response = await vendorApi.post("/checkin/manual/", { ticket_code: ticketCode });
  return response.data;
}

export async function syncPendingPayments() {
  const response = await vendorApi.post<{ ok: boolean; checked: number; confirmed: number }>(
    "/payments/vendor/sync-pending/"
  );
  return response.data;
}

export type Vendor = {
  id: number;
  display_name: string;
  role: "seller" | "recharge" | "checkin";
  is_active?: boolean;
};

export type Card = {
  uid: string;
  status: "active" | "blocked" | "returned";
  balance: string;
  linked_at: string | null;
  participant_name: string | null;
  is_child: boolean | null;
};

export type CardTransactionItem = {
  product_name: string;
  unit_price: string;
  quantity: number;
};

export type CardResult = {
  result:
    | "ok"
    | "insufficient_balance"
    | "card_blocked"
    | "card_returned"
    | "not_linked"
    | "already_linked"
    | "ticket_already_has_card"
    | "ticket_not_found"
    | "ticket_not_eligible"
    | "card_not_found"
    | "invalid_amount";
  card?: Card;
  items?: CardTransactionItem[];
};

export type TicketSearchResult = {
  id: number;
  ticket_code: string;
  participant_name: string;
  participant_document: string;
  is_child: boolean;
  order_buyer_name: string;
  has_card: boolean;
  purchased_on_event_day: boolean;
};

export type AdminCard = {
  id: number;
  uid: string;
  status: "active" | "blocked" | "returned";
  balance: string;
  linked_at: string | null;
  participant_name: string | null;
  created_at: string;
};

export type CardReconciliation = {
  recharge_by_vendor: Array<{ vendor_id: number | null; vendor__display_name: string | null; total: string }>;
  sold_by_vendor: Array<{ vendor_id: number | null; vendor__display_name: string | null; total: string }>;
  outstanding_balance: string;
  status_counts: Record<string, number>;
};

export type Product = {
  id: number;
  vendor: number;
  vendor_name: string;
  name: string;
  price: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

export type SellerOption = {
  id: number;
  display_name: string;
  is_active: boolean;
};

export type CartItem = { product_id: number; quantity: number };

export async function vendorLogin(username: string, password: string) {
  const response = await vendorApi.post<{ token: string; vendor: Vendor }>("/cards/login/", { username, password });
  return response.data;
}

export async function vendorMe() {
  const response = await vendorApi.get<Vendor>("/cards/me/");
  return response.data;
}

export async function getCard(uid: string) {
  const response = await vendorApi.get<Card>(`/cards/${encodeURIComponent(uid)}/`);
  return response.data;
}

export async function searchTickets(query: string) {
  const response = await vendorApi.get<TicketSearchResult[]>("/cards/search-tickets/", { params: { q: query } });
  return response.data;
}

export async function linkCard(uid: string, ticketId: number) {
  const response = await vendorApi.post<CardResult>(`/cards/${encodeURIComponent(uid)}/link/`, {
    ticket_id: ticketId,
  });
  return response.data;
}

export async function debitCard(uid: string, amount: string, idempotencyKey: string, note?: string) {
  const response = await vendorApi.post<CardResult>(`/cards/${encodeURIComponent(uid)}/debit/`, {
    amount,
    idempotency_key: idempotencyKey,
    note,
  });
  return response.data;
}

export async function getProducts() {
  const response = await vendorApi.get<Product[]>("/cards/products/");
  return response.data;
}

export async function debitCardCart(uid: string, items: CartItem[], idempotencyKey: string, note?: string) {
  const response = await vendorApi.post<CardResult>(`/cards/${encodeURIComponent(uid)}/debit/`, {
    items,
    idempotency_key: idempotencyKey,
    note,
  });
  return response.data;
}

export async function creditCard(uid: string, amount: string, idempotencyKey: string, note?: string) {
  const response = await vendorApi.post<CardResult>(`/cards/${encodeURIComponent(uid)}/credit/`, {
    amount,
    idempotency_key: idempotencyKey,
    note,
  });
  return response.data;
}

export async function getAdminCards(search = "", page = 1, pageSize = 50, excludeReturned = false) {
  const response = await api.get<PaginatedResponse<AdminCard>>("/admin/cards/", {
    params: { search, page, page_size: pageSize, exclude_returned: excludeReturned ? "true" : undefined },
  });
  return response.data;
}

export async function getCardReconciliation() {
  const response = await api.get<CardReconciliation>("/admin/cards/reconciliation/");
  return response.data;
}

export async function blockCard(uid: string) {
  const response = await api.post<AdminCard>(`/admin/cards/${encodeURIComponent(uid)}/block/`);
  return response.data;
}

export async function unblockCard(uid: string) {
  const response = await api.post<AdminCard>(`/admin/cards/${encodeURIComponent(uid)}/unblock/`);
  return response.data;
}

export async function returnCard(uid: string) {
  const response = await api.post<AdminCard>(`/admin/cards/${encodeURIComponent(uid)}/return/`);
  return response.data;
}

export async function getAdminProducts(search = "", page = 1, pageSize = 50) {
  const response = await api.get<PaginatedResponse<Product>>("/admin/products/", {
    params: { search, page, page_size: pageSize },
  });
  return response.data;
}

export async function getAdminSellers() {
  const response = await api.get<SellerOption[]>("/admin/cards/sellers/");
  return response.data;
}

export async function getAdminVendors() {
  const response = await api.get<Vendor[]>("/admin/cards/vendors/");
  return response.data;
}

export async function impersonateVendor(vendorId: number) {
  const response = await api.post<{ token: string; vendor: Vendor }>(`/admin/cards/vendors/${vendorId}/impersonate/`);
  return response.data;
}

export async function createProduct(data: { name: string; price: string; vendor: number }) {
  const response = await api.post<Product>("/admin/products/", data);
  return response.data;
}

export async function updateProduct(
  id: number,
  data: Partial<{ name: string; price: string; is_active: boolean; vendor: number }>,
) {
  const response = await api.patch<Product>(`/admin/products/${id}/`, data);
  return response.data;
}

export async function deleteProduct(id: number) {
  await api.delete(`/admin/products/${id}/`);
}
