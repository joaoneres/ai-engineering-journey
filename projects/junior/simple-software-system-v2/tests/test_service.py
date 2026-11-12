import unittest
from unittest import mock

from errors import ApiError, FileError, InputError
from services import pickup_service as service

LOCATION = {"cep": "01001-000", "street": "Sé", "neighborhood": "Sé", "city": "São Paulo", "state": "SP"}


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    def patch_save(self, **kwargs):
        patcher = mock.patch.object(service.storage, "save_pickups", new=mock.AsyncMock(**kwargs))
        self.addCleanup(patcher.stop)
        return patcher.start()

    async def test_create_saves_the_enriched_pickup(self):
        save = self.patch_save()
        updated = await service.create_pickup([], "Ana", "Rua A", 2, "high", LOCATION)
        self.assertEqual(updated[0]["city"], "São Paulo")
        save.assert_awaited_once_with(updated)

    async def test_create_without_location_is_not_enriched(self):
        self.patch_save()
        updated = await service.create_pickup([], "Ana", "Rua A", 2, "high")
        self.assertFalse(updated[0]["enriched"])

    async def test_invalid_data_is_rejected_before_saving(self):
        save = self.patch_save()
        with self.assertRaises(InputError):
            await service.create_pickup([], "", "Rua A", 2, "high")
        save.assert_not_awaited()

    async def test_file_failure_propagates_and_original_list_is_unchanged(self):
        self.patch_save(side_effect=FileError("disk full"))
        original = []
        with self.assertRaises(FileError):
            await service.create_pickup(original, "Ana", "Rua A", 2, "high")
        self.assertEqual(original, [])

    async def test_lookup_location_success_and_api_failure(self):
        body = (b'{"cep":"01001-000","logradouro":"Se","bairro":"Se","localidade":"SP","uf":"SP"}')
        self.assertEqual((await service.lookup_location("01001000", lambda u, t: body))["state"], "SP")

        def broken(url, timeout):
            raise ApiError("sem rede")

        with self.assertRaises(ApiError):
            await service.lookup_location("01001000", broken)

    async def test_change_status_saves_the_new_list(self):
        save = self.patch_save()
        pickups = await service.create_pickup([], "Ana", "Rua A", 2, "high")
        updated = await service.change_status(pickups, 1, "in_transit")
        self.assertEqual(updated[0]["status"], "in_transit")
        self.assertEqual(save.await_count, 2)


if __name__ == "__main__":
    unittest.main()
