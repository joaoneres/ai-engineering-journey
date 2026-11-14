"""Terminal styling: width, wrapping and colours.

Colours are used only when the output is a real terminal that supports them: never in a pipe, never
when NO_COLOR is set and never on a "dumb" terminal. Text is wrapped to the terminal width with a
hanging indent, so long answers stay readable. This module contains no user-facing text.
"""

import os
import shutil
import sys
import textwrap
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TextIO

RESET = "\033[0m"
CODES = {"bold": "1", "dim": "2", "red": "31", "green": "32", "yellow": "33", "cyan": "36"}
CLEAR_LINE = "\r\033[K"
MIN_WIDTH = 40
MAX_WIDTH = 100
DEFAULT_WIDTH = 80


@dataclass(frozen=True)
class Style:
    """How output is drawn. `interactive` means the cursor can redraw the current line."""

    color: bool = False
    width: int = DEFAULT_WIDTH
    interactive: bool = False

    def paint(self, text: str, *styles: str) -> str:
        """Wrap text in ANSI codes, or return it unchanged when colours are off."""
        if not self.color or not styles:
            return text
        codes = ";".join(CODES[name] for name in styles)
        return f"\033[{codes}m{text}{RESET}"

    def rule(self, title: str = "") -> str:
        """A horizontal line, optionally with a title inside it."""
        if not title:
            return "─" * self.width
        return f"── {title} " + "─" * max(3, self.width - len(title) - 4)

    def wrap(
        self,
        text: str,
        prefix: str = "",
        painter: Callable[[str], str] | None = None,
    ) -> str:
        """Wrap to the width with a hanging indent under the prefix. Paragraphs are kept."""
        rest = " " * len(prefix)
        paragraphs = []
        for index, paragraph in enumerate(text.split("\n")):
            first = prefix if index == 0 else rest
            filled = textwrap.fill(
                paragraph,
                width=self.width,
                initial_indent=first,
                subsequent_indent=rest,
                break_long_words=False,
                break_on_hyphens=False,
            )
            paragraphs.append(filled or first.rstrip())
        body = "\n".join(paragraphs)
        if prefix and painter:
            body = painter(prefix) + body[len(prefix) :]
        return body


PLAIN = Style()


def detect_style(stream: TextIO | None = None, environ: Mapping[str, str] | None = None) -> Style:
    """Choose colours and width for a stream (stdout by default)."""
    stream = stream or sys.stdout
    environ = os.environ if environ is None else environ
    is_tty = bool(getattr(stream, "isatty", lambda: False)())
    capable = is_tty and environ.get("TERM") != "dumb"
    color = capable and not environ.get("NO_COLOR")
    columns = shutil.get_terminal_size(fallback=(DEFAULT_WIDTH, 24)).columns
    width = max(MIN_WIDTH, min(MAX_WIDTH, columns))
    return Style(color=color, width=width, interactive=capable)
