/** Klien API terpusat untuk PantauApi. */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api";

export type WindowHours = 24 | 48 | 168;
export type SensorFilter = "all" | "viirs" | "modis";
export type ConfidenceFilter = "all" | "nominal" | "high";

export type Freshness = {
  status: "fresh" | "delayed" | "stale" | "unknown";
  age_hours: number | null;
  max_acq_ts: string | null;
  label: string;
};

// --- Peta ------------------------------------------------------------------

export type HotspotProperties = {
  acq_ts_utc?: string;
  acq_ts_wib: string;
  acq_date?: string;
  acq_time?: string;
  satellite: string;
  instrument: string;
  confidence_level: "low" | "nominal" | "high";
  confidence_score: number;
  frp: number;
  province: string;
  grid_id?: string;
};

export type HotspotFeature = {
  type: "Feature";
  geometry: { type: "Point"; coordinates: [number, number] };
  properties: HotspotProperties;
};

export type HotspotResponse = {
  type: "FeatureCollection";
  features: HotspotFeature[];
  meta: {
    count: number;
    limit: number;
    truncated: boolean;
    window_hours: WindowHours;
    bbox: [number, number, number, number];
    max_acq_ts: string;
    freshness: Freshness;
  };
};

export type GridProperties = {
  hotspot_count: number;
  high_count: number;
  nominal_count: number;
  low_count: number;
  frp_sum: number;
  frp_max: number;
  frp_avg: number;
  province: string | null;
  grid_lat: number;
  grid_lon: number;
};

export type GridFeature = {
  type: "Feature";
  geometry: { type: "Polygon"; coordinates: number[][][] };
  properties: GridProperties;
};

export type GridResponse = {
  type: "FeatureCollection";
  features: GridFeature[];
  meta: {
    count: number;
    window_hours: WindowHours;
    resolution: 1 | 0.5 | 0.25;
    zoom: number;
    bbox: [number, number, number, number];
  };
};

export type Kpi = {
  window_hours: WindowHours;
  hotspots: number;
  high_confidence: number;
  top_province: { name: string; count: number } | null;
  latest_acq_ts: string | null;
  freshness: Freshness;
};

export type ProvinceTrendPoint = { date: string; count: number };

export type ProvinceSummary = {
  province: string;
  last_window: number;
  previous_window: number;
  last_7d: number;
  high_last_window: number;
  rank: number;
  trend: ProvinceTrendPoint[];
};

export type ProvinceResponse = {
  provinces: ProvinceSummary[];
  meta: { count: number; hours: number; max_date: string; freshness: Freshness };
};

export type RiskResponse = {
  type: "FeatureCollection";
  features: unknown[];
  meta: { available: boolean; message?: string; count?: number };
};

export type GeoJson = {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    properties: { code: string; name: string; level: string };
    geometry: GeoJSON.Geometry;
  }>;
};

// --- Sumber data & strip status -------------------------------------------

export type SourceCard = {
  id: string;
  name: string;
  satellite: string | null;
  kind: "firms" | "weather";
  automatic: boolean;
  status: string;
  last_update: string | null;
  rows: number | null;
  date_range: { start?: string; end?: string };
  hdfs_path: string;
  files?: number;
  size_bytes?: number;
};

export type SourcesResponse = {
  generated_at: string | null;
  freshness: Freshness;
  target_rows: number;
  total_raw_rows: number;
  clean_rows: number;
  indicator: { met: boolean; progress_percent: number };
  strip: {
    hdfs_raw: { files: number; bytes: number };
    total_raw_rows: number;
    target_rows: number;
    indicator_met: boolean;
    last_ingest: { at: string | null; source: string | null; rows: number | null; status: string | null };
    spark: { status: "idle" | "running"; active_job: string | null; active_type: string | null };
    quarantine_count: number;
    catalog: { files: number; total_size_bytes: number; total_rows: number; quarantine_count: number };
  };
  sources: SourceCard[];
  schedule: {
    nifi: { enabled: boolean; interval_hours: number; url: string; next_run: string | null; note: string };
    folder_import: {
      enabled: boolean;
      inbox: string;
      interval_seconds: number;
      next_run: string | null;
      last_run: string | null;
      note: string;
    };
  };
};

// --- Dataset ---------------------------------------------------------------

export type DatasetItem = {
  id: number | null;
  name: string;
  hdfs_path: string;
  folder: string | null;
  origin: string;
  source: string;
  size_bytes: number;
  modified: string | null;
  row_count: number | null;
  ingest_path: string;
  detected_format: string | null;
  created_at: string | null;
  in_catalog: boolean;
  missing_in_hdfs?: boolean;
};

