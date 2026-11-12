"""Typed errors, one per origin: user input, data file and external API."""


class FilaFacilError(Exception):
    """Base class for every expected error; the UI shows it without crashing."""

    kind = "error"


class InputError(FilaFacilError, ValueError):
    """Invalid data typed by the user or rejected by a business rule."""

    kind = "input"


class NotFoundError(InputError, LookupError):
    """A pickup that does not exist."""


class FileError(FilaFacilError):
    """Failure reading or writing the local data file."""

    kind = "file"


class ApiError(FilaFacilError):
    """Failure calling or interpreting the external REST API."""

    kind = "api"
