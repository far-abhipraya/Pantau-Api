from typing import List, Dict, Any
import pandas as pd
from .base import BaseAdapter
from app.core.config import settings

class Era5Adapter(BaseAdapter):
    source_type = "ERA5_WEATHER"

    def can_handle(self, header: List[str], sample_rows: List[Dict[str, Any]]) -> bool:
        lower_header = [h.strip().lower() for h in header]
        # Weather typically contains temp_max, temp_min, precipitation, wind_speed_max
        weather_keys = {"precipitation", "temp_max", "temp_mean", "wind_speed_max"}
        matches = weather_keys.intersection(set(lower_header))
        return len(matches) >= 2

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
        df["temp_max"] = pd.to_numeric(df.get("temp_max", 0.0), errors="coerce")
        df["temp_min"] = pd.to_numeric(df.get("temp_min", 0.0), errors="coerce")
        df["temp_mean"] = pd.to_numeric(df.get("temp_mean", 0.0), errors="coerce")
        df["precipitation"] = pd.to_numeric(df.get("precipitation", 0.0), errors="coerce").fillna(0.0)
        df["wind_speed_max"] = pd.to_numeric(df.get("wind_speed_max", 0.0), errors="coerce").fillna(0.0)

        df["source"] = self.source_type
        return df

    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        errors = []
        null_coords = df["latitude"].isna() | df["longitude"].isna()
        if null_coords.any():
            errors.append(f"{null_coords.sum()} baris koordinat cuaca kosong / tidak valid")

        bbox = settings.BBOX_INDONESIA
        out_of_bbox = (
            (df["latitude"] < bbox["min_lat"]) | 
            (df["latitude"] > bbox["max_lat"]) | 
            (df["longitude"] < bbox["min_lon"]) | 
            (df["longitude"] > bbox["max_lon"])
        )
        if out_of_bbox.any():
            errors.append(f"{out_of_bbox.sum()} stasiun/grid cuaca di luar Bounding Box Indonesia")

        invalid_mask = null_coords | out_of_bbox
        valid_count = int((~invalid_mask).sum())
        invalid_count = int(invalid_mask.sum())

        return {
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "errors": errors
        }

