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
  payment_method: "pix" | "credit_card";
  accepted_no_refund: boolean;
  participants: Array<{ participant_name: string; participant_email: string }>;
}) {
  const response = await api.post<Order>("/orders/checkout/", payload);
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

export async function getAdminOrders(search = "") {
  const response = await api.get<Order[]>("/admin/orders/", { params: { search } });
  return response.data;
}

export async function getAdminTickets(search = "") {
  const response = await api.get<any[]>("/admin/tickets/", { params: { search } });
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

export async function scanCheckin(qrToken: string) {
  const response = await api.post("/checkin/scan/", { qr_token: qrToken });
  return response.data;
}

export async function manualCheckin(ticketCode: string) {
  const response = await api.post("/checkin/manual/", { ticket_code: ticketCode });
  return response.data;
}
