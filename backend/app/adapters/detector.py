import csv
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any
from .base import BaseAdapter
from .viirs import ViirsAdapter
from .modis import ModisAdapter
from .era5 import Era5Adapter

REGISTRY: List[BaseAdapter] = [
    ViirsAdapter(),
    ModisAdapter(),
    Era5Adapter(),
]

def detect_format(file_path: Path, max_rows: int = 20) -> Tuple[Optional[BaseAdapter], str, List[Dict[str, Any]]]:
    """
    Membaca header dan sampel baris file CSV untuk mendeteksi adapter yang cocok.
    Mengembalikan: (adapter_instance, source_type, sample_rows)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")

    sample_rows = []
    header = []
    
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            sample_rows.append(row)

    if not header:
        return None, "empty_or_invalid", []

    for adapter in REGISTRY:
        if adapter.can_handle(header, sample_rows):
            return adapter, adapter.source_type, sample_rows

    return None, "unknown", sample_rows

