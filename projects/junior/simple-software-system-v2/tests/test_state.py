import unittest

from errors import ApiError, FileError, InputError
from state import app_state as app


PICKUPS = [
    {"id": 1, "status": "pending", "priority": "high"},
    {"id": 2, "status": "pending", "priority": "low"},
    {"id": 3, "status": "completed", "priority": "high"},
]


class AppStateTests(unittest.TestCase):
    def test_initial_state(self):
        state = app.initial_state()
        self.assertEqual((state.pickups, state.loading, state.last_error, state.filters), ([], False, None, {}))

    def test_transitions_return_new_state_and_keep_the_old_one(self):
        state = app.initial_state(PICKUPS)
        loading = app.set_loading(state, True)
        self.assertTrue(loading.loading)
        self.assertFalse(state.loading)
        self.assertEqual(loading.pickups, PICKUPS)

    def test_set_pickups_copies_the_list(self):
        source = list(PICKUPS)
        state = app.set_pickups(app.initial_state(), source)
        source.clear()
        self.assertEqual(len(state.pickups), 3)

    def test_error_records_its_origin_and_can_be_cleared(self):
        state = app.initial_state()
        for error, kind in ((InputError("x"), "input"), (FileError("y"), "file"), (ApiError("z"), "api")):
            with self.subTest(kind=kind):
                self.assertEqual(app.set_error(state, error).last_error, {"kind": kind, "message": str(error)})
        self.assertIsNone(app.clear_error(app.set_error(state, ApiError("z"))).last_error)

    def test_filters_combine_and_clear(self):
        state = app.initial_state(PICKUPS)
        state = app.set_filter(state, "status", "pending")
        self.assertEqual([p["id"] for p in app.visible_pickups(state)], [1, 2])
        state = app.set_filter(state, "priority", "high")
        self.assertEqual([p["id"] for p in app.visible_pickups(state)], [1])
        state = app.clear_filters(state)
        self.assertEqual(len(app.visible_pickups(state)), 3)

    def test_invalid_filter_is_rejected_and_state_is_unchanged(self):
        state = app.initial_state(PICKUPS)
        with self.assertRaises(InputError):
            app.set_filter(state, "status", "done")
        with self.assertRaises(InputError):
            app.set_filter(state, "city", "x")
        self.assertEqual(state.filters, {})


if __name__ == "__main__":
    unittest.main()
