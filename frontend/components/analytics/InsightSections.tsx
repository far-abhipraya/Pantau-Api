"use client";

import { Badge } from "@/components/ui/Badge";
import SectionCard from "@/components/analytics/SectionCard";
import type { WeatherCorrelation } from "@/lib/api";
import { CloudSun, FlaskConical, Info, ShieldCheck } from "lucide-react";

const FAKTOR_ROWS = [
  { id: "FP1", label: "Korelasi lag curah hujan / hari kering", status: "Menunggu data cuaca" },
  { id: "FP2", label: "Kurva dosis-respons hari tanpa hujan", status: "Menunggu data cuaca" },
  { id: "FP3", label: "Anomali cuaca periode berjalan", status: "Menunggu data cuaca" },
  { id: "FP4", label: "Penjelas wilayah (faktor pendorong)", status: "Menunggu model (Fase 6)" },
  { id: "FP5", label: "Pembanding antar tahun", status: "Tersedia di Ringkasan" },
  { id: "FP6", label: "Feature importance model", status: "Menunggu model (Fase 6)" },
];

export function FaktorSection() {
  return (
    <SectionCard
      id="faktor"
      className="scroll-mt-36"
      title="Faktor di masa lalu yang berkaitan dengan kejadian hari ini"
      description="Diagnostik asosiasi membutuhkan data cuaca dan fitur turunan yang baru tersedia pada Fase 6."
    >
      <ul className="divide-y divide-border text-xs">
        {FAKTOR_ROWS.map((row) => (
          <li key={row.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
            <span className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-text-subtle">{row.id}</span>
              <span className="text-text">{row.label}</span>
            </span>
            {row.status === "Tersedia di Ringkasan" ? (
              <a href="#ringkasan" className="text-[11px] font-medium text-fire-deep-orange hover:underline">
                Lihat grafik kumulatif tahunan
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

export function PrediksiSection() {
  return (
    <section id="prediksi" className="scroll-mt-36 overflow-hidden rounded-xl border border-border bg-surface shadow-[var(--shadow-card)]">
      <div className="flex flex-wrap items-center gap-2 bg-[linear-gradient(115deg,#2A1210_0%,#3B1814_100%)] px-4 py-3 text-ember-text">
        <FlaskConical className="size-4 text-[#ffa94d]" aria-hidden />
        <h3 className="font-display text-base font-semibold">Prediksi Risiko 7 Hari</h3>
        <span className="rounded-full border border-[#ffa94d]/50 bg-[#f76707]/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#ffd8bf]">
          Prediksi
        </span>
        <p className="w-full text-[11px] text-ember-text-muted">
          Estimasi risiko, bukan kepastian.
        </p>
      </div>
      <div className="space-y-2 px-4 py-5">
        <p className="text-sm font-medium text-text">Model belum tersedia (Fase 6)</p>
        <p className="max-w-2xl text-xs text-text-muted">
          Belum ada model risiko yang dilatih pada pipeline ini. Seksi ini akan menampilkan peta
          risiko 7 hari, tabel grid risiko tertinggi, kurva risiko mingguan, panel performa model
          (AUC-ROC, AUC-PR, precision, recall, F1, confusion matrix), perbandingan baseline
          persistensi, feature importance, serta tanggal training dan catatan keterbatasan.
        </p>
        <p className="text-[11px] text-text-subtle">
          Tidak ada angka prediksi yang ditampilkan sampai job <code className="font-mono">train.py</code>{" "}
          dan <code className="font-mono">predict.py</code> dijalankan.
        </p>
      </div>
    </section>
  );
}

export function ValidasiSection() {
  return (
    <SectionCard
      id="validasi"
      title="Validasi terhadap rekap eksternal"
      description="Perbandingan tren pipeline dengan rekap SiPongi+/BNPB."
    >
      <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border bg-surface-muted/50 px-4 py-8 text-center">
        <ShieldCheck className="size-6 text-text-subtle" aria-hidden />
        <p className="text-sm font-medium text-text">Belum ada data validasi</p>
        <p className="max-w-xl text-xs text-text-muted">
          Unggah rekap SiPongi+/BNPB akan diaktifkan pada Fase 8. Grafik garis ganda, korelasi, dan
          selisih relatif baru dapat dihitung setelah rekap tersedia.
        </p>
      </div>
    </SectionCard>
  );
}
