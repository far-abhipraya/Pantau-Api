"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import EChart from "@/components/charts/EChart";
import SectionCard from "@/components/analytics/SectionCard";
import type {
  AnalyticsModel,
  ModelMetric,
  ValidationCompare,
  ValidationSummary,
  WeatherCorrelation,
} from "@/lib/api";
import { formatDate, formatDateTimeWib, formatNumber } from "@/lib/format";
import { CloudSun, FlaskConical, Info, Upload } from "lucide-react";

const FAKTOR_ROWS = [
  { id: "FP1", label: "Korelasi lag curah hujan / hari kering", status: "Menunggu data cuaca" },
  { id: "FP2", label: "Kurva dosis-respons hari tanpa hujan", status: "Menunggu data cuaca" },
  { id: "FP3", label: "Anomali cuaca periode berjalan", status: "Menunggu data cuaca" },
  { id: "FP4", label: "Penjelas wilayah (faktor pendorong)", status: "Menunggu model (Fase 6)" },
  { id: "FP5", label: "Pembanding antar tahun", status: "Tersedia di Ringkasan" },
  { id: "FP6", label: "Feature importance model", status: "Menunggu model (Fase 6)" },
];

export function FaktorSection({ modelAvailable = false }: { modelAvailable?: boolean }) {
  const rows = FAKTOR_ROWS.map((row) =>
    modelAvailable && (row.id === "FP4" || row.id === "FP6")
      ? { ...row, status: "Tersedia di Prediksi ML" }
      : row,
  );
  return (
    <SectionCard
      id="faktor"
      className="scroll-mt-36"
      title="Faktor di masa lalu yang berkaitan dengan kejadian hari ini"
      description="Diagnostik asosiasi membutuhkan data cuaca dan fitur turunan; feature importance model tersedia di seksi Prediksi ML."
    >
      <ul className="divide-y divide-border text-xs">
        {rows.map((row) => (
          <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-text-subtle">{row.id}</span>
              <span className="text-text">{row.label}</span>
            </span>
            {row.status === "Tersedia di Ringkasan" ? (
              <a href="#ringkasan" className="text-[11px] font-medium text-fire-deep-orange hover:underline">
                Lihat grafik kumulatif tahunan
              </a>
            ) : row.status === "Tersedia di Prediksi ML" ? (
              <a href="#prediksi" className="text-[11px] font-medium text-fire-deep-orange hover:underline">
                Lihat feature importance
              </a>
            ) : (
              <Badge tone="muted">{row.status}</Badge>
            )}
          </li>
        ))}
      </ul>
      <MethodologyNote />
    </SectionCard>
  );
}

export function MethodologyNote() {
  return (
    <div className="mt-3 flex items-start gap-2 rounded-lg border border-border bg-surface-muted/60 px-3 py-2 text-[11px] leading-relaxed text-text-muted">
      <Info className="mt-0.5 size-3.5 shrink-0 text-text-subtle" aria-hidden />
      <p>
        <strong className="text-text">Catatan metodologi:</strong> asosiasi bukan sebab-akibat. Hotspot
        adalah indikasi anomali suhu dari satelit, bukan kepastian kebakaran; awan dapat menutupi
        deteksi; data cuaca beresolusi kasar; hasil sensitif terhadap pemilihan wilayah dan periode.
      </p>
    </div>
  );
}

