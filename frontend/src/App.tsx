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

    const onVisible = () => { if (!document.hidden) loadPrices(); };
    document.addEventListener("visibilitychange", onVisible);

    const now = new Date();
    const target = new Date();
    target.setHours(20, 30, 0, 0);
    const eveningTimer = now < target
      ? setTimeout(loadPrices, target.getTime() - now.getTime())
      : undefined;

    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      clearTimeout(eveningTimer);
    };
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
    <div className="flex h-screen overflow-hidden">
      {/* Main panel */}
      <div className="flex-1 overflow-y-auto p-8 space-y-6 max-w-4xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tu factura de luz</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Analiza tus facturas de electricidad españolas y compáralas con el PVPC.
          </p>
        </div>

        <PriceChart data={prices} error={pricesError} />

        <UploadPanel onFile={handleFile} loading={analyzing} />

        {analysisError && (
          <p className="text-sm text-destructive">{analysisError}</p>
        )}

        {analysis && <ResultsPanel data={analysis} />}

        <footer className="text-xs text-muted-foreground text-center pt-4 pb-2 border-t">
          <a href="https://raulrc.com" target="_blank" rel="noopener noreferrer" className="hover:underline">raulrc.com</a>
        </footer>
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
