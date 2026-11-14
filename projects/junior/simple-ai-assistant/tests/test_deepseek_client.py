import json
import unittest
import urllib.error
from unittest import mock

from ai_assistant.deliveries import load_deliveries
from ai_assistant.flow import Flow
from ai_assistant.library import load_library
from ai_assistant.model import DeepSeekClient, ModelError, http_post
from ai_assistant.scenarios import load_scenario

FAKE_KEY = "sk-test-0000000000000000000000000000"


def completion(content):
    return json.dumps(
        {"choices": [{"message": {"role": "assistant", "content": content}}]}
    ).encode()


class RecordingTransport:
    def __init__(self, reply):
        self.reply = reply
        self.requests = []

    def __call__(self, url, headers, body, timeout):
        self.requests.append((url, headers, json.loads(body), timeout))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


class RequestShapeTests(unittest.TestCase):
    def setUp(self):
        self.transport = RecordingTransport(completion('{"ok": true}'))
        self.client = DeepSeekClient(FAKE_KEY, "deepseek-flash", 12.0, self.transport)

    def test_sends_an_openai_compatible_request_in_json_mode(self):
        result = self.client.complete("system text", "user text")
        self.assertEqual(result, '{"ok": true}')
        url, headers, body, timeout = self.transport.requests[0]
        self.assertEqual(url, "https://api.deepseek.com/chat/completions")
        self.assertEqual(headers["Authorization"], f"Bearer {FAKE_KEY}")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(body["model"], "deepseek-flash")
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertEqual(
            body["messages"],
            [
                {"role": "system", "content": "system text"},
                {"role": "user", "content": "user text"},
            ],
        )
        self.assertIn("max_tokens", body)
        self.assertFalse(body["stream"])
        self.assertEqual(timeout, 12.0)

    def test_reasoning_is_off_by_default_and_can_be_turned_on(self):
        self.client.complete("s", "u")
        self.assertEqual(self.transport.requests[0][2]["thinking"], {"type": "disabled"})
        transport = RecordingTransport(completion("{}"))
        DeepSeekClient(FAKE_KEY, transport=transport, thinking=True).complete("s", "u")
        self.assertEqual(transport.requests[0][2]["thinking"], {"type": "enabled"})

    def test_the_token_budget_leaves_room_for_the_answer(self):
        self.client.complete("s", "u")
        self.assertGreaterEqual(self.transport.requests[0][2]["max_tokens"], 4096)

    def test_blank_content_is_returned_as_an_empty_string(self):
        # JSON mode can return blank content; the flow treats it as an invalid answer and retries
        for blank in ("", None, "  "):
            client = DeepSeekClient(FAKE_KEY, transport=RecordingTransport(completion(blank)))
            self.assertEqual(client.complete("s", "u").strip(), "")

    def test_a_missing_key_is_refused_up_front(self):
        for missing in (None, ""):
            with self.assertRaises(ModelError) as context:
                DeepSeekClient(missing)
            self.assertIn("DEEPSEEK_API_KEY", str(context.exception))

    def test_unexpected_response_shapes_are_model_errors(self):
        for bad in (b"not json", b"{}", b'{"choices": []}', b'{"choices": [{"message": 1}]}'):
            client = DeepSeekClient(FAKE_KEY, transport=RecordingTransport(bad))
            with self.assertRaises(ModelError):
                client.complete("s", "u")


class KeyNeverLeaksTests(unittest.TestCase):
    def test_the_key_is_absent_from_repr_and_from_every_error_message(self):
        client = DeepSeekClient(FAKE_KEY, transport=RecordingTransport(b"garbage"))
        texts = [repr(client), str(client)]
        failures = [
            RecordingTransport(b"garbage"),
            RecordingTransport(b'{"choices": []}'),
            RecordingTransport(
                ModelError("the model service answered HTTP 401 (check DEEPSEEK_API_KEY)")
            ),
        ]
        for transport in failures:
            try:
                DeepSeekClient(FAKE_KEY, transport=transport).complete("s", "u")
            except ModelError as error:
                texts.append(str(error))
                texts.append(repr(error))
        self.assertGreaterEqual(len(texts), 5)
        for text in texts:
            self.assertNotIn(FAKE_KEY, text)

    def test_the_key_is_not_in_the_request_body(self):
        transport = RecordingTransport(completion("{}"))
        DeepSeekClient(FAKE_KEY, transport=transport).complete("system", "user")
        self.assertNotIn(FAKE_KEY, json.dumps(transport.requests[0][2]))


class HttpPostErrorTests(unittest.TestCase):
    def test_http_errors_become_model_errors_without_the_response_body(self):
        error = urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, None)
        with (
            mock.patch("urllib.request.urlopen", side_effect=error),
            self.assertRaises(ModelError) as context,
        ):
            http_post("https://x", {"Authorization": f"Bearer {FAKE_KEY}"}, b"{}", 1.0)
        self.assertIn("HTTP 401", str(context.exception))
        self.assertIn("DEEPSEEK_API_KEY", str(context.exception))
        self.assertNotIn(FAKE_KEY, str(context.exception))

    def test_network_failures_become_model_errors(self):
        for failure in (urllib.error.URLError("dns"), TimeoutError(), ConnectionResetError()):
            with (
                mock.patch("urllib.request.urlopen", side_effect=failure),
                self.assertRaises(ModelError),
            ):
                http_post("https://x", {}, b"{}", 1.0)


class WireFormatThroughTheFlowTests(unittest.TestCase):
    def test_a_whole_scenario_runs_through_the_client_and_a_fake_transport(self):
        scenario = load_scenario("customer")
        answers = [answer for turn in scenario.turns for answer in turn.model]
        replies = iter(completion(json.dumps(answer, ensure_ascii=False)) for answer in answers)

        def transport(url, headers, body, timeout):
            return next(replies)

        client = DeepSeekClient(FAKE_KEY, transport=transport)
        flow = Flow(load_library(), client, load_deliveries())
        state = flow.start("customer")
        for turn in scenario.turns:
            result = flow.turn(state, turn.user)
            state = result.state
            self.assertIsNone(result.failure, result.errors)
        self.assertEqual(result.next_action, "hand_off_to_team")

    def test_a_service_failure_in_the_middle_of_a_turn_escalates(self):
        client = DeepSeekClient(
            FAKE_KEY, transport=RecordingTransport(ModelError("could not reach the model service"))
        )
        flow = Flow(load_library(), client, load_deliveries())
        result = flow.turn(flow.start("customer"), "oi")
        self.assertEqual(result.failure, "model_error")
        self.assertTrue(result.escalated)


if __name__ == "__main__":
    unittest.main()