export type DatasetsResponse = {
  items: DatasetItem[];
  meta: {
    count: number;
    summary: { files: number; total_size_bytes: number; total_rows: number; quarantine_count: number };
    sources: string[];
  };
};

export type DatasetPreview = {
  id: number;
  name: string;
  hdfs_path: string;
  columns: string[];
  rows: string[][];
  preview_limit: number;
  truncated: boolean;
};

export type QuarantineResponse = {
  items: Array<{ id: number; file_name: string; reason: string; row_count: number; created_at: string }>;
  meta: { count: number; failed_dir: string; files: { name: string; size_bytes: number }[] };
};

// --- Job -------------------------------------------------------------------

export type JobItem = {
  id: string;
  job_type: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  rows_in: number | null;
  rows_out: number | null;
  config: Record<string, unknown> | null;
};

export type JobsResponse = {
  items: JobItem[];
  meta: {
    count: number;
    queue: { running: string | null; queued: string[] };
    driver_memory: string;
    available_gb: number;
  };
};

export type JobDetail = JobItem & {
  log_tail: string;
  report: PreprocessReport | Record<string, unknown>;
};

// --- Pre-processing --------------------------------------------------------

export type OptionSpec = {
  key: string;
  label: string;
  type: "boolean" | "select" | "number";
  default: unknown;
  help?: string;
  choices?: { value: string; label: string }[];
};

export type StepSpec = {
  key: string;
  label: string;
  description: string;
  available: boolean;
  note?: string;
  options: OptionSpec[];
};

export type ConfigSchema = {
  steps: StepSpec[];
  defaults: Record<string, Record<string, unknown>>;
};

export type PreprocessConfig = Record<string, Record<string, unknown>>;

export type FunnelStep = {
  step: string;
  label: string;
  rows: number;
  duration_ms: number;
  note: string;
};

export type ColumnStat = {
  name: string;
  dtype: string;
  null_count: number;
  null_percent: number;
  distinct: number;
};

export type PreprocessReport = {
  job_id: string;
  status: string;
  started_at: string;
  finished_at: string;
  inputs: string[];
  output_path: string;
  config: PreprocessConfig;
  rows: {
    input: number;
    invalid_coords_or_time: number;
    out_of_bbox: number;
    in_bbox: number;
    before_dedup: number;
    clean: number;
    duplicates_removed: number;
    confidence_filtered?: number;
    outliers_removed?: number;
    clean_rate_percent: number;
  };
  funnel?: FunnelStep[];
  durations_ms?: Record<string, number>;
  null_handling?: { strategy: string; filled: Record<string, number> };
  normalization?: { method: string; params: Record<string, number | null> };
  provinces?: Record<string, number>;
  sensors?: { instrument: string; satellite: string; count: number }[];
  schema?: [string, string][];
};

export type ProfilingReport = {
  job_id: string;
  timestamp: string;
  source_paths: string[];
  total_rows: number;
  valid_coords_rows: number;
  missing_coords: number;
  date_range: { start: string; end: string };
  frp_metrics: { min: number; max: number; avg: number; std: number };
  brightness_metrics: { min: number; max: number; avg: number };
  satellite_distribution: { satellite: string; count: number }[];
  confidence_distribution: { confidence: string; count: number }[];
  columns?: ColumnStat[];
  duplicate_rows_on_key?: number;
  distribution_deciles?: Record<string, number[]>;
};

export type LatestPreprocessing = {
  report: PreprocessReport | null;
  config: { job_id?: string; config?: PreprocessConfig } | null;
  profiling_path: string | null;
};

export type UploadInit = {
  upload_id: string;
  filename: string;
  chunk_size: number;
  max_bytes: number;
  received_bytes: number;
};

export type DetectionResult = {
  upload_id: string;
  filename: string;
  size_bytes: number;
  detected_format: string;
  adapter: string | null;
  estimated_rows: number;
  columns: { total: number; recognized: string[]; unknown: string[] };
  sample_validation: { valid_count: number; invalid_count: number; errors: string[] } | null;
  procesable: boolean;
};

export type UploadComplete = {
  file: string;
  status: string;
  detected_format?: string;
  hdfs_path?: string;
  rows?: { input: number };
  message?: string;
  quarantined?: boolean;
  job_id: string;
  pipeline_job_id?: string | null;
};

