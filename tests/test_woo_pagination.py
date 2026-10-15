"""Offline regression tests for the actual importer source; no Frappe/site required.

Run from the repository root:
    python -m unittest discover -s tests -p 'test_woo_pagination.py' -v

Only the two network-selection functions are loaded from the source AST. This
avoids importing Frappe or connecting to a database, and all HTTP is simulated.
These are not ERPNext installation or live-source integration tests.
"""
import ast
import re
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urljoin, urlparse


def product(identifier):
    return {"id": identifier, "type": "simple"}


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body = body
        self.status_code = status
        self.headers = headers or {"content-type": "application/json"}

    def json(self):
        return self.body


class Session:
    def __init__(self, products=None, responder=None):
        self.products = products or []
        self.responder = responder
        self.headers = {}
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, url, params=None, **kwargs):
        self.calls.append((url, dict(params or {}), kwargs))
        if self.responder:
            return self.responder(params)
        size = params["per_page"]
        start = (params["page"] - 1) * size
        return Response(self.products[start:start + size])


def load_fetcher(session):
    source = Path(__file__).resolve().parents[1] / "mastercellar" / "woo_import.py"
    parsed = ast.parse(source.read_text(encoding="utf-8"))
    selected = [node for node in parsed.body if isinstance(node, ast.FunctionDef)
                and node.name in {"_allowed_source_host", "_get_products"}]
    namespace = {
        "requests": SimpleNamespace(Session=lambda: session),
        "re": re, "urlparse": urlparse, "urljoin": urljoin,
        "sleep": lambda _: None, "MAX_PRODUCTS": 60,
        "REQUEST_TIMEOUT": (5, 18), "UA": "offline-test",
        "API": "https://www.themastercellar.com/wp-json/wc/store/v1/products",
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["_get_products"]


class PaginationTests(unittest.TestCase):
    def test_36_requested_means_36_distinct_products(self):
        session = Session([product(i) for i in range(1, 81)])
        result = load_fetcher(session)(36)
        self.assertEqual([p["id"] for p in result], list(range(1, 37)))
        self.assertEqual([c[1]["per_page"] for c in session.calls], [24, 24])

    def test_12_uses_one_request(self):
        session = Session([product(i) for i in range(1, 40)])
        self.assertEqual(len(load_fetcher(session)(12)), 12)
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0][1]["per_page"], 12)

    def test_60_uses_three_equal_sized_pages(self):
        session = Session([product(i) for i in range(1, 81)])
        result = load_fetcher(session)(60)
        self.assertEqual([p["id"] for p in result], list(range(1, 61)))
        self.assertEqual([c[1]["per_page"] for c in session.calls], [24, 24, 24])

    def test_stops_at_short_final_page(self):
        session = Session([product(i) for i in range(1, 28)])
        self.assertEqual(len(load_fetcher(session)(36)), 27)
        self.assertEqual(len(session.calls), 2)

    def test_empty_source(self):
        session = Session()
        self.assertEqual(load_fetcher(session)(36), [])
        self.assertEqual(len(session.calls), 1)

    def test_import_limit_remains_60(self):
        session = Session([product(i) for i in range(1, 150)])
        self.assertEqual(len(load_fetcher(session)(1000)), 60)

    def test_duplicate_source_ids_not_returned_twice(self):
        pages = {1: [product(i) for i in range(1, 25)],
                 2: [product(i) for i in range(20, 44)]}
        session = Session(responder=lambda params: Response(pages.get(params["page"], [])))
        result = load_fetcher(session)(36)
        self.assertEqual([p["id"] for p in result], list(range(1, 37)))

    def test_repeating_full_page_is_bounded(self):
        session = Session(responder=lambda _: Response([product(i) for i in range(1, 25)]))
        result = load_fetcher(session)(36)
        self.assertEqual(len(result), 24)
        self.assertEqual(len(session.calls), 6)

    def test_filters_remain_the_same_across_pages(self):
        session = Session([product(i) for i in range(1, 60)])
        load_fetcher(session)(36, category="maltese-wines", search=" Marsovin ")
        for _, params, options in session.calls:
            self.assertEqual(params["category"], "maltese-wines")
            self.assertEqual(params["search"], "Marsovin")
            self.assertEqual(params["type"], "simple")
            self.assertFalse(options["allow_redirects"])

    def test_bad_category_rejected_before_http(self):
        session = Session()
        with self.assertRaises(ValueError):
            load_fetcher(session)(12, category="https://unrelated.example")
        self.assertEqual(session.calls, [])

    def test_bad_search_rejected_before_http(self):
        session = Session()
        with self.assertRaises(ValueError):
            load_fetcher(session)(12, search="x" * 81)
        self.assertEqual(session.calls, [])

    def test_redirect_outside_source_rejected(self):
        session = Session(responder=lambda _: Response([], 302, {"Location": "https://unrelated.example/"}))
        with self.assertRaises(RuntimeError):
            load_fetcher(session)(12)
        self.assertEqual(len(session.calls), 1)

    def test_invalid_rows_and_non_simple_products_skipped(self):
        session = Session([None, "invalid", product(True), product(-1),
                           {"id": 2, "type": "variable"}, product(3)])
        self.assertEqual(load_fetcher(session)(12), [product(3)])


if __name__ == "__main__":
    unittest.main()
