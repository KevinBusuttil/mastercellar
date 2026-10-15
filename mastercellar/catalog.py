"""Read-only, explicitly scoped ERPNext catalogue for the Master Cellar demonstration.

No website visitor can invoke data-changing operations here.
The TMC- prefix is a deliberate isolation boundary for public demo items.
"""

from urllib.parse import quote

import frappe
from frappe.utils import fmt_money, getdate, nowdate

DEMO_PREFIX = "TMC-"
SELLING_PRICE_LIST = "Master Cellar Retail"
MAX_ITEMS = 80

CATEGORIES = {
    "Wines": {"Maltese Wines", "Foreign Wines"},
    "Spirits": {"Spirits"},
    "Beer & Cider": {"Beer & Cider"},
    "Gift Hampers": {"Gift Hampers"},
    "Gourmet": {"Gourmet"},
}


def _price_by_item(item_codes):
    if not item_codes:
        return {}

    rows = frappe.get_all(
        "Item Price",
        filters={
            "item_code": ["in", item_codes],
            "price_list": SELLING_PRICE_LIST,
            "selling": 1,
        },
        fields=["item_code", "price_list_rate", "currency", "valid_from", "valid_upto"],
        order_by="valid_from desc, modified desc",
        limit_page_length=500,
    )
    today = getdate(nowdate())
    prices = {}

    for row in rows:
        if row.item_code in prices:
            continue
        if row.valid_from and getdate(row.valid_from) > today:
            continue
        if row.valid_upto and getdate(row.valid_upto) < today:
            continue
        prices[row.item_code] = row

    return prices


def _decorate(items):
    prices = _price_by_item([item.item_code for item in items])
    result = []

    for item in items:
        rate = prices.get(item.item_code)
        result.append(
            {
                "item_code": item.item_code,
                "item_name": item.item_name,
                "item_group": item.item_group,
                "image": item.image or "",
                "product_url": "/mastercellar/product?item=" + quote(item.item_code, safe=""),
                "price_text": (
                    fmt_money(rate.price_list_rate, currency=rate.currency or "EUR") if rate else None
                ),
            }
        )

    return result


def get_demo_products(category=None, limit=MAX_ITEMS):
    """Show only the manually designated TMC-* demonstration stock."""
    rows = frappe.get_all(
        "Item",
        filters={
            "item_code": ["like", DEMO_PREFIX + "%"],
            "disabled": 0,
            "is_sales_item": 1,
        },
        fields=["item_code", "item_name", "item_group", "image"],
        order_by="item_name asc",
        limit_page_length=min(max(int(limit), 1), MAX_ITEMS),
    )
    if category in CATEGORIES:
        rows = [row for row in rows if row.item_group in CATEGORIES[category]]
    return _decorate(rows)


def get_demo_product(item_code):
    if not isinstance(item_code, str) or not item_code.startswith(DEMO_PREFIX):
        return None

    items = frappe.get_all(
        "Item",
        filters={"item_code": item_code, "disabled": 0, "is_sales_item": 1},
        fields=["item_code", "item_name", "item_group", "image"],
        limit_page_length=1,
    )
    products = _decorate(items)
    return products[0] if products else None