export function CuacaSection({
  weather,
  loading,
  error,
}: {
  weather: WeatherCorrelation | null;
  loading: boolean;
  error?: string | null;
}) {
  const unavailable = weather && !weather.available;
  return (
    <SectionCard
      id="cuaca"
      title="Cuaca dan hotspot"
      description="Korelasi curah hujan/suhu dengan hotspot serta hari kering berturut-turut."
      loading={loading && !weather}
      error={error}
      empty={!loading && !weather}
      emptyHint="Status data cuaca tidak tersedia."
    >
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border bg-surface-muted/50 px-4 py-8 text-center">
        <CloudSun className="size-6 text-weather-teal" aria-hidden />
        <p className="text-sm font-medium text-text">Data cuaca belum lengkap</p>
        <p className="max-w-xl text-xs text-text-muted">
          {unavailable ? weather?.reason : "Endpoint cuaca tidak mengembalikan data."}
        </p>
        {unavailable && weather?.needs?.length ? (
          <ul className="mt-1 list-disc space-y-0.5 pl-5 text-left text-[11px] text-text-subtle">
            {weather.needs.map((need) => (
              <li key={need}>{need}</li>
            ))}
          </ul>
        ) : null}
        <p className="mt-1 text-[11px] text-text-subtle">
          Grafik dua sumbu dan scatter korelasi akan tampil otomatis setelah data cuaca masuk ke
          serving layer (Fase 6).
        </p>
      </div>
    </SectionCard>
  );
}

