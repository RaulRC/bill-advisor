import { useCallback, useEffect, useState } from "react";

import { type AnalyzeResponse, type PricesResponse, analyzePDF, chat, fetchPrices } from "./api";
import { ChatPanel } from "./ChatPanel";
import { PriceChart } from "./PriceChart";
import { ResultsPanel } from "./ResultsPanel";
import { UploadPanel } from "./UploadPanel";

type Message = { role: "user" | "assistant"; content: string };

export function App() {
  const [prices, setPrices] = useState<PricesResponse | null>(null);
  const [pricesError, setPricesError] = useState<string | null>(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [chatMessages, setChatMessages] = useState<Message[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);

  // ── Prices ──────────────────────────────────────────────────────────────

  const loadPrices = useCallback(async () => {
    try {
      setPricesError(null);
      setPrices(await fetchPrices());
    } catch (e) {
      setPricesError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    loadPrices();
    const id = setInterval(loadPrices, 300_000);
    return () => clearInterval(id);
  }, [loadPrices]);

  // ── Analysis ─────────────────────────────────────────────────────────────

  const handleFile = useCallback(async (file: File) => {
    setAnalyzing(true);
    setAnalysisError(null);
    setAnalysis(null);
    try {
      setAnalysis(await analyzePDF(file));
    } catch (e) {
      setAnalysisError((e as Error).message);
    } finally {
      setAnalyzing(false);
    }
  }, []);

  // ── Chat ─────────────────────────────────────────────────────────────────

  const handleChat = useCallback(
    async (text: string) => {
      const userMsg: Message = { role: "user", content: text };
      setChatMessages((prev) => [...prev, userMsg]);
      setChatLoading(true);
      try {
        const res = await chat({
          messages: [...chatMessages, userMsg].map((m) => ({
            role: m.role,
            content: m.content,
          })),
          factura: analysis?.factura ?? null,
          prices,
        });
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.answer },
        ]);
      } catch {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Lo siento, hubo un error." },
        ]);
      } finally {
        setChatLoading(false);
      }
    },
    [chatMessages, analysis, prices],
  );

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* Main panel */}
      <div style={{ flex: 1, overflowY: "auto", padding: 32 }}>
        <h1 style={{ margin: "0 0 4px", fontSize: 22, fontWeight: 700 }}>
          Bill Advisor
        </h1>
        <p style={{ margin: "0 0 24px", fontSize: 14, color: "#888" }}>
          Analiza tus facturas de electricidad españolas y compáralas con el PVPC.
        </p>

        <PriceChart data={prices} error={pricesError} />

        <div style={{ marginTop: 24 }}>
          <UploadPanel onFile={handleFile} loading={analyzing} />
        </div>

        {analysisError && (
          <p style={{ color: "#b91c1c", fontSize: 14, marginTop: 12 }}>
            {analysisError}
          </p>
        )}

        {analysis && (
          <div style={{ marginTop: 24 }}>
            <ResultsPanel data={analysis} />
          </div>
        )}
      </div>

      {/* Chat sidebar */}
      <ChatPanel
        messages={chatMessages}
        onSend={handleChat}
        loading={chatLoading}
        collapsed={chatCollapsed}
        onToggle={() => setChatCollapsed((c) => !c)}
      />
    </div>
  );
}
