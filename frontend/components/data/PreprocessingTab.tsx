"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Database, Loader2, Play, Save, TriangleAlert } from "lucide-react";

import ConfigStepper from "@/components/data/ConfigStepper";
import { FunnelReport, ProfilingSummary } from "@/components/data/PipelineReport";
import { Badge, StatusBadge } from "@/components/ui/Badge";
import {
  api,
  type ConfigSchema,
  type DatasetsResponse,
  type PreprocessConfig,
  type PreprocessReport,
  type ProfilingReport,
} from "@/lib/api";
import { formatNumber } from "@/lib/format";

type Watch = { jobId: string; kind: "profile" | "run" } | null;

export default function PreprocessingTab({
  datasets,
  onJobsChanged,
}: {
  datasets: DatasetsResponse | null;
  onJobsChanged: () => void;
}) {
  const [schema, setSchema] = useState<ConfigSchema | null>(null);
  const [config, setConfig] = useState<PreprocessConfig>({});
  const [selectedDataset, setSelectedDataset] = useState<number | null>(null);
  const [watch, setWatch] = useState<Watch>(null);
  const [jobStatus, setJobStatus] = useState<string>("idle");
  const [profileReport, setProfileReport] = useState<ProfilingReport | null>(null);
  const [report, setReport] = useState<PreprocessReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedName, setSavedName] = useState("");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [savedConfigs, setSavedConfigs] = useState<{ name: string; config: PreprocessConfig }[]>([]);

  const catalogItems = useMemo(
    () => (datasets?.items ?? []).filter((item) => item.id !== null && !item.missing_in_hdfs),
    [datasets],
  );

  useEffect(() => {
    const controller = new AbortController();
    api
      .configSchema({ signal: controller.signal })
      .then((data) => {
        setSchema(data);
        setConfig(data.defaults);
      })
      .catch(() => undefined);
    api
      .preprocessingLatest({ signal: controller.signal })
      .then((data) => {
        if (data.report) setReport(data.report);
        if (data.config?.config) setConfig(data.config.config);
      })
      .catch(() => undefined);
    api
      .savedConfigs({ signal: controller.signal })
      .then((data) => setSavedConfigs(data.items))
      .catch(() => undefined);
    return () => controller.abort();
  }, []);

  // Polling status job (profil & pipeline).
  useEffect(() => {
    if (!watch) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const detail = await api.job(watch.jobId);
        if (cancelled) return;
        setJobStatus(detail.status);
        if (detail.status === "COMPLETED" || detail.status === "FAILED") {
          setWatch(null);
          if (detail.status === "FAILED") {
            setError(`Job ${watch.jobId} gagal. Lihat Riwayat Job untuk log.`);
          } else if (watch.kind === "profile") {
            const profile = await api.profileReport(watch.jobId);
            if (!cancelled && profile.report) setProfileReport(profile.report);
          } else if (detail.report && "rows" in detail.report) {
            setReport(detail.report as PreprocessReport);
          }
          onJobsChanged();
        }
      } catch (pollError) {
        if (!cancelled) setError((pollError as Error).message);
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), 3000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [watch, onJobsChanged]);

  const updateConfig = useCallback((section: string, key: string, value: unknown) => {
    setConfig((current) => ({ ...current, [section]: { ...(current[section] ?? {}), [key]: value } }));
  }, []);

  const runProfile = useCallback(async () => {
    setError(null);
    setProfileReport(null);
    try {
      const submission = await api.profileDataset(
        selectedDataset ? { dataset_id: selectedDataset } : {},
      );
      setJobStatus("queued");
      setWatch({ jobId: submission.job_id, kind: "profile" });
      onJobsChanged();
    } catch (submitError) {
      setError((submitError as Error).message);
    }
  }, [onJobsChanged, selectedDataset]);

  const runPipeline = useCallback(async () => {
    setError(null);
    try {
      const submission = await api.runPreprocessing(config);
      setJobStatus("queued");
      setWatch({ jobId: submission.job_id, kind: "run" });
      onJobsChanged();
    } catch (submitError) {
      setError((submitError as Error).message);
    }
  }, [config, onJobsChanged]);

  const saveConfig = useCallback(async () => {
    if (!savedName.trim()) return;
    setSaveMessage(null);
    try {
      const result = await api.saveConfig(savedName.trim(), config);
      setSaveMessage(`Konfigurasi tersimpan: ${result.name}`);
      const list = await api.savedConfigs();
      setSavedConfigs(list.items);
    } catch (saveError) {
      setSaveMessage((saveError as Error).message);
    }
  }, [config, savedName]);

  const busy = watch !== null;

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-3">
        <section className="card p-4 xl:col-span-1">
          <div className="flex items-center gap-2">
            <Database className="size-4 text-fire-deep-orange" aria-hidden />
            <h3 className="font-display text-base font-semibold">Dataset sumber</h3>
          </div>
          <p className="mt-1 text-[11px] text-text-muted">
            Pilih dataset dari katalog HDFS untuk profilling, atau gunakan semua file mentah.
          </p>
          <select
            value={selectedDataset ?? ""}
            onChange={(event) => setSelectedDataset(event.target.value ? Number(event.target.value) : null)}
            className="mt-3 h-9 w-full rounded-lg border border-border bg-surface px-2 text-xs"
          >
            <option value="">Semua file raw (hist + NRT)</option>
            {catalogItems.map((item) => (
              <option key={item.id as number} value={item.id as number}>
                {item.name} · {formatNumber(item.row_count)} baris
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => void runProfile()}
            disabled={busy}
            className="mt-3 inline-flex h-9 w-full items-center justify-center gap-1.5 rounded-lg border border-border text-sm font-medium text-text-muted transition-colors hover:bg-surface-muted disabled:opacity-60"
          >
            {busy && watch?.kind === "profile" ? <Loader2 className="size-4 animate-spin" aria-hidden /> : null}
            Profiling dataset
          </button>

          <div className="mt-4">
            {profileReport ? (
              <ProfilingSummary report={profileReport} />
            ) : (
              <p className="rounded-lg bg-surface-muted px-3 py-2 text-[11px] text-text-muted">
                Belum ada hasil profiling pada sesi ini. Tekan &ldquo;Profiling dataset&rdquo; untuk menghitung
                jumlah baris, tipe kolom, null, duplikat, dan distribusi.
              </p>
            )}
          </div>
        </section>

        <section className="card p-4 xl:col-span-2">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="font-display text-base font-semibold">Stepper pipeline</h3>
              <p className="text-[11px] text-text-muted">
                Opsi aktif dijalankan oleh Spark; langkah abu-abu belum tersedia.
              </p>
            </div>
            {watch ? <StatusBadge status={watch.kind === "run" ? jobStatus : "running"} /> : null}
          </div>
          <div className="mt-3">
            {schema ? (
              <ConfigStepper steps={schema.steps} config={config} onChange={updateConfig} />
            ) : (
              <p className="text-xs text-text-muted">Memuat skema konfigurasi…</p>
            )}
          </div>
        </section>
      </div>

      <section className="card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <div className="mr-auto">
            <h3 className="font-display text-base font-semibold">Konfigurasi &amp; eksekusi</h3>
            <p className="text-[11px] text-text-muted">
              Pipeline menulis ulang <code className="font-mono">clean/hotspot</code>; satu job Spark pada satu waktu.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void runPipeline()}
            disabled={busy}
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-fire-deep-orange px-4 text-sm font-semibold text-white transition-colors hover:bg-fire-crimson disabled:opacity-60"
          >
            {busy && watch?.kind === "run" ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Play className="size-4" aria-hidden />
            )}
            Jalankan pipeline
          </button>
        </div>

        {savedConfigs.length > 0 ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl border border-border px-3 py-2">
            <label htmlFor="saved-config" className="text-[11px] font-medium text-text-muted">
              Muat konfigurasi tersimpan
            </label>
            <select
              id="saved-config"
              value=""
              onChange={(event) => {
                const picked = savedConfigs.find((item) => item.name === event.target.value);
                if (picked) {
                  setConfig(picked.config);
                  setSaveMessage(`Konfigurasi dimuat: ${picked.name}`);
                }
              }}
              className="h-8 w-56 rounded-lg border border-border bg-surface px-2 text-xs"
            >
              <option value="">Pilih…</option>
              {savedConfigs.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
            <span className="text-[11px] text-text-subtle">
              Dijalankan ulang dengan tombol &ldquo;Jalankan pipeline&rdquo;.
            </span>
          </div>
        ) : null}

        <div className="mt-3 flex flex-wrap items-center gap-2 rounded-xl bg-surface-muted px-3 py-2">
          <span className="text-[11px] font-medium text-text-muted">Simpan konfigurasi</span>
          <input
            value={savedName}
            onChange={(event) => setSavedName(event.target.value)}
            placeholder="nama konfigurasi"
            className="h-8 w-48 rounded-lg border border-border bg-surface px-2 text-xs"
          />
          <button
            type="button"
            onClick={() => void saveConfig()}
            disabled={!savedName.trim()}
            className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-border bg-surface px-3 text-xs font-medium text-text-muted transition-colors hover:bg-surface-muted disabled:opacity-50"
          >
            <Save className="size-3.5" aria-hidden /> Simpan JSON
          </button>
          {saveMessage ? <span className="text-[11px] text-text-muted">{saveMessage}</span> : null}
        </div>

        <details className="mt-3">
          <summary className="cursor-pointer text-[11px] font-medium text-text-muted">
            Lihat JSON konfigurasi aktif
          </summary>
          <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-ember px-3 py-2 font-mono text-[10px] text-ember-text">
            {JSON.stringify(config, null, 2)}
          </pre>
        </details>

        {error ? (
          <p className="mt-3 flex items-start gap-1.5 rounded-lg bg-[#FFF5F5] px-3 py-2 text-xs text-danger">
            <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            {error}
          </p>
        ) : null}
      </section>

      <section className="card p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-display text-base font-semibold">Laporan sebelum / sesudah</h3>
          {report ? <Badge tone="success">{report.rows.clean_rate_percent}% bersih</Badge> : null}
        </div>
        <div className="mt-3">
          {report ? (
            <FunnelReport report={report} />
          ) : (
            <p className="text-xs text-text-muted">
              Belum ada laporan. Jalankan pipeline untuk melihat funnel jumlah baris per langkah.
            </p>
          )}
        </div>
      </section>
    </div>
  );
}
