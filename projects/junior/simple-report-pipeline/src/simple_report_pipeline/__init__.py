"""Operational report for FilaFácil Logística pickups."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("simple-report-pipeline")
except PackageNotFoundError:  # running from a source checkout that was not installed
    __version__ = "0+unknown"
