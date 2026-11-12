import json
import unittest

from errors import ApiError, InputError
from integrations import cep_client

OK_BODY = json.dumps({
    "cep": "01001-000", "logradouro": "Praça da Sé", "bairro": "Sé",
    "localidade": "São Paulo", "uf": "SP",
}).encode()


class ParseTests(unittest.TestCase):
    def test_parses_a_valid_response(self):
        self.assertEqual(cep_client.parse_cep_response(OK_BODY), {
            "cep": "01001-000", "street": "Praça da Sé", "neighborhood": "Sé",
            "city": "São Paulo", "state": "SP",
        })

    def test_unknown_cep_invalid_json_and_unexpected_shape(self):
        for body in (b'{"erro": true}', b"<html>", b"", b"[1, 2]", b'"text"'):
            with self.subTest(body=body), self.assertRaises(ApiError):
                cep_client.parse_cep_response(body)


class FetchTests(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_uses_normalized_cep_in_url(self):
        calls = []

        def transport(url, timeout):
            calls.append((url, timeout))
            return OK_BODY

        location = await cep_client.fetch_address("01001-000", transport)
        self.assertEqual(location["city"], "São Paulo")
        self.assertEqual(calls[0][0], "https://viacep.com.br/ws/01001000/json/")
        self.assertGreater(calls[0][1], 0)

    async def test_network_failure_becomes_api_error(self):
        def transport(url, timeout):
            raise ApiError("sem rede")

        with self.assertRaises(ApiError):
            await cep_client.fetch_address("01001000", transport)

    async def test_invalid_cep_is_an_input_error_and_never_calls_the_api(self):
        def transport(url, timeout):
            raise AssertionError("must not be called")

        with self.assertRaises(InputError):
            await cep_client.fetch_address("123", transport)


if __name__ == "__main__":
    unittest.main()