export function PrediksiSection({
  model,
  loading,
  error,
  onRefresh,
}: {
  model: AnalyticsModel | null;
  loading: boolean;
  error?: string | null;
  onRefresh: () => Promise<void>;
}) {
  const [refreshing, setRefreshing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    setRefreshing(true);
    setNotice(null);
    try {
      await onRefresh();
      setNotice("Job fitur + latih + prediksi diantrekan. Muat ulang halaman setelah job selesai.");
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Gagal menjalankan job model.");
    } finally {
      setRefreshing(false);
    }
  }

  const metrics = model?.metrics;
  const risk = model?.risk;
  const topGrids = risk?.top_grids ?? [];
  const importance = (model?.feature_importance ?? []).slice(0, 10);
  const maxImportance = importance[0]?.value || 1;
  const categories = risk?.categories ?? {};

  return (
    <section
      id="prediksi"
      className="scroll-mt-36 overflow-hidden rounded-xl border border-border bg-surface shadow-[var(--shadow-card)]"
    >
      <div className="flex flex-wrap items-center gap-2 bg-[linear-gradient(115deg,#2A1210_0%,#3B1814_100%)] px-4 py-3 text-ember-text">
        <FlaskConical className="size-4 text-[#ffa94d]" aria-hidden />
        <h3 className="font-display text-base font-semibold">Prediksi Risiko 7 Hari</h3>
        <span className="rounded-full border border-[#ffa94d]/50 bg-[#f76707]/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ffd8bf]">
          Prediksi
        </span>
        <p className="w-full text-[11px] text-ember-text-muted">
          Estimasi risiko, bukan kepastian. Label: hotspot pada t+1..t+7; split berbasis waktu.
        </p>
      </div>

      <div className="space-y-4 px-4 py-5">
        {loading && !model ? (
          <p className="text-xs text-text-muted">Memuat status model…</p>
        ) : null}

        {error ? (
          <div className="rounded-lg border border-[#FFC9C9] bg-[#FFF5F5] px-3 py-2 text-xs text-[#C92A2A]">
            {error}
          </div>
        ) : null}

        {!loading && !error && model && !model.available ? (
          <div className="space-y-2">
            <Badge tone="warning">Model belum tersedia</Badge>
            <p className="max-w-2xl text-xs text-text-muted">
              {model.message ??
                "Belum ada metrik model di serving layer. Jalankan job fitur, training, dan prediksi."}
            </p>
            <button
              type="button"
              onClick={refresh}
              disabled={refreshing}
              className="inline-flex items-center gap-1.5 rounded-full border border-fire-tint-strong bg-fire-tint px-3 py-1 text-xs font-semibold text-fire-deep-orange transition-colors duration-150 hover:bg-fire-tint-strong disabled:opacity-60"
            >
              {refreshing ? "Mengantrekan…" : "Latih + prediksi sekarang"}
            </button>
            {notice ? <p className="text-[11px] text-text-subtle">{notice}</p> : null}
          </div>
        ) : null}

        {model?.available ? (
          <>
            <div className="flex flex-wrap items-center gap-2 text-[11px] text-text-muted">
              <Badge tone="fire" mono>
                {model.version}
              </Badge>
              <span>
                Dilatih {formatDateTimeWib(model.trained_at)} · {model.rows?.train?.toLocaleString("id-ID")}{" "}
                baris latih / {model.rows?.test?.toLocaleString("id-ID")} baris uji
              </span>
              {risk?.available ? (
                <span>
                  · Prediksi {formatDate(risk.predicted_at)} untuk {formatDate(risk.target_date)}
                </span>
              ) : null}
              <button
                type="button"
                onClick={refresh}
                disabled={refreshing}
                className="ml-auto inline-flex items-center gap-1.5 rounded-full border border-fire-tint-strong bg-fire-tint px-3 py-1 text-xs font-semibold text-fire-deep-orange transition-colors duration-150 hover:bg-fire-tint-strong disabled:opacity-60"
              >
                {refreshing ? "Mengantrekan…" : "Perbarui prediksi"}
              </button>
            </div>
            {notice ? <p className="text-[11px] text-text-subtle">{notice}</p> : null}

            {metrics ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[620px] text-left text-xs">
                  <thead className="text-[10px] uppercase tracking-wide text-text-subtle">
                    <tr>
                      <th className="py-2 pr-3 font-medium">Model</th>
                      <th className="px-3 py-2 font-medium">AUC-ROC</th>
                      <th className="px-3 py-2 font-medium">AUC-PR</th>
                      <th className="px-3 py-2 font-medium">Precision</th>
                      <th className="px-3 py-2 font-medium">Recall</th>
                      <th className="px-3 py-2 font-medium">F1</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    <MetricRow label="Random Forest" metric={metrics.model} highlight />
                    {metrics.gbt ? <MetricRow label="GBT (pembanding)" metric={metrics.gbt} /> : null}
                    <MetricRow
                      label="Baseline persistensi"
                      metric={metrics.baseline_persistence}
                    />
                  </tbody>
                </table>
                <p className="mt-1 text-[10px] text-text-subtle">
                  Evaluasi pada data uji {model.split?.test_start}+; baseline persistensi: ada hotspot 7
                  hari terakhir → prediksi ada. Ambang klasifikasi 0,5.
                </p>
              </div>
            ) : null}

            <div className="grid gap-3 sm:grid-cols-2">
              {metrics ? (
                <div>
                  <p className="mb-1 text-[11px] font-semibold text-text">Confusion matrix (uji)</p>
                  <div className="grid grid-cols-2 gap-1 text-[11px]">
                    <ConfusionCell label="TP" value={metrics.model.confusion.tp} tone="success" />
                    <ConfusionCell label="FP" value={metrics.model.confusion.fp} tone="warning" />
                    <ConfusionCell label="FN" value={metrics.model.confusion.fn} tone="danger" />
                    <ConfusionCell label="TN" value={metrics.model.confusion.tn} tone="muted" />
                  </div>
                  <p className="mt-1 text-[10px] text-text-subtle">
                    Positif {formatNumber(metrics.model.confusion.tp + metrics.model.confusion.fn)} dari{" "}
                    {formatNumber(metrics.model.rows)} baris uji.
                  </p>
                </div>
              ) : null}

              <div>
                <p className="mb-1 text-[11px] font-semibold text-text">Sebaran kategori risiko</p>
                <div className="flex flex-wrap gap-1.5">
                  {["sangat tinggi", "tinggi", "sedang", "rendah"].map((category) => (
                    <span
                      key={category}
                      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] ${CATEGORY_STYLE[category]}`}
                    >
                      <span className="capitalize">{category}</span>
                      <span className="font-mono">{formatNumber(categories[category] ?? 0)}</span>
                    </span>
                  ))}
                </div>
                <p className="mt-1 text-[10px] text-text-subtle">
                  {formatNumber(risk?.rows ?? 0)} grid historis diprediksi; skor maksimum{" "}
                  {formatPercent(risk?.max_score ?? 0)}. Ambang: &lt;0,25 rendah; &lt;0,5 sedang;
                  &lt;0,75 tinggi; ≥0,75 sangat tinggi.
                </p>
              </div>
            </div>

            {importance.length ? (
              <div>
                <p className="mb-2 text-[11px] font-semibold text-text">
                  Feature importance (Random Forest)
                </p>
                <ul className="space-y-1.5">
                  {importance.map((item) => (
                    <li key={item.feature} className="grid grid-cols-[minmax(0,1fr)_3rem] items-center gap-2">
                      <div className="min-w-0">
                        <div className="flex items-baseline justify-between gap-2 text-[11px]">
                          <span className="truncate text-text">{item.label}</span>
                        </div>
                        <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-muted">
                          <div
                            className="h-full rounded-full bg-fire-orange"
                            style={{ width: `${Math.max(2, (item.value / maxImportance) * 100)}%` }}
                          />
                        </div>
                      </div>
                      <span className="text-right font-mono text-[10px] text-text-muted">
                        {(item.value * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {topGrids.length ? (
              <div>
                <p className="mb-2 text-[11px] font-semibold text-text">
                  Grid risiko tertinggi — target {formatDate(risk?.target_date)}
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[520px] text-left text-xs">
                    <thead className="text-[10px] uppercase tracking-wide text-text-subtle">
                      <tr>
                        <th className="py-1.5 pr-3 font-medium">Grid</th>
                        <th className="px-3 py-1.5 font-medium">Provinsi</th>
                        <th className="px-3 py-1.5 font-medium">Hotspot 7h</th>
                        <th className="px-3 py-1.5 font-medium">Skor</th>
                        <th className="px-3 py-1.5 font-medium">Kategori</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {topGrids.map((grid) => (
                        <tr key={grid.grid_id}>
                          <td className="py-1.5 pr-3 font-mono text-[10px] text-text-muted">
                            {grid.grid_id}
                          </td>
                          <td className="px-3 py-1.5 text-text">{grid.province ?? "–"}</td>
                          <td className="px-3 py-1.5 font-mono text-[11px] text-text-muted">
                            {formatNumber(grid.cnt_7d ?? 0)}
                          </td>
                          <td className="px-3 py-1.5 font-mono text-[11px] text-text">
                            {formatPercent(grid.risk_score)}
                          </td>
                          <td className="px-3 py-1.5">
                            <span
                              className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] capitalize ${CATEGORY_STYLE[grid.risk_category] ?? CATEGORY_STYLE.rendah}`}
                            >
                              {grid.risk_category}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="mt-1 text-[10px] text-text-subtle">
                  Skor dapat jenuh pada grid beraktivitas tinggi; urutan seri memakai hotspot 7 hari.
                  Lapisan risiko juga tersedia di peta (kontrol Lapisan → Risiko).
                </p>
              </div>
            ) : null}

            <div className="rounded-lg border border-border bg-surface-muted/60 px-3 py-2 text-[11px] leading-relaxed text-text-muted">
              <p>
                <strong className="text-text">Keterbatasan:</strong>{" "}
                {model.weather_features_available
                  ? "fitur cuaca ERA5 hanya mencakup 10 stasiun Sumatera/Kalimantan pada 2022–2024, di luar itu ditandai weather_missing; "
                  : "fitur cuaca belum tersedia sehingga model hanya memakai fitur hotspot, waktu, dan lokasi; "}
                grid yang belum pernah memiliki hotspot historis tidak diprediksi; skor adalah estimasi
                statistik, bukan kepastian kebakaran.
              </p>
              {model.limitations?.length ? (
                <ul className="mt-1 list-disc space-y-0.5 pl-4">
                  {(model.limitations ?? []).slice(1).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </div>
          </>
        ) : null}
      </div>
    </section>
  );
}

const CATEGORY_STYLE: Record<string, string> = {
  rendah: "border-[#B2F2BB] bg-[#EBFBEE] text-[#2B8A3E]",
  sedang: "border-[#FFE8A1] bg-[#FFF9DB] text-[#8A4B00]",
  tinggi: "border-[#FFD8A8] bg-[#FFF4E6] text-[#D9480F]",
  "sangat tinggi": "border-[#FFC9C9] bg-[#FFF5F5] text-[#C92A2A]",
};

function formatPercent(value: number): string {
  return `${(value * 100).toLocaleString("id-ID", { maximumFractionDigits: 1 })}%`;
}

function MetricRow({
  label,
  metric,
  highlight,
}: {
  label: string;
  metric: ModelMetric;
  highlight?: boolean;
}) {
  return (
    <tr className={highlight ? "bg-fire-tint/40" : undefined}>
      <td className={`py-1.5 pr-3 ${highlight ? "font-semibold text-text" : "text-text-muted"}`}>
        {label}
      </td>
      <td className="px-3 py-1.5 font-mono text-[11px]">{metric.auc_roc.toFixed(3)}</td>
      <td className="px-3 py-1.5 font-mono text-[11px]">{metric.auc_pr.toFixed(3)}</td>
      <td className="px-3 py-1.5 font-mono text-[11px]">{metric.precision.toFixed(3)}</td>
      <td className="px-3 py-1.5 font-mono text-[11px]">{metric.recall.toFixed(3)}</td>
      <td className="px-3 py-1.5 font-mono text-[11px]">{metric.f1.toFixed(3)}</td>
    </tr>
  );
}

function ConfusionCell({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "success" | "warning" | "danger" | "muted";
}) {
  return (
    <div className={`rounded border px-2 py-1 ${CATEGORY_STYLE[tone === "success" ? "rendah" : tone === "warning" ? "sedang" : tone === "danger" ? "sangat tinggi" : "tinggi"]}`}>
      <span className="font-mono text-[10px]">{label}</span>{" "}
      <span className="font-semibold">{formatNumber(value)}</span>
    </div>
  );
}

export function ValidasiSection({
  summary,
  compare,
  loading,
  error,
  onUpload,
}: {
  summary: ValidationSummary | null;
  compare: ValidationCompare[] | null;
  loading: boolean;
  error?: string | null;
  onUpload: (file: File) => Promise<void>;
}) {
  const [uploading, setUploading] = useState(false);
  const [uploadNotice, setUploadNotice] = useState<string | null>(null);

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadNotice(null);
    try {
      await onUpload(file);
      setUploadNotice("Rekap SiPongi+/BNPB berhasil diunggah. Muat ulang untuk melihat perbandingan.");
    } catch (err) {
      setUploadNotice(err instanceof Error ? err.message : "Gagal mengunggah rekap validasi.");
    } finally {
      setUploading(false);
    }
  }

  const hasData = summary && summary.reference_rows > 0;

  return (
    <SectionCard
      id="validasi"
      title="Validasi terhadap rekap eksternal"
      description="Perbandingan tren pipeline dengan rekap SiPongi+/BNPB (korelasi dan selisih relatif)."
      loading={loading && !summary}
      error={error}
      empty={!loading && !summary}
      emptyHint="Belum ada data referensi validasi."
    >
      {error ? (
        <div className="rounded-lg border border-[#FFC9C9] bg-[#FFF5F5] px-3 py-2 text-xs text-[#C92A2A]">
          {error}
        </div>
      ) : null}

      <div className="space-y-3 px-4 py-3">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-medium text-text-subtle">Unggah rekap CSV</label>
            <p className="text-[10px] text-text-subtle">
              SiPongi+ atau BNPB; kolom wajib: date, province, hotspot_count.
            </p>
          </div>
          <label className="inline-flex items-center gap-2 rounded-lg border border-dashed border-border bg-surface-muted/50 px-4 py-3 text-[11px] text-text hover:border-border/70 cursor-pointer">
            <Upload className="size-4 text-text-subtle" aria-hidden />
            {uploading ? "Mengunggah…" : "Pilih file CSV"}
            <input
              type="file"
              accept=".csv"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void handleUpload(f);
              }}
              className="sr-only"
            />
          </label>
          {uploadNotice ? (
            <span className="text-[10px] text-text-subtle">{uploadNotice}</span>
          ) : null}
        </div>

        {hasData ? (
          <>
            <div className="grid gap-3 sm:grid-cols-3 text-[11px]">
              <div className="rounded-lg border border-border bg-surface px-3 py-2">
                <p className="text-[10px] uppercase tracking-wide text-text-subtle">Korelasi</p>
                <p className="text-sm font-semibold text-text">
                  {summary.correlation === null ? "–" : summary.correlation.toFixed(3)}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-surface px-3 py-2">
                <p className="text-[10px] uppercase tracking-wide text-text-subtle">Selisih relatif</p>
                <p className="text-sm font-semibold text-text">
                  {summary.relative_difference_percent === null
                    ? "–"
                    : `${summary.relative_difference_percent.toFixed(1)}%`}
                </p>
              </div>
              <div className="rounded-lg border border-border bg-surface px-3 py-2">
                <p className="text-[10px] uppercase tracking-wide text-text-subtle">RMSE</p>
                <p className="text-sm font-semibold text-text">
                  {summary.rmse === null ? "–" : summary.rmse.toFixed(1)}
                </p>
              </div>
            </div>

            <div className="rounded-lg border border-border bg-surface px-3 py-2">
              <p className="text-[10px] uppercase tracking-wide text-text-subtle mb-2">Rentang referensi</p>
              <p className="text-text-muted">
                {summary.date_start} s/d {summary.date_end} · {formatNumber(summary.reference_rows)} baris ·
                provinsi: {summary.reference_provinces.join(", ")}
              </p>
            </div>

            {compare && compare.length ? (
              <div className="mt-3">
                <p className="text-[11px] font-semibold text-text mb-2">
                  Perbandingan harian (pipeline vs referensi)
                </p>
                <EChart
                  option={{
                    tooltip: { trigger: "axis" },
                    legend: { data: ["Pipeline", "Referensi"], bottom: 0 },
                    grid: { left: 60, right: 40, top: 40, bottom: 60 },
                    xAxis: {
                      type: "category",
                      data: compare.map((c) => c.date),
                      name: "Tanggal",
                      axisLabel: { rotate: 45, fontSize: 10 },
                    },
                    yAxis: {
                      type: "value",
                      name: "Jumlah hotspot",
                      axisLabel: { fontSize: 10 },
                    },
                    series: [
                      {
                        name: "Pipeline",
                        type: "line",
                        smooth: true,
                        data: compare.map((c) => c.pipeline_count),
                        itemStyle: { color: "#D9480F" },
                      },
                      {
                        name: "Referensi",
                        type: "line",
                        smooth: true,
                        data: compare.map((c) => c.reference_count),
                        itemStyle: { color: "#1864AB" },
                      },
                    ],
                  }}
                  height={240}
                />
              </div>
            ) : null}

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[10px]">
                <thead className="text-[9px] uppercase tracking-wide text-text-subtle">
                  <tr>
                    <th className="px-2 py-1 font-medium">Tanggal</th>
                    <th className="px-2 py-1 font-medium">Pipeline</th>
                    <th className="px-2 py-1 font-medium">Referensi</th>
                    <th className="px-2 py-1 font-medium">Selisih</th>
                    <th className="px-2 py-1 font-medium">% Selisih</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {(compare ?? []).slice(0, 30).map((c) => (
                    <tr key={c.date}>
                      <td className="px-2 py-1 font-mono">{c.date}</td>
                      <td className="px-2 py-1">{formatNumber(c.pipeline_count)}</td>
                      <td className="px-2 py-1">{formatNumber(c.reference_count)}</td>
                      <td className="px-2 py-1">{formatNumber(c.diff)}</td>
                      <td className="px-2 py-1">
                        {c.diff_percent === null ? "–" : `${c.diff_percent}%`}
                      </td>
                    </tr>
                  ))}
                  {(compare ?? []).length > 30 && (
                    <tr>
                      <td colSpan={5} className="px-2 py-1 text-text-subtle">
                        Menampilkan 30 dari {(compare ?? []).length} tanggal
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        ) : null}
      </div>
    </SectionCard>
  );
}
