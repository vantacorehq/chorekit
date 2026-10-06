"""Downloads exchange rates from a free public API (no API key needed)."""

import csv
import json
import time
from datetime import datetime, timezone

import requests

API_URL_TEMPLATE = "https://open.er-api.com/v6/latest/{base}"
SOURCE = "https://www.exchangerate-api.com/"


def fetch_exchange_rates(base_currency: str, timeout: float = 10, retries: int = 3,
                         backoff: float = 1.0, sleep=time.sleep) -> dict:
    """Requests current rates for the base currency.

    Connection errors, timeouts, HTTP 429 and HTTP 5xx are retried up to
    `retries` times, waiting backoff, 2*backoff, 4*backoff, ... seconds.
    Other HTTP errors (for example 404) fail immediately.
    """
    url = API_URL_TEMPLATE.format(base=base_currency.upper())
    last_error = None

    for attempt in range(retries + 1):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 429 or response.status_code >= 500:
                raise requests.HTTPError(f"HTTP {response.status_code}", response=response)
            response.raise_for_status()
            break
        except (requests.ConnectionError, requests.Timeout) as e:
            last_error = e
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status is None or not (status == 429 or status >= 500):
                raise
            last_error = e

        if attempt < retries:
            sleep(backoff * 2 ** attempt)
    else:
        raise last_error

    data = response.json()
    if data.get("result") != "success":
        raise ValueError(f"API returned an error: {data.get('error-type', 'unknown error')}")
    return data


def filter_rates(data: dict, symbols: list) -> dict:
    """Returns a copy of the data that keeps only the requested currencies."""
    rates = data.get("rates", {})
    wanted = [s.strip().upper() for s in symbols if s.strip()]
    unknown = [s for s in wanted if s not in rates]
    if unknown:
        raise ValueError(f"Unknown currency code(s): {', '.join(unknown)}")
    filtered = dict(data)
    filtered["rates"] = {s: rates[s] for s in wanted}
    return filtered


def convert(amount: float, data: dict, target: str) -> float:
    """Converts an amount of the base currency into the target currency."""
    target = target.strip().upper()
    rates = data.get("rates", {})
    if target not in rates:
        raise ValueError(f"Unknown currency code(s): {target}")
    return amount * rates[target]


def save_rates(data: dict, output_path: str, fmt: str = "json") -> None:
    """Saves rates as JSON (with timestamp and source) or as a CSV table."""
    if fmt == "csv":
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["currency", "rate"])
            for currency, rate in sorted(data.get("rates", {}).items()):
                writer.writerow([currency, rate])
        return

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": SOURCE,
        "data": data,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