// --- Analitik --------------------------------------------------------------

export type AnalyticsWindowDays = 30 | 90 | 365 | 0;
export type AnalyticsConf = "all" | "high";
export type AnalyticsGranularity = "day" | "week" | "month";

export type AnalyticsKpi = {
  today: number;
  yesterday: number;
  last_7d: number;
  prev_7d: number;
  last_30d: number;
  prev_30d: number;
  top_province: { name: string; count: number } | null;
  high_confidence_30d: number;
  avg_frp_30d: number;
  meta: {
    computed_at: string;
    conf: string;
    max_date: string | null;
    history_start: string | null;
    n_days: number;
  };
};

export type AnalyticsTrendPoint = { date: string; count: number; high_count: number };

export type AnalyticsTrend = {
  points: AnalyticsTrendPoint[];
  meta: {
    computed_at: string;
    granularity: AnalyticsGranularity;
    days: number;
    province: string | null;
    conf: string;
    n: number;
  };
};

export type AnalyticsRankingItem = {
  rank: number;
  province: string;
  count: number;
  share_percent: number;
  previous: number;
  delta_percent: number | null;
};

export type AnalyticsRanking = {
  items: AnalyticsRankingItem[];
  meta: { computed_at: string; days: number; conf: string; total: number; n: number };
};

export type AnalyticsSeasonality = {
  months: string[];
  years: number[];
  by_year: Record<string, number[]>;
  by_province: Record<string, number[]>;
  meta: {
    computed_at: string;
    province: string | null;
    conf: string;
    n_years: number;
    n_provinces: number;
    years_covered: string | null;
  };
};

export type AnalyticsYearCompare = {
  years: { year: number; points: { doy: number; cum: number }[] }[];
  current_year?: number;
  historical_mean: { doy: number; cum: number }[];
  meta: { computed_at: string; province: string | null; conf: string; n_years: number };
};

export type AnalyticsTopGrid = {
  items: {
    grid_lat: number;
    grid_lon: number;
    province: string | null;
    count: number;
    high_count: number;
  }[];
  meta: { computed_at: string; days: number; province: string | null; conf: string; n: number };
};

export type InsightCard = {
  id: string;
  type: "tren" | "wilayah" | "musiman" | string;
  score: number;
  title: string;
  key_figure: string;
  sentence: string;
  confidence: "Tinggi" | "Sedang" | "Rendah";
  evidence: Record<string, unknown>;
  anchor: string;
};

export type AnalyticsInsights = {
  cards: InsightCard[];
  meta: {
    computed_at: string;
    days: number;
    province: string | null;
    conf: string;
    scope: string;
    n: number;
    skipped: { id: string; reason: string }[];
  };
};

export type WeatherCorrelation = {
  available: boolean;
  reason?: string;
  needs?: string[];
  computed_at: string;
};

export type ModelMetric = {
  auc_roc: number;
  auc_pr: number;
  precision: number;
  recall: number;
  f1: number;
  confusion: { tp: number; fp: number; fn: number; tn: number };
  rows: number;
};

export type ModelFeatureImportance = {
  feature: string;
  label: string;
  value: number;
};

export type ModelRiskGrid = {
  grid_id: string;
  province: string | null;
  lat: number;
  lon: number;
  risk_score: number;
  risk_category: "rendah" | "sedang" | "tinggi" | "sangat tinggi";
  target_date: string;
  cnt_7d?: number;
};

export type ValidationCompare = {
  date: string;
  pipeline_count: number;
  reference_count: number;
  diff: number;
  diff_percent: number | null;
};

export type ValidationSummary = {
  reference_rows: number;
  reference_provinces: string[];
  date_start: string | null;
  date_end: string | null;
  correlation: number | null;
  relative_difference_percent: number | null;
  rmse: number | null;
  comparison: ValidationCompare[];
};

export type AnalyticsModel = {
  available: boolean;
  message?: string;
  version?: string;
  algorithm?: string;
  trained_at?: string;
  split?: { train_end: string; validation: string; test_start: string };
  rows?: { train: number; validation: number; test: number; positive_weight: number };
  label_rate?: { train: number; test: number };
  metrics?: {
    model: ModelMetric;
    baseline_persistence: ModelMetric;
    gbt?: ModelMetric;
  };
  feature_importance?: ModelFeatureImportance[];
  features?: string[];
  weather_features_available?: boolean;
  limitations?: string[];
  risk: {
    available: boolean;
    predicted_at?: string;
    feature_date?: string;
    target_date?: string;
    horizon_days?: number;
    rows?: number;
    categories?: Record<string, number>;
    max_score?: number;
    mean_score?: number;
    thresholds?: Record<string, string>;
    top_grids: ModelRiskGrid[];
  };
};

