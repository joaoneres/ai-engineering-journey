import unittest

from simple_manifest_validator.formatting import format_report

APPROVED = {
    "total_records": 1,
    "total_errors": 0,
    "problems": [],
    "status": "approved",
}


class FormattingTests(unittest.TestCase):
    def test_approved_report(self):
        self.assertEqual(
            format_report(APPROVED),
            "\n".join(
                [
                    "===== Validation report =====",
                    "Records: 1",
                    "Errors: 0",
                    "Problems:",
                    "- none",
                    "Final status: approved",
                ]
            )
            + "\n",
        )

    def test_rejected_report_lists_every_problem(self):
        text = format_report(
            {
                "total_records": 2,
                "total_errors": 2,
                "problems": [
                    {"record": 2, "message": "duplicate package PKG-1"},
                    {"record": 2, "message": "empty route"},
                ],
                "status": "rejected",
            }
        )
        self.assertIn("- record 2: duplicate package PKG-1", text)
        self.assertIn("- record 2: empty route", text)
        self.assertIn("Final status: rejected", text)


if __name__ == "__main__":
    unittest.main()
