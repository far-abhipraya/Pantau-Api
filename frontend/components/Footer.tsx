export default function Footer() {
  return (
    <footer className="bg-ember px-4 py-6 text-ember-text">
      <div className="mx-auto flex max-w-[1200px] flex-col gap-2 text-xs">
        <p className="text-ember-text-muted">
          Sumber data: NASA FIRMS (VIIRS SNPP/NOAA-20/NOAA-21, MODIS Terra/Aqua) · Basemap: CARTO,
          Esri World Imagery
        </p>
        <p className="text-[11px] text-ember-text-muted">
          Hotspot adalah indikasi anomali suhu satelit, bukan kepastian kebakaran. Data cuaca
          beresolusi kasar dan awan dapat menutupi deteksi.
        </p>
        <p className="text-[11px] text-ember-text-muted/80">
          PantauApi · Proyek Big Data &amp; Analitik · 2026
        </p>
      </div>
    </footer>
  );
}
