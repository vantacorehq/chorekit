import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import requests

from chorekit.rates import convert, fetch_exchange_rates, filter_rates, save_rates

GOOD = {"result": "success", "rates": {"USD": 1, "EUR": 0.9, "GBP": 0.8}}


def fake_response(status=200, payload=None):
    response = mock.Mock()
    response.status_code = status
    response.json.return_value = payload if payload is not None else GOOD
    if status >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}", response=response)
    else:
        response.raise_for_status.return_value = None
    return response


class FetchTests(unittest.TestCase):
    @mock.patch("chorekit.rates.requests.get")
    def test_success(self, get):
        get.return_value = fake_response()
        data = fetch_exchange_rates("usd")
        self.assertEqual(data["rates"]["EUR"], 0.9)
        self.assertIn("/latest/USD", get.call_args[0][0])

    @mock.patch("chorekit.rates.requests.get")
    def test_retries_on_connection_error_then_succeeds(self, get):
        get.side_effect = [requests.ConnectionError("boom"), requests.Timeout("slow"), fake_response()]
        waits = []
        data = fetch_exchange_rates("USD", retries=3, backoff=1.0, sleep=waits.append)
        self.assertEqual(data["result"], "success")
        self.assertEqual(waits, [1.0, 2.0])

    @mock.patch("chorekit.rates.requests.get")
    def test_retries_on_server_error(self, get):
        get.side_effect = [fake_response(503), fake_response()]
        waits = []
        fetch_exchange_rates("USD", retries=2, backoff=0.5, sleep=waits.append)
        self.assertEqual(waits, [0.5])

    @mock.patch("chorekit.rates.requests.get")
    def test_gives_up_after_all_retries(self, get):
        get.side_effect = requests.ConnectionError("down")
        with self.assertRaises(requests.ConnectionError):
            fetch_exchange_rates("USD", retries=2, sleep=lambda _s: None)
        self.assertEqual(get.call_count, 3)

    @mock.patch("chorekit.rates.requests.get")
    def test_client_error_is_not_retried(self, get):
        get.return_value = fake_response(404)
        with self.assertRaises(requests.HTTPError):
            fetch_exchange_rates("USD", retries=3, sleep=lambda _s: None)
        self.assertEqual(get.call_count, 1)

    @mock.patch("chorekit.rates.requests.get")
    def test_api_error_payload_raises_value_error(self, get):
        get.return_value = fake_response(payload={"result": "error", "error-type": "unsupported-code"})
        with self.assertRaisesRegex(ValueError, "unsupported-code"):
            fetch_exchange_rates("XXX")


class HelperTests(unittest.TestCase):
    def test_filter_rates(self):
        data = filter_rates(GOOD, ["eur", " gbp "])
        self.assertEqual(data["rates"], {"EUR": 0.9, "GBP": 0.8})
        self.assertEqual(data["result"], "success")
        self.assertEqual(len(GOOD["rates"]), 3)  # original is untouched

    def test_filter_rates_unknown_code(self):
        with self.assertRaisesRegex(ValueError, "ZZZ"):
            filter_rates(GOOD, ["EUR", "zzz"])

    def test_convert(self):
        self.assertAlmostEqual(convert(100, GOOD, "eur"), 90.0)
        with self.assertRaises(ValueError):
            convert(100, GOOD, "ZZZ")

    def test_save_json_has_timestamp_source_and_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.json"
            save_rates(GOOD, str(path), "json")
            saved = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(saved), {"fetched_at", "source", "data"})
        self.assertEqual(saved["data"]["rates"]["EUR"], 0.9)

    def test_save_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.csv"
            save_rates(GOOD, str(path), "csv")
            rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
        self.assertEqual(rows[0], ["currency", "rate"])
        self.assertEqual(rows[1], ["EUR", "0.9"])


if __name__ == "__main__":
    unittest.main()
