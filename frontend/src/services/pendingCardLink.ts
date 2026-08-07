const STORAGE_KEY = "pending_card_link";
const EXPIRY_MS = 3 * 60 * 1000; // 3 minutos

export type PendingCardLink = {
  ticketId: number;
  participantName: string;
  timestamp: number;
};

export function setPendingCardLink(ticketId: number, participantName: string) {
  const value: PendingCardLink = { ticketId, participantName, timestamp: Date.now() };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
}

export function getPendingCardLink(): PendingCardLink | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed: PendingCardLink = JSON.parse(raw);
    if (Date.now() - parsed.timestamp > EXPIRY_MS) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function clearPendingCardLink() {
  localStorage.removeItem(STORAGE_KEY);
}
