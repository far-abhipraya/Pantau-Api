from typing import List, Dict, Any
import pandas as pd
import numpy as np
from .base import BaseAdapter
from app.core.config import settings

class ModisAdapter(BaseAdapter):
    source_type = "FIRMS_MODIS"

    def can_handle(self, header: List[str], sample_rows: List[Dict[str, Any]]) -> bool:
        lower_header = [h.strip().lower() for h in header]
        has_coords = "latitude" in lower_header and "longitude" in lower_header
        if not has_coords:
            return False

        # Modis typically has numeric confidence (0-100) and satellite Terra / Aqua
        if "bright_ti4" in lower_header:
            return False

        for r in sample_rows:
            instrument = str(r.get("instrument", "")).upper()
            satellite = str(r.get("satellite", "")).upper()
            confidence = str(r.get("confidence", "")).strip()
            if "MODIS" in instrument or "TERRA" in satellite or "AQUA" in satellite:
                return True
            if confidence.isdigit():
                return True
        return False

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        if "instrument" not in df.columns:
            df["instrument"] = "MODIS"
        else:
            df["instrument"] = df["instrument"].fillna("MODIS")

        # MODIS confidence is 0-100 numeric
        def map_conf(val):
            try:
                score = float(val)
                if score >= 80:
                    return "high"
                elif score >= 30:
                    return "nominal"
                else:
                    return "low"
            except (ValueError, TypeError):
                v = str(val).strip().lower()
                if v == "h":
                    return "high"
                elif v == "l":
                    return "low"
                return "nominal"

        df["confidence_score"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(50.0)
        df["confidence_level"] = df["confidence"].apply(map_conf)

        df["acq_date"] = pd.to_datetime(df["acq_date"]).dt.strftime("%Y-%m-%d")
        df["acq_time"] = df["acq_time"].astype(str).str.zfill(4)

        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["brightness"] = pd.to_numeric(df["brightness"], errors="coerce")
        df["frp"] = pd.to_numeric(df.get("frp", 0.0), errors="coerce").fillna(0.0)

        df["source"] = self.source_type
        return df

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        errors = []
        null_coords = df["latitude"].isna() | df["longitude"].isna()
        if null_coords.any():
            errors.append(f"{null_coords.sum()} baris koordinat kosong / tidak valid")

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

