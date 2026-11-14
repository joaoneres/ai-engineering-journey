import unittest

from simple_report_pipeline.formatting import format_priority, format_status, format_summary


class FormattingTests(unittest.TestCase):
    def test_format_status_returns_portuguese_label(self):
        self.assertEqual(format_status("in_transit"), "Em rota")

    def test_format_status_rejects_unknown(self):
        with self.assertRaises(ValueError):
            format_status("lost")

    def test_format_priority_rejects_unknown(self):
        with self.assertRaises(ValueError):
            format_priority("urgent")

    def test_format_summary_lists_every_category(self):
        summary = {
            "total_pickups": 2,
            "total_packages": 13,
            "by_priority": {"low": 1, "medium": 0, "high": 1},
            "by_status": {"pending": 1, "in_transit": 1, "completed": 0},
        }
        text = format_summary(summary)
        self.assertIn("Total de coletas: 2 | Total de pacotes: 13", text)
        self.assertIn("Por prioridade: Alta 1 | Média 0 | Baixa 1", text)
        self.assertIn("Por status: Pendente 1 | Em rota 1 | Concluída 0", text)


if __name__ == "__main__":
    unittest.main()