// --- Transport -------------------------------------------------------------

type RequestOptions = { signal?: AbortSignal };

async function send<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  params: Record<string, string | number | undefined> = {},
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") url.searchParams.set(key, String(value));
  })
  const isFormData = body instanceof FormData;
  const response = await fetch(url, {
    method,
    headers: {
      Accept: "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
    },
    body: isFormData ? (body as FormData) : (body === undefined ? undefined : JSON.stringify(body)),
    signal: options.signal,
    cache: "no-store",
  });
  if (!response.ok) {
    let detail = `Permintaan gagal (${response.status})`;
    try {
      const payload = await response.json();
      if (typeof payload?.detail === "string") detail = payload.detail;
    } catch {
      /* biarkan pesan bawaan */
    }
    throw new Error(detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const get = <T,>(path: string, params?: Record<string, string | number | undefined>, options?: RequestOptions) =>
  send<T>("GET", path, params, undefined, options);
const post = <T,>(path: string, body?: unknown, params?: Record<string, string | number | undefined>, options?: RequestOptions) =>
  send<T>("POST", path, params, body, options);

export const api = {
  // Peta
  kpi: (hours: WindowHours, options?: RequestOptions) => get<Kpi>("/map/kpi", { hours }, options),
  hotspots: (
    bbox: string,
    params: { hours: WindowHours; sensor: SensorFilter; min_conf: ConfidenceFilter; limit?: number },
    options?: RequestOptions,
  ) => get<HotspotResponse>("/map/hotspots", { bbox, ...params }, options),
  grid: (
    bbox: string,
    params: { zoom: number; hours: WindowHours; resolution?: number },
    options?: RequestOptions,
  ) => get<GridResponse>("/map/grid", { bbox, ...params }, options),
  provinces: (hours: 24 | 168, options?: RequestOptions) => get<ProvinceResponse>("/map/provinces", { hours }, options),
  risk: (options?: RequestOptions) => get<RiskResponse>("/map/risk", {}, options),
  provincesGeo: async (options?: RequestOptions): Promise<GeoJson> => {
    const response = await fetch(`${API_BASE}/geo/provinces`, { signal: options?.signal, cache: "force-cache" });
    if (!response.ok) throw new Error("Batas provinsi tidak tersedia");
    return (await response.json()) as GeoJson;
  },
  health: (options?: RequestOptions) =>
    get<{ status: string; serving: { available: boolean } }>("/health", {}, options),

  // Sumber data & katalog
  sources: (options?: RequestOptions) => get<SourcesResponse>("/sources", {}, options),
  datasets: (params: { source?: string; limit?: number } = {}, options?: RequestOptions) =>
    get<DatasetsResponse>("/datasets", params, options),
  datasetPreview: (id: number, limit = 30, options?: RequestOptions) =>
    get<DatasetPreview>(`/datasets/${id}/preview`, { limit }, options),
  deleteDataset: (id: number, options?: RequestOptions) => send<{ deleted: boolean }>("DELETE", `/datasets/${id}`, {}, undefined, options),
  quarantine: (options?: RequestOptions) => get<QuarantineResponse>("/quarantine", {}, options),

  // Upload manual
  uploadInit: (filename: string, sizeBytes: number, options?: RequestOptions) =>
    post<UploadInit>("/datasets/upload/init", { filename, size_bytes: sizeBytes }, undefined, options),
  uploadChunk: async (uploadId: string, index: number, blob: Blob, options?: RequestOptions) => {
    const form = new FormData();
    form.set("upload_id", uploadId);
    form.set("index", String(index));
    form.set("file", blob);
    const response = await fetch(`${API_BASE}/datasets/upload/chunk`, {
      method: "POST",
      body: form,
      signal: options?.signal,
    });
    if (!response.ok) throw new Error(`Potongan ${index + 1} gagal diunggah`);
    return (await response.json()) as { received_bytes: number; size_bytes: number; parts: number };
  },
  datasetDetect: (uploadId: string, options?: RequestOptions) =>
    post<DetectionResult>("/datasets/detect", { upload_id: uploadId }, undefined, options),
  uploadComplete: (uploadId: string, runPipeline = true, options?: RequestOptions) =>
    post<UploadComplete>("/datasets/upload/complete", { upload_id: uploadId, run_pipeline: runPipeline }, undefined, options),
  uploadCancel: (uploadId: string) =>
    send<{ cancelled: boolean }>("DELETE", `/datasets/upload/${uploadId}`),

  // Job & ingest
  jobs: (params: { limit?: number; job_type?: string; status?: string } = {}, options?: RequestOptions) =>
    get<JobsResponse>("/jobs", params, options),
  job: (id: string, options?: RequestOptions) => get<JobDetail>(`/jobs/${id}`, {}, options),
  importInbox: (runPipeline = true, options?: RequestOptions) =>
    post<{ job_id: string; status: string }>("/ingest/inbox", { run_pipeline: runPipeline }, undefined, options),

  // Pre-processing
  configSchema: (options?: RequestOptions) => get<ConfigSchema>("/preprocessing/config-schema", {}, options),
  preprocessingLatest: (options?: RequestOptions) => get<LatestPreprocessing>("/preprocessing/latest", {}, options),
  profileDataset: (payload: { dataset_id?: number; hdfs_path?: string }, options?: RequestOptions) =>
    post<{ job_id: string; status: string; report_path: string }>("/preprocessing/profile", payload, undefined, options),
  profileReport: (jobId: string, options?: RequestOptions) =>
    get<{ status: string; ready: boolean; job_id: string; report?: ProfilingReport }>(`/preprocessing/profile/${jobId}`, {}, options),
  runPreprocessing: (config: PreprocessConfig, options?: RequestOptions) =>
    post<{ job_id: string; status: string; report_path: string }>("/preprocessing/run", { config }, undefined, options),
  saveConfig: (name: string, config: PreprocessConfig, options?: RequestOptions) =>
    post<{ saved: boolean; name: string; path: string }>("/preprocessing/configs", { name, config }, undefined, options),
  savedConfigs: (options?: RequestOptions) =>
    get<{ items: { name: string; path: string; config: PreprocessConfig }[] }>("/preprocessing/configs", {}, options),

  // Analitik
  analyticsKpi: (conf: AnalyticsConf = "all", options?: RequestOptions) =>
    get<AnalyticsKpi>("/analytics/kpi", { conf }, options),
  analyticsTrend: (
    params: {
      granularity: AnalyticsGranularity;
      days: AnalyticsWindowDays;
      province?: string;
      conf: AnalyticsConf;
    },
    options?: RequestOptions,
  ) => get<AnalyticsTrend>("/analytics/trend", params, options),
  analyticsRanking: (
    params: { days: AnalyticsWindowDays; limit?: number; conf: AnalyticsConf },
    options?: RequestOptions,
  ) => get<AnalyticsRanking>("/analytics/ranking", params, options),
  analyticsSeasonality: (
    params: { province?: string; conf: AnalyticsConf },
    options?: RequestOptions,
  ) => get<AnalyticsSeasonality>("/analytics/seasonality", params, options),
  analyticsYearCompare: (
    params: { province?: string; conf: AnalyticsConf },
    options?: RequestOptions,
  ) => get<AnalyticsYearCompare>("/analytics/year-compare", params, options),
  analyticsTopGrid: (
    params: { days: AnalyticsWindowDays; limit?: number; province?: string; conf: AnalyticsConf },
    options?: RequestOptions,
  ) => get<AnalyticsTopGrid>("/analytics/top-grid", params, options),
  analyticsInsights: (
    params: { days: AnalyticsWindowDays; province?: string; conf: AnalyticsConf },
    options?: RequestOptions,
  ) => get<AnalyticsInsights>("/analytics/insights", params, options),
  analyticsWeather: (options?: RequestOptions) =>
    get<WeatherCorrelation>("/analytics/weather-correlation", {}, options),
  analyticsModel: (options?: RequestOptions) =>
    get<AnalyticsModel>("/analytics/model", {}, options),
  analyticsModelRefresh: (options?: RequestOptions) =>
    post<{ job_id: string; status: string }>("/analytics/model/refresh", undefined, undefined, options),
  analyticsRefresh: (options?: RequestOptions) =>
    post<{ job_id: string; status: string }>("/analytics/refresh", undefined, undefined, options),
  validationReferenceUpload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return send<{ status: string; rows_inserted: number; file: string; message: string }>(
      "POST",
      "/validation/reference",
      {},
      formData,
    );
  },
  validationCompare: (options?: RequestOptions) =>
    get<ValidationSummary>("/validation/compare", {}, options),
};
