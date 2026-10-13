"""Strict parsing of the optional gateway-forwarded envelope header."""

from __future__ import annotations

import json
import unittest

from auditlog.gateway import GatewayEnvelope, GatewayEnvelopeError, parse_gateway_envelope


class MissingHeaderTests(unittest.TestCase):
    def test_absent_header_is_not_an_error(self) -> None:
        self.assertIsNone(parse_gateway_envelope(None))


class WellFormedEnvelopeTests(unittest.TestCase):
    def test_valid_envelope_parses(self) -> None:
        raw = json.dumps({"gateway_id": "gw-1", "forwarded_for": "203.0.113.7"})
        self.assertEqual(
            parse_gateway_envelope(raw),
            GatewayEnvelope(gateway_id="gw-1", forwarded_for="203.0.113.7"),
        )


class MalformedEnvelopeTests(unittest.TestCase):
    def test_not_json_raises(self) -> None:
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope("{not json")

    def test_json_array_raises(self) -> None:
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope(json.dumps(["gw-1", "203.0.113.7"]))

    def test_json_scalar_raises(self) -> None:
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope(json.dumps("gw-1"))

    def test_missing_field_raises(self) -> None:
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope(json.dumps({"gateway_id": "gw-1"}))

    def test_extra_field_raises(self) -> None:
        raw = json.dumps({"gateway_id": "gw-1", "forwarded_for": "203.0.113.7", "extra": "nope"})
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope(raw)

    def test_wrong_typed_field_raises(self) -> None:
        raw = json.dumps({"gateway_id": 123, "forwarded_for": "203.0.113.7"})
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope(raw)

    def test_empty_string_field_raises(self) -> None:
        raw = json.dumps({"gateway_id": "", "forwarded_for": "203.0.113.7"})
        with self.assertRaises(GatewayEnvelopeError):
            parse_gateway_envelope(raw)


if __name__ == "__main__":
    unittest.main()
