"""Tests for devtools.http_fixture only. Does not exercise accountsvc."""
import json
import os
import sys
import unittest
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from devtools.http_fixture import HttpFixture  # noqa: E402


def _post(url, path, body=None, raw=None, headers=None):
    data = raw if raw is not None else json.dumps(body if body is not None else {}).encode("utf-8")
    request = urllib.request.Request(
        url + path,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


class NoAccountsvcDependencyTests(unittest.TestCase):
    def test_source_does_not_reference_accountsvc(self):
        source_path = os.path.join(REPO_ROOT, "devtools", "http_fixture.py")
        with open(source_path, "r", encoding="utf-8") as handle:
            source = handle.read()
        self.assertNotIn("accountsvc", source)


class LifecycleTests(unittest.TestCase):
    def test_url_raises_before_start(self):
        fixture = HttpFixture()
        with self.assertRaises(RuntimeError):
            fixture.url

    def test_start_binds_loopback_only(self):
        fixture = HttpFixture()
        self.addCleanup(fixture.stop)
        fixture.start()
        host, _port = fixture._httpd.server_address
        self.assertEqual(host, "127.0.0.1")
        self.assertTrue(fixture.url.startswith("http://127.0.0.1:"))

    def test_double_start_raises(self):
        fixture = HttpFixture()
        self.addCleanup(fixture.stop)
        fixture.start()
        with self.assertRaises(RuntimeError):
            fixture.start()

    def test_stop_is_idempotent(self):
        fixture = HttpFixture()
        fixture.start()
        fixture.stop()
        fixture.stop()  # no error calling stop a second time

    def test_context_manager_starts_and_stops(self):
        with HttpFixture() as fixture:
            self.assertTrue(fixture.url.startswith("http://127.0.0.1:"))
            status, _ = _post(fixture.url, "/anything", {"a": 1})
            self.assertEqual(status, 200)
        with self.assertRaises(RuntimeError):
            fixture.url  # stopped by __exit__


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = HttpFixture()
        self.addCleanup(self.fixture.stop)
        self.fixture.start()

    def test_records_path_headers_and_json_body(self):
        status, _ = _post(
            self.fixture.url,
            "/mail",
            {"recipient": "alice@example.com", "recovery_token": "tok-123"},
            headers={"Authorization": "Bearer secret"},
        )
        self.assertEqual(status, 200)

        self.assertEqual(len(self.fixture.received), 1)
        record = self.fixture.received[0]
        self.assertEqual(record["path"], "/mail")
        self.assertEqual(
            record["json"], {"recipient": "alice@example.com", "recovery_token": "tok-123"}
        )
        self.assertEqual(record["headers"]["Authorization"], "Bearer secret")

    def test_records_multiple_requests_in_order(self):
        _post(self.fixture.url, "/a", {"n": 1})
        _post(self.fixture.url, "/b", {"n": 2})
        paths = [r["path"] for r in self.fixture.received]
        self.assertEqual(paths, ["/a", "/b"])

    def test_empty_body_recorded_as_none(self):
        status, _ = _post(self.fixture.url, "/empty", raw=b"")
        self.assertEqual(status, 200)
        self.assertEqual(self.fixture.received[0]["json"], None)

    def test_malformed_json_returns_400_and_is_not_recorded(self):
        status, _ = _post(self.fixture.url, "/bad", raw=b"{not json")
        self.assertEqual(status, 400)
        self.assertEqual(self.fixture.received, [])

    def test_missing_content_length_returns_411(self):
        # urllib always sends Content-Length for our `data=` requests, so
        # drive this directly over a raw socket via http.client instead.
        import http.client

        host, port = self.fixture._httpd.server_address
        conn = http.client.HTTPConnection(host, port)
        try:
            conn.putrequest("POST", "/no-length", skip_accept_encoding=True)
            conn.endheaders()
            response = conn.getresponse()
            self.assertEqual(response.status, 411)
            response.read()
        finally:
            conn.close()
        self.assertEqual(self.fixture.received, [])


class ConfiguredStatusTests(unittest.TestCase):
    def test_default_status_and_body_are_used(self):
        fixture = HttpFixture(status=201, body=b"created")
        self.addCleanup(fixture.stop)
        fixture.start()

        status, body = _post(fixture.url, "/x", {})
        self.assertEqual(status, 201)
        self.assertEqual(body, b"created")

    def test_set_response_changes_status_for_all_future_requests(self):
        fixture = HttpFixture()
        self.addCleanup(fixture.stop)
        fixture.start()

        fixture.set_response(503, b"unavailable")
        first_status, first_body = _post(fixture.url, "/x", {})
        second_status, second_body = _post(fixture.url, "/x", {})
        self.assertEqual((first_status, first_body), (503, b"unavailable"))
        self.assertEqual((second_status, second_body), (503, b"unavailable"))

    def test_queue_response_is_one_shot_then_falls_back_to_default(self):
        fixture = HttpFixture(status=200, body=b"ok")
        self.addCleanup(fixture.stop)
        fixture.start()

        fixture.queue_response(503, b"first fails")
        first_status, first_body = _post(fixture.url, "/x", {})
        second_status, second_body = _post(fixture.url, "/x", {})
        self.assertEqual((first_status, first_body), (503, b"first fails"))
        self.assertEqual((second_status, second_body), (200, b"ok"))

    def test_queue_response_drains_in_fifo_order(self):
        fixture = HttpFixture()
        self.addCleanup(fixture.stop)
        fixture.start()

        fixture.queue_response(503, b"one")
        fixture.queue_response(502, b"two")
        statuses_and_bodies = [_post(fixture.url, "/x", {}) for _ in range(3)]
        self.assertEqual(
            statuses_and_bodies,
            [(503, b"one"), (502, b"two"), (200, b"")],
        )


class BoundedBodyTests(unittest.TestCase):
    def test_oversized_body_rejected_and_not_recorded(self):
        fixture = HttpFixture(max_body_bytes=16)
        self.addCleanup(fixture.stop)
        fixture.start()

        oversized = json.dumps({"pad": "x" * 100}).encode("utf-8")
        status, _ = _post(fixture.url, "/x", raw=oversized)
        self.assertEqual(status, 413)
        self.assertEqual(fixture.received, [])

    def test_body_at_exactly_the_bound_is_accepted(self):
        fixture = HttpFixture(max_body_bytes=64)
        self.addCleanup(fixture.stop)
        fixture.start()

        payload = {"pad": "x"}
        raw = json.dumps(payload).encode("utf-8")
        self.assertLessEqual(len(raw), 64)
        status, _ = _post(fixture.url, "/x", raw=raw)
        self.assertEqual(status, 200)
        self.assertEqual(fixture.received[0]["json"], payload)


if __name__ == "__main__":
    unittest.main()
