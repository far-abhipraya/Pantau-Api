"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AnalyticsFilterBar, { SECTION_LINKS } from "@/components/analytics/AnalyticsFilterBar";
import HeroKpi from "@/components/analytics/HeroKpi";
import InsightCards from "@/components/analytics/InsightCards";
import {
  CuacaSection,
  FaktorSection,
  PrediksiSection,
  ValidasiSection,
} from "@/components/analytics/InsightSections";
import MusimanSection from "@/components/analytics/MusimanSection";
import RingkasanSection from "@/components/analytics/RingkasanSection";
import WilayahSection from "@/components/analytics/WilayahSection";
import Footer from "@/components/Footer";
import TopBar from "@/components/TopBar";
import {
  api,
  type AnalyticsConf,
  type AnalyticsGranularity,
  type AnalyticsInsights,
  type AnalyticsKpi,
  type AnalyticsModel,
  type AnalyticsRanking,
  type AnalyticsSeasonality,
  type AnalyticsTopGrid,
  type AnalyticsTrend,
  type AnalyticsWindowDays,
  type AnalyticsYearCompare,
  type GeoJson,
  type ValidationSummary,
  type WeatherCorrelation,
} from "@/lib/api";

type Errors = Record<string, string | undefined>;

function applyResult<T>(
  result: PromiseSettledResult<T>,
  key: string,
  setValue: (value: T) => void,
  errors: Errors,
) {
  if (result.status === "fulfilled") {
    setValue(result.value);
    return;
  }
  const reason = result.reason;
  if (reason instanceof DOMException && reason.name === "AbortError") return;
  errors[key] = reason instanceof Error ? reason.message : "Gagal memuat data";
}

