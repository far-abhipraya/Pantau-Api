from typing import List, Dict, Any
import pandas as pd
import numpy as np
from .base import BaseAdapter
from app.core.config import settings

class ViirsAdapter(BaseAdapter):
    source_type = "FIRMS_VIIRS"

    def can_handle(self, header: List[str], sample_rows: List[Dict[str, Any]]) -> bool:
        lower_header = [h.strip().lower() for h in header]
        # VIIRS FIRMS format typically contains: bright_ti4, bright_ti5 OR (instrument=='VIIRS' / confidence in {'l','n','h'})
        has_coords = "latitude" in lower_header and "longitude" in lower_header
        if not has_coords:
            return False

        # Cek kolom khas VIIRS
        if "bright_ti4" in lower_header or "bright_ti5" in lower_header:
            return True

        # Cek sampel baris jika kolom standar 'brightness' digunakan (seperti archive VIIRS)
        for r in sample_rows:
            instrument = str(r.get("instrument", "")).upper()
            satellite = str(r.get("satellite", "")).upper()
            confidence = str(r.get("confidence", "")).lower()
            if "VIIRS" in instrument or "SNPP" in satellite or "NOAA" in satellite or confidence in ["l", "n", "h"]:
                return True
        return False

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # Normalisasi nama kolom menjadi lower case
        df.columns = [c.strip().lower() for c in df.columns]

        # Standardisasi kolom brightness (VIIRS punya bright_ti4 atau brightness)
        if "bright_ti4" in df.columns and "brightness" not in df.columns:
            df["brightness"] = df["bright_ti4"]
        if "bright_ti5" in df.columns and "bright_t31" not in df.columns:
            df["bright_t31"] = df["bright_ti5"]

        # Instrument & Satellite
        if "instrument" not in df.columns:
            df["instrument"] = "VIIRS"
        else:
            df["instrument"] = df["instrument"].fillna("VIIRS")

        # Confidence: mapping 'l' -> low, 'n' -> nominal, 'h' -> high
        def map_conf(val):
            v = str(val).strip().lower()
            if v == "l":
                return "low"
            elif v == "h":
                return "high"
            return "nominal"

        df["confidence_level"] = df["confidence"].apply(map_conf)
        # Numerical confidence score representation for ML (low: 30, nominal: 70, high: 95)
        conf_numeric = {"low": 30.0, "nominal": 70.0, "high": 95.0}
        df["confidence_score"] = df["confidence_level"].map(conf_numeric)

        # Datetime
        df["acq_date"] = pd.to_datetime(df["acq_date"]).dt.strftime("%Y-%m-%d")
        df["acq_time"] = df["acq_time"].astype(str).str.zfill(4)
        
        # Numeric parsing
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["brightness"] = pd.to_numeric(df["brightness"], errors="coerce")
        df["frp"] = pd.to_numeric(df.get("frp", 0.0), errors="coerce").fillna(0.0)

        df["source"] = self.source_type
        return df

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        errors = []
        # Missing coordinates
        null_coords = df["latitude"].isna() | df["longitude"].isna()
        if null_coords.any():
            errors.append(f"{null_coords.sum()} baris koordinat kosong / tidak valid")

        # Bounding box Indonesia
        bbox = settings.BBOX_INDONESIA
        out_of_bbox = (
            (df["latitude"] < bbox["min_lat"]) | 
            (df["latitude"] > bbox["max_lat"]) | 
            (df["longitude"] < bbox["min_lon"]) | 
            (df["longitude"] > bbox["max_lon"])
        )
        if out_of_bbox.any():
            errors.append(f"{out_of_bbox.sum()} baris di luar Bounding Box Indonesia")

        invalid_mask = null_coords | out_of_bbox
        valid_count = int((~invalid_mask).sum())
        invalid_count = int(invalid_mask.sum())

        return {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "errors": errors
        }

