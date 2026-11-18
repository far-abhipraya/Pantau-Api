import unittest
from pathlib import Path
from app.adapters.detector import detect_format
from app.adapters.viirs import ViirsAdapter
from app.adapters.modis import ModisAdapter
from app.adapters.era5 import Era5Adapter
import pandas as pd

class TestAdapters(unittest.TestCase):
    def setUp(self):
        self.samples_dir = Path("data_samples")

    def test_detect_viirs(self):
        sample_file = self.samples_dir / "firms_viirs_sample.csv"
        adapter, source_type, _ = detect_format(sample_file)
        self.assertIsNotNone(adapter)
        self.assertEqual(source_type, "FIRMS_VIIRS")
        self.assertIsInstance(adapter, ViirsAdapter)

        df = pd.read_csv(sample_file)
        normalized = adapter.normalize(df)
        self.assertIn("confidence_level", normalized.columns)
        self.assertIn("confidence_score", normalized.columns)
        self.assertEqual(normalized["source"].iloc[0], "FIRMS_VIIRS")

        val = adapter.validate(normalized)
        self.assertGreater(val["valid_count"], 0)

    def test_detect_modis(self):
        sample_file = self.samples_dir / "firms_modis_sample.csv"
        adapter, source_type, _ = detect_format(sample_file)
        self.assertIsNotNone(adapter)
        self.assertEqual(source_type, "FIRMS_MODIS")
        self.assertIsInstance(adapter, ModisAdapter)

        df = pd.read_csv(sample_file)
        normalized = adapter.normalize(df)
        self.assertIn("confidence_level", normalized.columns)
        self.assertEqual(normalized["source"].iloc[0], "FIRMS_MODIS")

        val = adapter.validate(normalized)
        self.assertGreater(val["valid_count"], 0)

    def test_detect_era5(self):
        sample_file = self.samples_dir / "era5_sample.csv"
        adapter, source_type, _ = detect_format(sample_file)
        self.assertIsNotNone(adapter)
        self.assertEqual(source_type, "ERA5_WEATHER")
        self.assertIsInstance(adapter, Era5Adapter)

        df = pd.read_csv(sample_file)
        normalized = adapter.normalize(df)
        self.assertIn("temp_max", normalized.columns)
        self.assertIn("precipitation", normalized.columns)

        val = adapter.validate(normalized)
        self.assertGreater(val["valid_count"], 0)

if __name__ == "__main__":
    unittest.main()