export default function AnalyticsPage() {
  const [days, setDays] = useState<AnalyticsWindowDays>(30);
  const [province, setProvince] = useState("");
  const [conf, setConf] = useState<AnalyticsConf>("all");
  const [granularity, setGranularity] = useState<AnalyticsGranularity>("day");

  const [geo, setGeo] = useState<GeoJson | null>(null);
  const [kpi, setKpi] = useState<AnalyticsKpi | null>(null);
  const [insights, setInsights] = useState<AnalyticsInsights | null>(null);
  const [trend, setTrend] = useState<AnalyticsTrend | null>(null);
  const [ranking, setRanking] = useState<AnalyticsRanking | null>(null);
  const [yearCompare, setYearCompare] = useState<AnalyticsYearCompare | null>(null);
  const [seasonality, setSeasonality] = useState<AnalyticsSeasonality | null>(null);
  const [topGrid, setTopGrid] = useState<AnalyticsTopGrid | null>(null);
  const [weather, setWeather] = useState<WeatherCorrelation | null>(null);
  const [model, setModel] = useState<AnalyticsModel | null>(null);
  const [modelError, setModelError] = useState<string | null>(null);
  const [modelLoading, setModelLoading] = useState(true);
  const [validation, setValidation] = useState<ValidationSummary | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [validationLoading, setValidationLoading] = useState(true);

  const [loading, setLoading] = useState(true);
  const [errors, setErrors] = useState<Errors>({});
  const [refreshing, setRefreshing] = useState(false);
  const [notice, setNotice] = useState<{ tone: "success" | "warning"; text: string } | null>(null);
  const [activeSection, setActiveSection] = useState<string>("ringkasan");

  const provinces = useMemo(
    () =>
      (geo?.features ?? [])
        .map((feature) => feature.properties.name)
        .filter((name) => Boolean(name))
        .sort((a, b) => a.localeCompare(b, "id")),
    [geo],
  );

  // GeoJSON dipakai untuk daftar provinsi dan choropleth; cukup dimuat sekali.
  useEffect(() => {
    let cancelled = false;
    api
      .provincesGeo()
      .then((data) => {
        if (!cancelled) setGeo(data);
      })
      .catch(() => {
        /* seksi peta akan menampilkan status kosong */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Muat semua agregat analitik setiap filter berubah.
  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    const provinceParam = province || undefined;
    const nextErrors: Errors = {};

    // Tandai status memuat di luar badan effect (hindari render berantai sinkron).
    void Promise.resolve().then(() => {
      if (signal.aborted) return;
      setLoading(true);
      setErrors({});
    });

    void Promise.allSettled([
      api.analyticsKpi(conf, { signal }),
      api.analyticsInsights({ days, province: provinceParam, conf }, { signal }),
      api.analyticsTrend({ granularity, days, province: provinceParam, conf }, { signal }),
      api.analyticsRanking({ days, limit: 38, conf }, { signal }),
      api.analyticsYearCompare({ province: provinceParam, conf }, { signal }),
      api.analyticsSeasonality({ province: provinceParam, conf }, { signal }),
      api.analyticsTopGrid({ days, limit: 10, province: provinceParam, conf }, { signal }),
      api.analyticsWeather({ signal }),
    ]).then((results) => {
      if (signal.aborted) return;
      applyResult(results[0], "kpi", setKpi, nextErrors);
      applyResult(results[1], "insights", setInsights, nextErrors);
      applyResult(results[2], "trend", setTrend, nextErrors);
      applyResult(results[3], "ranking", setRanking, nextErrors);
      applyResult(results[4], "year", setYearCompare, nextErrors);
      applyResult(results[5], "seasonality", setSeasonality, nextErrors);
      applyResult(results[6], "grid", setTopGrid, nextErrors);
      applyResult(results[7], "weather", setWeather, nextErrors);
      setErrors(nextErrors);
      setLoading(false);
    });

    return () => controller.abort();
  }, [days, province, conf, granularity]);

  // Muat data validasi (tidak bergantung filter halaman; cukup sekali).
  useEffect(() => {
    const controller = new AbortController();
    api
      .validationCompare({ signal: controller.signal })
      .then((data) => {
        setValidation(data);
        setValidationError(null);
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setValidationError(error instanceof Error ? error.message : "Gagal memuat data validasi");
      })
      .finally(() => setValidationLoading(false));
    return () => controller.abort();
  }, []);

  // Scroll-spy ringan untuk navigasi seksi.
  useEffect(() => {
    const elements = SECTION_LINKS.map((section) => document.getElementById(section.id)).filter(
      (element): element is HTMLElement => Boolean(element),
    );
    if (!elements.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible) setActiveSection(visible.target.id);
      },
      { rootMargin: "-160px 0px -55% 0px", threshold: [0.05, 0.3, 0.6] },
    );
    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, [loading]);

  const changeDays = useCallback((value: AnalyticsWindowDays) => {
    setDays(value);
    setGranularity(value === 30 ? "day" : value === 90 ? "week" : "month");
  }, []);

  // Model dan risiko tidak bergantung filter halaman; cukup dimuat sekali.
  useEffect(() => {
    const controller = new AbortController();
    api
      .analyticsModel({ signal: controller.signal })
      .then((data) => {
        setModel(data);
        setModelError(null);
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setModelError(error instanceof Error ? error.message : "Gagal memuat status model");
      })
      .finally(() => setModelLoading(false));
    return () => controller.abort();
  }, []);

  const refreshModel = useCallback(async () => {
    await api.analyticsModelRefresh();
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setNotice(null);
    try {
      const submission = await api.analyticsRefresh();
      setNotice({
        tone: "success",
        text: `Job agregasi ${submission.job_id} dijalankan. Grafik memakai hasil terakhir sampai job selesai (pantau di halaman Data → Riwayat Job).`,
      });
    } catch (error) {
      setNotice({
        tone: "warning",
        text: error instanceof Error ? error.message : "Gagal menjalankan job agregasi.",
      });
    } finally {
      setRefreshing(false);
    }
  }, []);

  const uploadValidation = useCallback(async (file: File) => {
    await api.validationReferenceUpload(file);
    // Muat ulang data validasi setelah unggah
    const data = await api.validationCompare();
    setValidation(data);
    setValidationError(null);
  }, []);

  const periodLabel = days === 0 ? "seluruh riwayat" : `${days} hari terakhir`;
  const windowLabel = days === 0 ? "seluruh riwayat" : `${days} hari terakhir`;

  return (
    <div className="flex min-h-dvh flex-col bg-bg">
      <TopBar updatedAt={kpi?.meta.computed_at ?? null} />
      <main className="mx-auto w-full max-w-[1200px] flex-1 space-y-4 px-4 pb-16 pt-24">
        <div>
          <p className="field-label">Analitik</p>
          <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
            Insight hotspot Indonesia
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-text-muted">
            Ringkasan deskriptif dari serving layer: tren, wilayah, pola musiman, dan insight otomatis.
            Lapisan diagnostik cuaca menunggu data lengkap; prediksi risiko 7 hari memakai model
            berbasis waktu dengan baseline persistensi.
          </p>
        </div>

        <HeroKpi kpi={kpi} loading={loading && !kpi} province={province} />

        <InsightCards
          data={insights}
          loading={loading && !insights}
          error={errors.insights}
          periodLabel={periodLabel}
        />

        <AnalyticsFilterBar
          days={days}
          onDaysChange={changeDays}
          province={province}
          provinces={provinces}
          onProvinceChange={setProvince}
          conf={conf}
          onConfChange={setConf}
          onRefresh={refresh}
          refreshing={refreshing}
          updatedAt={kpi?.meta.computed_at ?? null}
          notice={notice}
          activeSection={activeSection}
        />

        <RingkasanSection
          trend={trend}
          yearCompare={yearCompare}
          loading={loading}
          trendError={errors.trend}
          yearError={errors.year}
          granularity={granularity}
          onGranularityChange={setGranularity}
        />

        <WilayahSection
          ranking={ranking}
          topGrid={topGrid}
          geo={geo}
          loading={loading}
          rankingError={errors.ranking}
          gridError={errors.grid}
          windowLabel={windowLabel}
        />

        <MusimanSection data={seasonality} loading={loading} error={errors.seasonality} />

        <FaktorSection modelAvailable={Boolean(model?.available)} />

        <CuacaSection weather={weather} loading={loading} error={errors.weather} />

        <PrediksiSection
          model={model}
          loading={modelLoading}
          error={modelError}
          onRefresh={refreshModel}
        />

        <ValidasiSection
          summary={validation}
          compare={validation?.comparison ?? null}
          loading={validationLoading}
          error={validationError}
          onUpload={uploadValidation}
        />

        <p className="text-[11px] text-text-subtle">
          Sumber: NASA FIRMS (VIIRS/MODIS) yang diolah pipeline PantauApi. Semua agregat dihitung
          ulang oleh job Spark dan dilayani DuckDB; tidak ada angka yang dikarang di sisi klien.
        </p>
      </main>
      <Footer />
    </div>
  );
}
