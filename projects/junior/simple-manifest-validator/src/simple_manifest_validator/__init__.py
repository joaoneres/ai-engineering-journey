"""Cargo manifest validator for FilaFácil Logística."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("simple-manifest-validator")
except PackageNotFoundError:  # running from a source checkout that was not installed
    __version__ = "0+unknown"
