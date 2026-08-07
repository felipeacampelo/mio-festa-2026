import { useState } from "react";
import { useNavigate } from "react-router-dom";
import VendorShell from "../components/VendorShell";
import { useVendorAuth } from "../contexts/VendorAuthContext";
import { useQrScanner } from "../hooks/useQrScanner";
import { manualCheckin, scanCheckin } from "../services/api";
import { setPendingCardLink } from "../services/pendingCardLink";

function SpinnerIcon() {
  return (
    <svg className="spinner" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" width="16" height="16" aria-hidden="true">
      <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
      <path d="M12 2a10 10 0 0 1 10 10" />
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
      <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  );
}

function IconX() {
  return (
    <svg width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="10"/>
      <line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
    </svg>
  );
}

export default function VendorCheckinPage() {
  const navigate = useNavigate();
  const { vendor, logout } = useVendorAuth();
  const [ticketCode, setTicketCode] = useState("");
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [manualLoading, setManualLoading] = useState(false);

  const handleResult = (response: any) => {
    setResult(response);
    stopCamera();
    // "blocked" significa ingresso pendente/cancelado - nao guarda sugestao
    // de vinculo pra isso. "confirmed" e "already_checked_in" sao pessoas
    // de verdade que podem precisar de cartao.
    if (response?.result !== "blocked" && response?.participant?.ticket_id) {
      setPendingCardLink(response.participant.ticket_id, response.participant.name);
    }
  };

  const { videoRef, scanning, cameraError, startCamera, stopCamera } = useQrScanner(async (data) => {
    try {
      const response = await scanCheckin(data);
      handleResult(response);
    } catch {
      setError("Erro ao validar QR code. Tente o código manual.");
      stopCamera();
    }
  });

  const resetCheckin = () => {
    setResult(null);
    setError("");
    setTicketCode("");
  };

  const handleManual = async () => {
    if (!ticketCode.trim()) return;
    setManualLoading(true);
    setError("");
    try {
      const response = await manualCheckin(ticketCode.trim());
      handleResult(response);
    } catch {
      setError("Código inválido ou erro de comunicação.");
    } finally {
      setManualLoading(false);
    }
  };

  const isSuccess = (r: any) => r?.result === "confirmed";

  return (
    <VendorShell vendor={vendor} onLogout={logout}>
      {result && (
        <div className={`checkin-result ${isSuccess(result) ? "checkin-success" : "checkin-fail"}`}>
          <div className="checkin-result-icon">
            {isSuccess(result) ? <IconCheck /> : <IconX />}
          </div>
          <p className="checkin-result-status">
            {isSuccess(result) ? "LIBERADO" : "NEGADO"}
          </p>
          <p className="checkin-result-name">{result.participant?.name}</p>
          {result.participant?.ticket_code && (
            <p className="checkin-result-code">{result.participant.ticket_code}</p>
          )}
          {!isSuccess(result) && result.result && (
            <p className="checkin-result-reason">{result.result}</p>
          )}
          {result.result !== "blocked" && (
            <p className="checkin-result-reason">Agora peça para a pessoa tocar o cartão no celular.</p>
          )}
          <button className="button checkin-next-btn" onClick={resetCheckin}>
            Próximo
          </button>
        </div>
      )}

      {!result && (
        <>
          <div className="card">
            <h2>Câmera</h2>
            <div className="camera-wrap">
              <video
                ref={videoRef}
                className="camera-preview"
                muted
                playsInline
                aria-label="Câmera para leitura de QR Code"
              />
              {scanning && <div className="camera-scanning-indicator" aria-hidden="true" />}
            </div>
            {!scanning ? (
              <button className="button button-primary" onClick={startCamera}>
                Iniciar leitura
              </button>
            ) : (
              <button className="button button-secondary" onClick={stopCamera}>
                Parar câmera
              </button>
            )}
            {cameraError && <div className="error-box" role="alert">{cameraError}</div>}
          </div>

          <div className="card">
            <h2>Digitar código</h2>
            <div className="stack-form">
              <div className="field">
                <label htmlFor="manual-code">Código do ingresso</label>
                <input
                  id="manual-code"
                  type="text"
                  placeholder="Ex: TKT-XXXXXX"
                  value={ticketCode}
                  onChange={(e) => setTicketCode(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleManual(); }}
                  autoCapitalize="characters"
                />
              </div>
              <button
                className="button button-primary"
                onClick={handleManual}
                disabled={manualLoading || !ticketCode.trim()}
              >
                {manualLoading ? <><SpinnerIcon /> Validando…</> : "Validar ingresso"}
              </button>
              <button className="button button-secondary" type="button" onClick={() => navigate("/caixa")}>
                Voltar
              </button>
              {error && (
                <div className="error-box" role="alert">{error}</div>
              )}
            </div>
          </div>
        </>
      )}
    </VendorShell>
  );
}
