import Footer from "@/components/Footer";
import TopBar from "@/components/TopBar";

export const metadata = { title: "Analitik · PantauApi" };

export default function AnalyticsPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <TopBar />
      <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 pb-16 pt-28">
        <p className="field-label">Fase 5</p>
        <h1 className="font-display text-3xl font-bold">Analitik</h1>
        <p className="mt-2 max-w-xl text-sm text-text-muted">
          Insight utama, tren, ranking wilayah, pola musiman, faktor pengaruh, prediksi ML, dan
          validasi akan dibangun pada Fase 5 sesuai <code className="font-mono text-[11px]">docs/ANALYTICS_SPEC.md</code>.
        </p>
        <div className="mt-6 card max-w-xl p-5">
          <p className="text-sm font-semibold">Data harian siap dipakai</p>
          <p className="mt-1 text-sm text-text-muted">
            <code className="font-mono text-[11px]">agg_daily_province</code> dan
            <code className="ml-1 font-mono text-[11px]">agg_daily_grid</code> sudah dihasilkan
            <code className="ml-1 font-mono text-[11px]">aggregate.py</code> dan dilayani DuckDB.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}
