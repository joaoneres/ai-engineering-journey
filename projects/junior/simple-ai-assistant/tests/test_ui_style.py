import unittest

from ai_assistant.ui_style import (
    CLEAR_LINE,
    DEFAULT_WIDTH,
    MAX_WIDTH,
    MIN_WIDTH,
    PLAIN,
    RESET,
    Style,
    detect_style,
)


class FakeStream:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


class DetectStyleTests(unittest.TestCase):
    def test_a_pipe_gets_no_colour_and_no_redrawing(self):
        style = detect_style(FakeStream(False), {"TERM": "xterm"})
        self.assertFalse(style.color)
        self.assertFalse(style.interactive)

    def test_a_real_terminal_gets_colour_and_redrawing(self):
        style = detect_style(FakeStream(True), {"TERM": "xterm-256color"})
        self.assertTrue(style.color)
        self.assertTrue(style.interactive)

    def test_no_color_turns_colour_off_but_keeps_redrawing(self):
        style = detect_style(FakeStream(True), {"TERM": "xterm", "NO_COLOR": "1"})
        self.assertFalse(style.color)
        self.assertTrue(style.interactive)

    def test_a_dumb_terminal_gets_nothing(self):
        style = detect_style(FakeStream(True), {"TERM": "dumb"})
        self.assertFalse(style.color)
        self.assertFalse(style.interactive)

    def test_a_stream_without_isatty_is_treated_as_a_pipe(self):
        self.assertFalse(detect_style(object(), {"TERM": "xterm"}).color)

    def test_the_width_is_kept_within_sensible_limits(self):
        width = detect_style(FakeStream(False), {}).width
        self.assertTrue(MIN_WIDTH <= width <= MAX_WIDTH)


class PaintTests(unittest.TestCase):
    def test_paint_adds_ansi_codes_only_when_colour_is_on(self):
        self.assertEqual(Style(color=True).paint("x", "bold", "green"), f"\033[1;32mx{RESET}")
        self.assertEqual(Style(color=False).paint("x", "bold"), "x")
        self.assertEqual(PLAIN.paint("x", "red"), "x")

    def test_paint_with_no_styles_returns_the_text(self):
        self.assertEqual(Style(color=True).paint("x"), "x")

    def test_the_clear_line_code_returns_the_cursor_and_erases(self):
        self.assertTrue(CLEAR_LINE.startswith("\r"))


class RuleTests(unittest.TestCase):
    def test_a_rule_fills_the_width(self):
        self.assertEqual(len(Style(width=50).rule()), 50)

    def test_a_titled_rule_contains_the_title_and_fills_the_width(self):
        rule = Style(width=50).rule("Título")
        self.assertIn(" Título ", rule)
        self.assertEqual(len(rule), 50)

    def test_a_long_title_never_breaks_the_rule(self):
        self.assertIn("x" * 70, Style(width=40).rule("x" * 70))


class WrapTests(unittest.TestCase):
    TEXT = "uma frase bem longa " * 8

    def test_lines_never_exceed_the_width(self):
        wrapped = Style(width=40).wrap(self.TEXT.strip())
        self.assertTrue(all(len(line) <= 40 for line in wrapped.splitlines()))
        self.assertGreater(len(wrapped.splitlines()), 1)

    def test_a_prefix_gets_a_hanging_indent(self):
        lines = Style(width=40).wrap(self.TEXT.strip(), prefix="IA:   ").splitlines()
        self.assertTrue(lines[0].startswith("IA:   "))
        self.assertTrue(all(line.startswith(" " * 6) for line in lines[1:]))

    def test_only_the_prefix_is_painted(self):
        style = Style(color=True, width=40)
        wrapped = style.wrap("olá mundo", prefix="IA: ", painter=lambda p: style.paint(p, "green"))
        self.assertTrue(wrapped.startswith("\033[32mIA: \033[0m"))
        self.assertTrue(wrapped.endswith("olá mundo"))

    def test_paragraphs_are_preserved(self):
        wrapped = PLAIN.wrap("primeiro\nsegundo")
        self.assertEqual(wrapped.splitlines(), ["primeiro", "segundo"])

    def test_a_word_longer_than_the_width_is_not_cut(self):
        self.assertIn("a" * 60, Style(width=40).wrap("a" * 60))

    def test_plain_style_defaults(self):
        self.assertEqual(PLAIN.width, DEFAULT_WIDTH)
        self.assertFalse(PLAIN.color)


if __name__ == "__main__":
    unittest.main()
