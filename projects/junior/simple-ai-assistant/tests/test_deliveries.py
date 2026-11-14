import json
import tempfile
import unittest
from pathlib import Path

from ai_assistant.deliveries import DeliveryDataError, find_delivery, load_deliveries


class DeliveriesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.deliveries = load_deliveries()

    def test_loads_the_synthetic_base(self):
        self.assertIn("ABC123", self.deliveries)
        self.assertEqual(self.deliveries["ABC123"]["status"], "in_transit")

    def test_lookup_is_exact_but_ignores_case_and_spaces(self):
        self.assertEqual(find_delivery(self.deliveries, " abc123 ")["code"], "ABC123")

    def test_unknown_or_empty_code_finds_nothing(self):
        self.assertIsNone(find_delivery(self.deliveries, "ZZZ999"))
        self.assertIsNone(find_delivery(self.deliveries, ""))
        self.assertIsNone(find_delivery(self.deliveries, None))

    def test_invalid_files_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "deliveries.json"
            with self.assertRaises(DeliveryDataError):
                load_deliveries(bad)  # missing
            bad.write_text("{not json", encoding="utf-8")
            with self.assertRaises(DeliveryDataError):
                load_deliveries(bad)
            bad.write_text(json.dumps([{"name": "no code"}]), encoding="utf-8")
            with self.assertRaises(DeliveryDataError):
                load_deliveries(bad)


if __name__ == "__main__":
    unittest.main()
