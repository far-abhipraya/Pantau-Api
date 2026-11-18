from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import pandas as pd
from pathlib import Path

class BaseAdapter(ABC):
    """
    Interface abstrak untuk adapter ingestion data PantauApi.
    """
    source_type: str = "unknown"

    @abstractmethod
    def can_handle(self, header: List[str], sample_rows: List[Dict[str, Any]]) -> bool:
        """
        Memeriksa apakah adapter dapat menangani format file berdasarkan header dan sampel baris.
        """
        pass

    @abstractmethod
    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Menormalisasi kolom dan tipe data menjadi skema kanonikal PantauApi.
        """
        pass

    @abstractmethod
    def validate(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Melakukan validasi batas geografis (bbox Indonesia), nilai kosong, dan rentang metrik.
        Mengembalikan ringkasan: {'valid_count': int, 'invalid_count': int, 'errors': list}
        """
        pass

