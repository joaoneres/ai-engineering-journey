import unittest

from domain import pickups as rules
from errors import InputError, NotFoundError


def make(pickups=None, name="Ana", address="Rua A", count=2, priority="high", location=None):
    return rules.register_pickup(pickups or [], name, address, count, priority, location)


class RegisterPickupTests(unittest.TestCase):
    def test_creates_pickup_with_trimmed_text_and_initial_status(self):
        pickup = make(name="  Ana  ", address=" Rua A ")[0]
        self.assertEqual(pickup["customer_name"], "Ana")
        self.assertEqual(pickup["address"], "Rua A")
        self.assertEqual(pickup["status"], "pending")
        self.assertFalse(pickup["enriched"])

    def test_ids_are_sequential_and_original_list_is_untouched(self):
        first = make()
        second = make(first)
        self.assertEqual([p["id"] for p in second], [1, 2])
        self.assertEqual(len(first), 1)

    def test_location_enriches_the_pickup(self):
        location = {"cep": "01001-000", "city": "São Paulo", "state": "SP"}
        pickup = make(location=location)[0]
        self.assertTrue(pickup["enriched"])
        self.assertEqual(pickup["city"], "São Paulo")


class ValidationTests(unittest.TestCase):
    def test_rejects_invalid_fields(self):
        invalid = [
            dict(name="   "),
            dict(address=""),
            dict(count=0),
            dict(count=-3),
            dict(count=True),
            dict(count="2"),
            dict(priority="urgent"),
        ]
        for kwargs in invalid:
            with self.subTest(kwargs=kwargs), self.assertRaises(InputError):
                make(**kwargs)

    def test_normalize_cep(self):
        self.assertEqual(rules.normalize_cep(" 01001-000 "), "01001000")
        for bad in ("123", "abcdefgh", "0100100000", ""):
            with self.subTest(cep=bad), self.assertRaises(InputError):
                rules.normalize_cep(bad)

    def test_is_valid_pickup_accepts_module_1_records(self):
        old = {"id": 1, "customer_name": "A", "address": "B", "package_count": 1,
               "priority": "low", "status": "pending"}
        self.assertTrue(rules.is_valid_pickup(old))
        self.assertFalse(rules.is_valid_pickup({**old, "status": "done"}))
        self.assertFalse(rules.is_valid_pickup("not a dict"))


class FilterAndFindTests(unittest.TestCase):
    def setUp(self):
        pickups = make(name="A", priority="high")
        pickups = make(pickups, name="B", priority="low")
        self.pickups = rules.update_status(pickups, 2, "in_transit")

    def test_filter_by_status_and_priority(self):
        self.assertEqual([p["id"] for p in rules.filter_by(self.pickups, "status", "in_transit")], [2])
        self.assertEqual([p["id"] for p in rules.filter_by(self.pickups, "priority", "high")], [1])

    def test_filter_rejects_invalid_field_or_value(self):
        with self.assertRaises(InputError):
            rules.filter_by(self.pickups, "city", "x")
        with self.assertRaises(InputError):
            rules.filter_by(self.pickups, "status", "done")

    def test_find_by_id(self):
        self.assertEqual(rules.find_by_id(self.pickups, 1)["customer_name"], "A")
        self.assertIsNone(rules.find_by_id(self.pickups, 99))


class UpdateStatusTests(unittest.TestCase):
    def test_updates_only_target_without_mutating_original(self):
        pickups = make(make())
        updated = rules.update_status(pickups, 1, "completed")
        self.assertEqual([p["status"] for p in updated], ["completed", "pending"])
        self.assertEqual(pickups[0]["status"], "pending")

    def test_errors(self):
        pickups = make()
        with self.assertRaises(NotFoundError):
            rules.update_status(pickups, 9, "completed")
        with self.assertRaises(InputError):
            rules.update_status(pickups, 1, "pending")
        with self.assertRaises(InputError):
            rules.update_status(pickups, 1, "unknown")


class SummaryTests(unittest.TestCase):
    def test_empty_summary_has_all_categories_with_zero(self):
        summary = rules.build_summary([])
        self.assertEqual(summary["total_pickups"], 0)
        self.assertEqual(summary["total_packages"], 0)
        self.assertEqual(summary["by_priority"], {"low": 0, "medium": 0, "high": 0})
        self.assertEqual(summary["by_status"], {"pending": 0, "in_transit": 0, "completed": 0})

    def test_summary_counts(self):
        pickups = make(count=3, priority="high")
        pickups = make(pickups, count=7, priority="low")
        pickups = rules.update_status(pickups, 2, "completed")
        summary = rules.build_summary(pickups)
        self.assertEqual(summary["total_packages"], 10)
        self.assertEqual(summary["by_priority"]["high"], 1)
        self.assertEqual(summary["by_status"]["completed"], 1)


if __name__ == "__main__":
    unittest.main()
