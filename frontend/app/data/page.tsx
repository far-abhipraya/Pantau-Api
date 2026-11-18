"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

import AddDataModal from "@/components/data/AddDataModal";
import JobsTab from "@/components/data/JobsTab";
import PreprocessingTab from "@/components/data/PreprocessingTab";
import SourcesTab from "@/components/data/SourcesTab";
import StatusStrip from "@/components/data/StatusStrip";
import Footer from "@/components/Footer";
import TopBar from "@/components/TopBar";
import Modal from "@/components/ui/Modal";
import Tabs from "@/components/ui/Tabs";
import {
  api,
  type DatasetItem,
  type DatasetsResponse,
  type JobsResponse,
  type QuarantineResponse,
  type SourcesResponse,
} from "@/lib/api";

type TabValue = "sources" | "preprocessing" | "jobs";

export default function DataPage() {
  const [tab, setTab] = useState<TabValue>("sources");
  const [sources, setSources] = useState<SourcesResponse | null>(null);
  const [datasets, setDatasets] = useState<DatasetsResponse | null>(null);
  const [quarantine, setQuarantine] = useState<QuarantineResponse | null>(null);
  const [jobs, setJobs] = useState<JobsResponse | null>(null);

  const [loadingSources, setLoadingSources] = useState(true);
  const [loadingDatasets, setLoadingDatasets] = useState(true);
  const [loadingQuarantine, setLoadingQuarantine] = useState(true);
  const [loadingJobs, setLoadingJobs] = useState(true);

  const [sourceFilter, setSourceFilter] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<DatasetItem | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "warning"; text: string } | null>(null);

  const loadSources = useCallback(async () => {
    try {
      setSources(await api.sources());
    } catch {
      /* biarkan UI menampilkan data terakhir */
    } finally {
      setLoadingSources(false);
    }
  }, []);

  const loadDatasets = useCallback(async (source: string) => {
    try {
      const data = await api.datasets({ source: source || undefined, limit: 500 });
      setDatasets(data);
    } catch {
      /* diamkan */
    } finally {
      setLoadingDatasets(false);
    }
  }, []);

  const loadQuarantine = useCallback(async () => {
    try {
      setQuarantine(await api.quarantine());
    } catch {
      /* diamkan */
    } finally {
      setLoadingQuarantine(false);
    }
  }, []);

  const loadJobs = useCallback(async () => {
    try {
      setJobs(await api.jobs({ limit: 40 }));
    } catch {
      /* diamkan */
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  const refreshAll = useCallback(() => {
    void loadSources();
    void loadDatasets(sourceFilter);
    void loadQuarantine();
    void loadJobs();
  }, [loadDatasets, loadJobs, loadQuarantine, loadSources, sourceFilter]);

  // Muat awal + polling: katalog/status tiap 20 dtk, job tiap 5 dtk.
  useEffect(() => {
    const kickoff = setTimeout(refreshAll, 0);
    const slow = setInterval(() => {
      void loadSources();
      void loadDatasets(sourceFilter);
      void loadQuarantine();
      void loadJobs();
    }, 20000);
    const fast = setInterval(() => void loadJobs(), 5000);
    return () => {
      clearTimeout(kickoff);
      clearInterval(slow);
      clearInterval(fast);
    };
  }, [refreshAll, loadDatasets, loadJobs, loadQuarantine, loadSources, sourceFilter]);

  const importInbox = useCallback(async () => {
    setImporting(true);
    setNotice(null);
    try {
      const submission = await api.importInbox(true);
      setNotice({
        tone: "success",
        text: `Impor folder berjalan sebagai job ${submission.job_id}. Progres muncul di Riwayat Job.`,
      });
      setTab("jobs");
      await loadJobs();
    } catch (error) {
      setNotice({ tone: "warning", text: (error as Error).message });
    } finally {
      setImporting(false);
    }
  }, [loadJobs]);

  const confirmDelete = useCallback(async () => {
    if (!pendingDelete?.id) return;
    setDeletingId(pendingDelete.id);
    try {
      await api.deleteDataset(pendingDelete.id);
      setNotice({ tone: "success", text: `File ${pendingDelete.name} dihapus dari HDFS.` });
      setPendingDelete(null);
      await Promise.all([loadDatasets(sourceFilter), loadSources()]);
    } catch (error) {
      setNotice({ tone: "warning", text: (error as Error).message });
    } finally {
      setDeletingId(null);
    }
  }, [loadDatasets, loadSources, pendingDelete, sourceFilter]);

  const tabItems = useMemo(
    () => [
      { value: "sources" as const, label: "Sumber Data" },
      { value: "preprocessing" as const, label: "Pre-processing" },
      {
        value: "jobs" as const,
        label: "Riwayat Job",
        badge: (jobs?.items.filter((job) => job.status === "running" || job.status === "queued").length ?? 0) || undefined,
      },
    ],
    [jobs],
  );

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <TopBar updatedAt={sources?.freshness.max_acq_ts ?? null} freshness={sources?.freshness.status} />

      <main className="mx-auto w-full max-w-[1200px] flex-1 px-4 pb-16 pt-24 sm:pt-28">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="field-label">Akuisisi &amp; pipeline</p>
            <h1 className="font-display text-3xl font-bold leading-9">Data &amp; Pre-processing</h1>
            <p className="mt-1 max-w-2xl text-sm text-text-muted">
              Pastikan akuisisi otomatis sehat, kelola dataset di HDFS, dan jalankan pre-processing
              yang sama dengan jalur otomatis.
            </p>
          </div>
          <Tabs items={tabItems} value={tab} onChange={setTab} ariaLabel="Bagian halaman data" />
        </div>

        {notice ? (
          <div
            className={`mt-4 flex items-start gap-2 rounded-xl border px-3 py-2 text-xs ${
              notice.tone === "success"
                ? "border-[#B2F2BB] bg-[#EBFBEE] text-[#2B8A3E]"
                : "border-[#FFE8A1] bg-[#FFF9DB] text-[#8A4B00]"
            }`}
            role="status"
          >
            {notice.tone === "success" ? (
              <CheckCircle2 className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            ) : (
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden />
            )}
            <span className="flex-1">{notice.text}</span>
            <button type="button" onClick={() => setNotice(null)} className="font-semibold hover:underline">
              tutup
            </button>
          </div>
        ) : null}

        <div className="mt-5">
          <StatusStrip
            sources={sources}
            loading={loadingSources}
            onOpenQuarantine={() => setTab("sources")}
          />
        </div>

        <div className="mt-6">
          {tab === "sources" ? (
            <SourcesTab
              sources={sources}
              datasets={datasets}
              quarantine={quarantine}
              loadingSources={loadingSources}
              loadingDatasets={loadingDatasets}
              loadingQuarantine={loadingQuarantine}
              sourceFilter={sourceFilter}
              onSourceFilter={setSourceFilter}
              onAddData={() => setAddOpen(true)}
              onImportFolder={() => void importInbox()}
              importing={importing}
              onDeleteDataset={setPendingDelete}
              deletingId={deletingId}
              onRefresh={refreshAll}
            />
          ) : null}

          {tab === "preprocessing" ? (
            <PreprocessingTab datasets={datasets} onJobsChanged={() => void loadJobs()} />
          ) : null}

          {tab === "jobs" ? <JobsTab jobs={jobs} loading={loadingJobs} onRefresh={refreshAll} /> : null}
        </div>
      </main>

      <Footer />

      <AddDataModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onFinished={() => {
          refreshAll();
        }}
      />

      <Modal
        open={pendingDelete !== null}
        title="Hapus file dari HDFS?"
        subtitle="Penghapusan hanya diizinkan di bawah /karhutla dan tidak dapat dibatalkan."
        onClose={() => setPendingDelete(null)}
        size="max-w-md"
        footer={
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setPendingDelete(null)}
              className="h-9 rounded-lg border border-border px-3 text-sm font-medium text-text-muted transition-colors hover:bg-surface-muted"
            >
              Batal
            </button>
            <button
              type="button"
              onClick={() => void confirmDelete()}
              disabled={deletingId !== null}
              className="h-9 rounded-lg bg-danger px-4 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
            >
              {deletingId !== null ? "Menghapus…" : "Hapus"}
            </button>
          </div>
        }
      >
        <p className="text-sm text-text-muted">
          File: <span className="font-medium text-text">{pendingDelete?.name}</span>
        </p>
        <p className="mt-1 break-all font-mono text-[11px] text-text-subtle">{pendingDelete?.hdfs_path}</p>
        <p className="mt-3 text-xs text-text-muted">
          Data yang sudah masuk <code className="font-mono">clean/hotspot</code> tidak terhapus otomatis;
          jalankan pipeline lagi bila perlu.
        </p>
      </Modal>
    </div>
  );
}
