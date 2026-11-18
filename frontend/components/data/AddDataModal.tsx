"use client";

import { useCallback, useRef, useState } from "react";
import { FileUp, Plus, Trash2, TriangleAlert } from "lucide-react";

import Modal from "@/components/ui/Modal";
import { Badge } from "@/components/ui/Badge";
import { api, type DetectionResult, type UploadComplete } from "@/lib/api";
import { formatBytes, formatNumber } from "@/lib/format";

type ItemStatus = "pending" | "uploading" | "detected" | "processing" | "done" | "error";

type Item = {
  key: string;
  file: File;
  status: ItemStatus;
  uploadId?: string;
  received: number;
  detection?: DetectionResult;
  result?: UploadComplete;
  error?: string;
};

const FORMAT_TONE: Record<string, "fire" | "info" | "muted" | "danger"> = {
  FIRMS_VIIRS: "fire",
  FIRMS_MODIS: "fire",
  ERA5: "info",
  CHIRPS: "info",
};

export default function AddDataModal({
  open,
  onClose,
  onFinished,
}: {
  open: boolean;
  onClose: () => void;
  onFinished: () => void;
}) {
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const patch = useCallback((key: string, changes: Partial<Item>) => {
    setItems((current) => current.map((item) => (item.key === key ? { ...item, ...changes } : item)));
  }, []);

  /** Unggah bertahap (di belakang layar) lalu deteksi format tanpa memproses. */
  const uploadAndDetect = useCallback(
    async (item: Item) => {
      patch(item.key, { status: "uploading", error: undefined });
      try {
        const init = await api.uploadInit(item.file.name, item.file.size);
        patch(item.key, { uploadId: init.upload_id, received: 0 });
        const size = item.file.size;
        const chunk = Math.max(1, init.chunk_size);
        let index = 0;
        for (let offset = 0; offset < size; offset += chunk, index += 1) {
          const blob = item.file.slice(offset, Math.min(offset + chunk, size));
          await api.uploadChunk(init.upload_id, index, blob);
          patch(item.key, { received: Math.min(size, offset + blob.size) });
        }
        const detection = await api.datasetDetect(init.upload_id);
        patch(item.key, { status: "detected", detection });
      } catch (error) {
        patch(item.key, { status: "error", error: (error as Error).message });
      }
    },
    [patch],
  );

  const addFiles = useCallback(
    (files: FileList | null) => {
      if (!files) return;
      const next: Item[] = Array.from(files).map((file) => ({
        key: `${file.name}-${file.size}-${file.lastModified}`,
        file,
        status: "pending",
        received: 0,
      }));
      setItems((current) => [
        ...current,
        ...next.filter((item) => !current.some((c) => c.key === item.key)),
      ]);
      // Perilaku FR-D3: unggah + deteksi format otomatis setelah file dipilih.
      next.forEach((item) => void uploadAndDetect(item));
    },
    [uploadAndDetect],
  );

  const processAll = useCallback(async () => {
    setBusy(true);
    const detected = items.filter((item) => item.status === "detected" && item.uploadId);
    let first = true;
    for (const item of detected) {
      patch(item.key, { status: "processing" });
      try {
        const result = await api.uploadComplete(item.uploadId as string, first);
        first = false;
        patch(item.key, { status: "done", result });
      } catch (error) {
        patch(item.key, { status: "error", error: (error as Error).message });
      }
    }
    setBusy(false);
    onFinished();
  }, [items, onFinished, patch]);

  const cancelUploads = useCallback(async () => {
    const ids = items.map((item) => item.uploadId).filter(Boolean) as string[];
    await Promise.allSettled(ids.map((id) => api.uploadCancel(id)));
    setItems([]);
  }, [items]);

  const close = useCallback(() => {
    if (busy) return;
    void cancelUploads();
    onClose();
  }, [busy, cancelUploads, onClose]);

  const detectedCount = items.filter((item) => item.status === "detected").length;
  const doneCount = items.filter((item) => item.status === "done").length;

  return (
    <Modal
      open={open}
      title="Tambah data"
      subtitle="Data akan diproses otomatis dan muncul di peta setelah job selesai."
      onClose={close}
      size="max-w-2xl"
      footer={
        <div className="flex items-center justify-between gap-3">
          <p className="text-[11px] text-text-muted">
            {items.length === 0
              ? "Belum ada file dipilih."
              : `${items.length} file · ${detectedCount} siap diproses · ${doneCount} selesai`}
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={close}
              disabled={busy}
              className="h-9 rounded-lg border border-border px-3 text-sm font-medium text-text-muted transition-colors hover:bg-surface-muted disabled:opacity-60"
            >
              Batal
            </button>
            <button
              type="button"
              onClick={() => void processAll()}
              disabled={busy || detectedCount === 0}
              className="h-9 rounded-lg bg-fire-deep-orange px-4 text-sm font-semibold text-white transition-colors hover:bg-fire-crimson disabled:cursor-not-allowed disabled:opacity-60"
            >
              {busy ? "Memproses…" : "Proses"}
            </button>
          </div>
        </div>
      }
    >
      <div className="space-y-4">
        <label
          htmlFor="add-data-files"
          onDragOver={(event) => event.preventDefault()}
          onDrop={(event) => {
            event.preventDefault();
            addFiles(event.dataTransfer.files);
          }}
          className="flex cursor-pointer flex-col items-center gap-2 rounded-xl border border-dashed border-border bg-surface-muted px-4 py-8 text-center transition-colors hover:border-fire-deep-orange/50"
        >
          <FileUp className="size-6 text-fire-deep-orange" aria-hidden />
          <span className="text-sm font-medium">Letakkan file atau klik untuk memilih</span>
          <span className="text-[11px] text-text-muted">CSV atau JSON · VIIRS, MODIS, atau cuaca</span>
          <input
            ref={inputRef}
            id="add-data-files"
            type="file"
            multiple
            accept=".csv,.json"
            className="sr-only"
            onChange={(event) => addFiles(event.target.files)}
          />
        </label>

        {items.length > 0 ? (
          <ul className="space-y-2">
            {items.map((item) => {
              const detection = item.detection;
              const percent = item.file.size > 0 ? Math.round((item.received / item.file.size) * 100) : 0;
              return (
                <li key={item.key} className="rounded-xl border border-border p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium">{item.file.name}</p>
                      <p className="text-[11px] text-text-muted">
                        {formatBytes(item.file.size)}
                        {item.status === "uploading" ? ` · mengunggah ${percent}%` : ""}
                        {detection ? ` · ± ${formatNumber(detection.estimated_rows)} baris` : ""}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {detection ? (
                        <Badge tone={FORMAT_TONE[detection.detected_format] ?? (detection.procesable ? "fire" : "danger")}>
                          {detection.procesable ? detection.detected_format : "Tidak dikenal"}
                        </Badge>
                      ) : null}
                      {item.status === "done" ? <Badge tone="success">Tersimpan</Badge> : null}
                      <button
                        type="button"
                        aria-label={`Hapus ${item.file.name}`}
                        disabled={busy}
                        onClick={() => setItems((current) => current.filter((entry) => entry.key !== item.key))}
                        className="rounded-md p-1 text-text-subtle transition-colors hover:bg-surface-muted hover:text-danger disabled:opacity-50"
                      >
                        <Trash2 className="size-3.5" aria-hidden />
                      </button>
                    </div>
                  </div>

                  {item.status === "uploading" ? (
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-muted">
                      <div className="h-full bg-fire-deep-orange transition-[width]" style={{ width: `${percent}%` }} />
                    </div>
                  ) : null}

                  {detection ? (
                    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-text-muted">
                      <span>
                        Kolom dikenali: <strong className="text-text">{detection.columns.recognized.length}</strong>
                      </span>
                      <span>
                        Tidak dikenali: <strong className="text-text">{detection.columns.unknown.length}</strong>
                      </span>
                      {detection.sample_validation ? (
                        <span>
                          Sampel valid: {detection.sample_validation.valid_count}/
                          {detection.sample_validation.valid_count + detection.sample_validation.invalid_count}
                        </span>
                      ) : null}
                    </div>
                  ) : null}

                  {item.result?.quarantined ? (
                    <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-[#FFF5F5] px-2 py-1.5 text-[11px] text-danger">
                      <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                      {item.result.message} — file masuk karantina.
                    </p>
                  ) : null}

                  {item.result && !item.result.quarantined ? (
                    <p className="mt-2 text-[11px] text-text-muted">
                      Tersimpan di <code className="font-mono">{item.result.hdfs_path}</code>
                      {item.result.pipeline_job_id ? ` · pipeline ${item.result.pipeline_job_id}` : ""}
                    </p>
                  ) : null}

                  {item.error ? (
                    <p className="mt-2 flex items-start gap-1.5 rounded-lg bg-[#FFF5F5] px-2 py-1.5 text-[11px] text-danger">
                      <TriangleAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
                      {item.error}
                    </p>
                  ) : null}
                </li>
              );
            })}
          </ul>
        ) : null}

        <div className="flex items-center justify-between gap-2">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-border px-3 text-sm font-medium text-text-muted transition-colors hover:bg-surface-muted"
          >
            <Plus className="size-3.5" aria-hidden /> Pilih file
          </button>
          <span className="text-[11px] text-text-subtle">
            File diunggah bertahap di belakang layar, lalu formatnya dideteksi otomatis.
          </span>
        </div>
      </div>
    </Modal>
  );
}
