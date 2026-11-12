"""ViaCEP integration: isolated so an API failure never reaches the other layers."""

import asyncio
import json
import urllib.error
import urllib.request
from collections.abc import Callable

from constants import API_TIMEOUT_SECONDS, VIACEP_URL
from domain.pickups import normalize_cep
from errors import ApiError

Transport = Callable[[str, float], bytes]


def http_get(url: str, timeout: float) -> bytes:
    """Blocking GET request; every network failure becomes ApiError."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise ApiError(f"A API de CEP respondeu com erro HTTP {error.code}.") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ApiError("Não foi possível conectar à API de CEP (sem rede ou tempo esgotado).") from error


def parse_cep_response(body: bytes | str) -> dict:
    """Turn the ViaCEP JSON into the fields stored in the pickup."""
    try:
        data = json.loads(body)
    except ValueError as error:
        raise ApiError("A API de CEP retornou uma resposta que não é JSON válido.") from error
    if not isinstance(data, dict):
        raise ApiError("A API de CEP retornou um formato inesperado.")
    if data.get("erro"):
        raise ApiError("CEP não encontrado na API.")
    return {
        "cep": str(data.get("cep", "")),
        "street": str(data.get("logradouro", "")),
        "neighborhood": str(data.get("bairro", "")),
        "city": str(data.get("localidade", "")),
        "state": str(data.get("uf", "")),
    }


async def fetch_address(cep: str, transport: Transport = http_get) -> dict:
    """Look up the CEP without blocking the event loop.

    `transport` is injectable so tests (and an offline mode) need no network.
    """
    url = VIACEP_URL.format(cep=normalize_cep(cep))
    body = await asyncio.to_thread(transport, url, API_TIMEOUT_SECONDS)
    return parse_cep_response(body)
