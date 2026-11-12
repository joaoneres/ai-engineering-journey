import json
import tempfile
import unittest
from pathlib import Path

from errors import FileError
from storage import json_storage as storage

PICKUP = {"id": 1, "customer_name": "Ana", "address": "Rua A", "package_count": 2,
          "priority": "high", "status": "pending"}


class StorageTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "pickups.json"

    async def test_missing_file_returns_empty_list(self):
        self.assertEqual(await storage.load_pickups(self.path), [])

    async def test_invalid_json_and_wrong_format_return_empty_list(self):
        for content in ("", "{not json", '{"a": 1}', json.dumps([{"id": "x"}])):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                self.assertEqual(await storage.load_pickups(self.path), [])

    async def test_round_trip_keeps_accents_and_leaves_no_temp_file(self):
        pickups = [{**PICKUP, "customer_name": "José", "enriched": True}]
        await storage.save_pickups(pickups, self.path)
        self.assertEqual(await storage.load_pickups(self.path), pickups)
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["pickups.json"])

    async def test_failed_write_raises_file_error_and_keeps_previous_file(self):
        await storage.save_pickups([PICKUP], self.path)
        with self.assertRaises(FileError):
            await storage.save_pickups([{"id": {1}}], self.path)  # not JSON serializable
        self.assertEqual(await storage.load_pickups(self.path), [PICKUP])

    async def test_unwritable_directory_raises_file_error(self):
        with self.assertRaises(FileError):
            await storage.save_pickups([PICKUP], Path(self.tmp.name) / "missing" / "p.json")


if __name__ == "__main__":
    unittest.main()
